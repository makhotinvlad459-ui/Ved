# backend/app/celery/tasks.py
import os
import re
import traceback
from datetime import datetime, timedelta, timezone

from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import worker_process_shutdown
from sqlalchemy import create_engine, select, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .worker import celery_app

from app.models import (
    ProcessingSession,
    Product,
    Category,
    Color,
    PendingModel,
    PendingWeight,
    PendingGtin,
)
from app.services.parser import parse_invoice, parse_manifest
from app.services.transformer import transform_product_name, clean_serial
from app.services.generator import generate_specification
from app.services.model_detector import save_pending_models, get_pending_models_by_session
from app.services.packing_list_parser import resolve_weight_extended


# ============================================================
# ЕДИНЫЙ ДВИЖОК ДЛЯ ВСЕХ CELERY-ЗАДАЧ
# ============================================================
DATABASE_URL = os.environ["DATABASE_URL"]  # без хардкода пароля

sync_engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,       # безопасно с prefork, соединение на задачу
    pool_pre_ping=True,       # безвредно с NullPool, полезно если сменим пул
    future=True,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    future=True,
)


@worker_process_shutdown.connect
def _dispose_engine_on_shutdown(**kwargs):
    """Аккуратно закрыть движок при завершении процесса воркера."""
    try:
        sync_engine.dispose()
    except Exception as e:
        print(f"⚠️ Ошибка dispose() при shutdown: {e}")


# ============================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================
def resolve_weight(db, part_number=None, model_number=None, description=None):
    """Обратная совместимость — вызывает расширенную версию."""
    return resolve_weight_extended(
        db,
        part_number=part_number,
        model_number=model_number,
        description=description,
    )


def _get_session_or_none(db, session_id: str):
    return db.execute(
        select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    ).scalar_one_or_none()


def _mark_session_error(session_id: str, error: str):
    """Помечает сессию как error в отдельной транзакции (для except-блоков)."""
    try:
        with SessionLocal() as db:
            session = _get_session_or_none(db, session_id)
            if session:
                session.status = "error"
                session.errors = error
                db.commit()
    except Exception as cleanup_err:
        print(f"❌ Не удалось пометить сессию {session_id} как error: {cleanup_err}")


def _handle_soft_time_limit(session_id: str):
    _mark_session_error(
        session_id,
        "Превышен лимит времени обработки (soft time limit)",
    )


# ============================================================
# process_invoice
# ============================================================
@celery_app.task(name="process_invoice")
def process_invoice(session_id: str):
    print(f"🔄 Начинаем обработку сессии {session_id}")

    try:
        with SessionLocal() as db:
            session = _get_session_or_none(db, session_id)
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            # Идемпотентный guard: если уже завершено — не переобрабатываем
            if session.status == "completed" and session.result_file:
                print(f"⏭️ Сессия {session_id} уже завершена, пропускаем")
                return {
                    "status": "completed",
                    "session_id": session_id,
                    "items": session.processed_items or 0,
                    "message": "Сессия уже была обработана",
                }

            print(f"📄 Парсим инвойс: {session.invoice_file}")
            invoice_data = parse_invoice(session.invoice_file)
            invoice_date = invoice_data.get("invoice_date", datetime.now())
            invoice_number = invoice_data.get("invoice_number", "")
            items = invoice_data.get("items", [])
            print(f"   Найдено позиций: {len(items)}")
            print(f"   Номер инвойса: {invoice_number}")
            print(f"   Дата инвойса: {invoice_date}")

            if not items:
                session.status = "error"
                session.errors = "В инвойсе не найдено ни одной позиции"
                db.commit()
                return {"error": "No items in invoice", "session_id": session_id}

            print(f"📄 Парсим манифест: {session.manifest_file}")
            manifest_data = parse_manifest(session.manifest_file)
            serials_dict = manifest_data.get("serials", {})
            imei_dict = manifest_data.get("imei", {})
            print(f"   Найдено серийников: {sum(len(v) for v in serials_dict.values())}")
            print(f"   Найдено IMEI: {sum(len(v) for v in imei_dict.values())}")

            categories = db.execute(select(Category)).scalars().all()
            colors = db.execute(select(Color)).scalars().all()
            color_mapping = {c.eng: c.rus for c in colors}

            # === Собираем все part_number и одним запросом тянем Product ===
            part_numbers = {item.get("part_number", "") for item in items if item.get("part_number")}
            products_by_pn = {}
            if part_numbers:
                products = db.execute(
                    select(Product).where(Product.part_number.in_(part_numbers))
                ).scalars().all()
                products_by_pn = {p.part_number: p for p in products}

            # === Обогащаем Product: coo и upc (если пусто) ===
            enriched = 0
            for item in items:
                pn = item.get("part_number", "")
                if not pn:
                    continue
                product = products_by_pn.get(pn)
                if product:
                    changed = False
                    if not product.coo and item.get("coo"):
                        product.coo = item.get("coo")
                        changed = True
                    if not product.upc and item.get("upc"):
                        product.upc = item.get("upc")
                        changed = True
                    if changed:
                        enriched += 1
                        print(f"   📥 Обогатили {pn}: coo={product.coo}, upc={product.upc}")
            if enriched:
                db.commit()

            print("🔍 Проверяем новые модели и товары без категории...")
            pending_models = save_pending_models(
                items=items,
                categories=categories,
                colors=colors,
                db=db,
                session_id=session_id,
            )

            missing_part_numbers = []
            missing_categories = []

            for item in items:
                pn = item.get("part_number", "")
                if not pn:
                    continue

                # MOONWALKERS: пропускаем проверку, чтобы он шел в спецификацию
                if "moonwalkers" in pn.lower():
                    continue

                product = products_by_pn.get(pn)
                if not product:
                    if not re.match(r'^[A-Z0-9\-/. ]+$', pn) or " " in pn:
                        continue
                    missing_part_numbers.append(pn)
                elif not product.category_id:
                    missing_categories.append(pn)

            if pending_models or missing_part_numbers or missing_categories:
                if pending_models:
                    print(f"   Найдено {len(pending_models)} новых/требующих категорию моделей")
                if missing_part_numbers:
                    print(f"   ⚠️ Товаров без Product в БД: {len(missing_part_numbers)} → {missing_part_numbers}")
                if missing_categories:
                    print(f"   ⚠️ Товаров без категории: {len(missing_categories)} → {missing_categories}")

                session.status = "pending_approval"
                db.commit()
                print(f"⏳ Сессия {session_id} ожидает подтверждения")
                pending_list = get_pending_models_by_session(db, session_id)
                return {
                    "status": "pending_approval",
                    "session_id": session_id,
                    "new_models": pending_list,
                    "missing_part_numbers": missing_part_numbers,
                    "missing_categories": missing_categories,
                    "message": (
                        f"Ожидается подтверждение "
                        f"{len(missing_part_numbers) + len(missing_categories)} позиций."
                    ),
                }

            print("   ✅ Все модели найдены, продолжаем обработку...")
            result_data = []

            serial_cursor = {}
            imei_cursor = {}

            for item in items:
                part_number = item.get("part_number", "")
                description = item.get("description", "")

                product = products_by_pn.get(part_number)

                category = None
                if product and product.category_id:
                    category = next((c for c in categories if c.id == product.category_id), None)

                if not category:
                    from app.services.model_detector import detect_category
                    category = detect_category(description, categories)

                color = None
                if product and product.color_id:
                    color = next((c for c in colors if c.id == product.color_id), None)
                else:
                    for c in colors:
                        if c.eng and c.eng in description:
                            color = c
                            break

                if product and product.custom_name_ru:
                    custom_ru_with_color = product.custom_name_ru

                    sorted_colors = sorted(
                        color_mapping.items(),
                        key=lambda kv: len(kv[0] or ""),
                        reverse=True,
                    )

                    for eng_color, rus_color in sorted_colors:
                        if not eng_color:
                            continue
                        if re.search(rf'\b{re.escape(eng_color)}\b', custom_ru_with_color):
                            custom_ru_with_color = re.sub(
                                rf'\b{re.escape(eng_color)}\b',
                                f'"{rus_color}"',
                                custom_ru_with_color,
                                count=1,
                            )
                            break

                    name_with_article = f"{custom_ru_with_color} ({part_number})"
                    if category and category.prefix_ru:
                        transformed_name = f"{category.prefix_ru} {name_with_article} / {description}"
                    else:
                        transformed_name = f"{name_with_article} / {description}"
                else:
                    transformed_name = transform_product_name(
                        description=description,
                        category=category,
                        color=color,
                        color_mapping=color_mapping,
                    )

                qty = item.get("qty", 0) or 0

                is_imei = bool(category and category.serial_source == "imei_1")
                source_dict = imei_dict if is_imei else serials_dict
                cursor = imei_cursor if is_imei else serial_cursor

                all_serials = source_dict.get(part_number, [])
                start = cursor.get(part_number, 0)
                serials = all_serials[start:start + qty] if qty > 0 else []
                cursor[part_number] = start + len(serials)

                cleaned_serials = [clean_serial(s, category, product) for s in serials]

                if qty > 0:
                    missing = qty - len(cleaned_serials)
                    if missing > 0:
                        cleaned_serials.extend(["N/A"] * missing)

                serials_str = "\n".join(cleaned_serials) if cleaned_serials else "Не заполняется"

                if len(serials) != qty:
                    print(f"⚠️ Расхождение: {part_number} - инвойс: {qty}, серийников: {len(serials)}")

                result_data.append({
                    "name": transformed_name,
                    "model": item.get("model_number", ""),
                    "coo": item.get("coo", ""),
                    "article": item.get("part_number", ""),
                    "serials": serials_str,
                    "qty": item.get("qty", 0),
                    "price": item.get("price", 0),
                    "total": item.get("total", 0),
                })

            # Проверка «хвостов» серийников, которые не попали в спецификацию
            for pn, all_serials in serials_dict.items():
                used = serial_cursor.get(pn, 0)
                if used < len(all_serials):
                    print(f"ℹ️ {pn}: не использовано {len(all_serials) - used} серийников из манифеста")
            for pn, all_codes in imei_dict.items():
                used = imei_cursor.get(pn, 0)
                if used < len(all_codes):
                    print(f"ℹ️ {pn}: не использовано {len(all_codes) - used} IMEI из манифеста")

            spec_number_for_name = (session.spec_number or "").strip() or session_id[:8]
            output_path = f"/app/output/Specification_{spec_number_for_name}.xlsx"
            print(f"📊 Генерируем спецификацию: {output_path}")

            spec_date = invoice_date - timedelta(days=1) if invoice_date else datetime.now()

            generate_specification(
                template_path=session.template_file,
                data=result_data,
                spec_number=session.spec_number or "",
                invoice_date=invoice_date,
                invoice_number=invoice_number,
                output_path=output_path,
            )

            if not os.path.exists(output_path):
                raise Exception(f"Файл спецификации не был создан: {output_path}")

            print(f"✅ Спецификация создана: {output_path}")

            session.status = "completed"
            session.result_file = output_path
            session.total_items = len(items)
            session.processed_items = len(result_data)
            session.invoice_date = invoice_date
            session.spec_date = spec_date
            session.errors = None  # очищаем прошлые ошибки при успехе
            db.commit()

            print(f"✅ Сессия {session_id} завершена")

            # Удаляем временные файлы (не трогаем template_file!)
            for file_path in (session.invoice_file, session.manifest_file):
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🗑️ Удален временный файл: {file_path}")
                    except Exception as e:
                        print(f"❌ Не удалось удалить {file_path}: {e}")

            return {"status": "completed", "session_id": session_id, "items": len(result_data)}

    except SoftTimeLimitExceeded:
        print(f"⏱️ Soft time limit превышен для {session_id}")
        _handle_soft_time_limit(session_id)
        raise

    except Exception as e:
        print(f"❌ Ошибка обработки {session_id}: {e}")
        traceback.print_exc()
        _mark_session_error(session_id, str(e))
        raise


# ============================================================
# cleanup_old_files
# ============================================================
@celery_app.task(name="cleanup_old_files")
def cleanup_old_files():
    import time

    PENDING_TTL_DAYS = 3
    SESSION_TTL_DAYS = 3
    FILE_TTL_HOURS = 24

    now = datetime.now(timezone.utc)

    # 1. Удаление старых файлов
    directories = ["/app/uploads", "/app/templates", "/app/output"]
    deleted_files = 0
    threshold_time = time.time() - FILE_TTL_HOURS * 3600

    for directory in directories:
        if not os.path.exists(directory):
            continue
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if not os.path.isfile(filepath):
                continue
            if os.path.getmtime(filepath) >= threshold_time:
                continue
            try:
                os.remove(filepath)
                deleted_files += 1
                print(f"🗑️ Удален файл: {filename}")
            except Exception as e:
                print(f"❌ Не удалось удалить файл {filename}: {e}")

    # 2. Работа с БД
    deleted_sessions = 0
    skipped_pending = {"models": 0, "weights": 0, "gtins": 0}
    pending_cutoff = now - timedelta(days=PENDING_TTL_DAYS)
    session_cutoff = now - timedelta(days=SESSION_TTL_DAYS)

    try:
        with SessionLocal() as db:
            # 2.1 Автоскип pending старше TTL
            n = (
                db.query(PendingModel)
                .filter(
                    PendingModel.status == "pending",
                    PendingModel.created_at < pending_cutoff,
                )
                .update({"status": "skipped", "updated_at": now}, synchronize_session=False)
            )
            skipped_pending["models"] = n or 0

            n = (
                db.query(PendingWeight)
                .filter(
                    PendingWeight.status == "pending",
                    PendingWeight.created_at < pending_cutoff,
                )
                .update({"status": "skipped", "updated_at": now}, synchronize_session=False)
            )
            skipped_pending["weights"] = n or 0

            n = (
                db.query(PendingGtin)
                .filter(
                    PendingGtin.status == "pending",
                    PendingGtin.created_at < pending_cutoff,
                )
                .update({"status": "skipped", "updated_at": now}, synchronize_session=False)
            )
            skipped_pending["gtins"] = n or 0

            db.commit()

            if any(skipped_pending.values()):
                print(
                    f"⏭️ Автоскип pending старше {PENDING_TTL_DAYS} дн.: "
                    f"models={skipped_pending['models']}, "
                    f"weights={skipped_pending['weights']}, "
                    f"gtins={skipped_pending['gtins']}"
                )

            # 2.2 Помечаем зависшие сессии как error (с сохранением исходного статуса)
            stuck_statuses = ("pending_approval", "pending_weights", "processing")
            stuck_sessions = (
                db.query(ProcessingSession)
                .filter(
                    ProcessingSession.created_at < session_cutoff,
                    ProcessingSession.status.in_(stuck_statuses),
                )
                .all()
            )
            for s in stuck_sessions:
                old_status = s.status
                s.status = "error"
                s.errors = (
                    f"Автоматически отменено: сессия зависла в "
                    f"'{old_status}' более {SESSION_TTL_DAYS} дней"
                )
                print(f"⚠️ Сессия {s.session_id[:8]} помечена как error (была '{old_status}')")

            db.commit()

            # 2.3 Удаление старых сессий без активных pending
            old_sessions = (
                db.query(ProcessingSession)
                .filter(ProcessingSession.created_at < session_cutoff)
                .all()
            )

            for session in old_sessions:
                sid = session.session_id

                has_models = (
                    db.query(PendingModel.id)
                    .filter(PendingModel.session_id == sid, PendingModel.status == "pending")
                    .first() is not None
                )
                has_weights = (
                    db.query(PendingWeight.id)
                    .filter(PendingWeight.session_id == sid, PendingWeight.status == "pending")
                    .first() is not None
                )
                has_gtins = (
                    db.query(PendingGtin.id)
                    .filter(PendingGtin.session_id == sid, PendingGtin.status == "pending")
                    .first() is not None
                )

                if has_models or has_weights or has_gtins:
                    print(
                        f"⏭️ Пропуск сессии {sid[:8]} — есть pending "
                        f"(models={has_models}, weights={has_weights}, gtins={has_gtins})"
                    )
                    continue

                db.delete(session)
                deleted_sessions += 1
                print(f"🗑️ Удалена сессия: {sid[:8]}")

            db.commit()

    except SoftTimeLimitExceeded:
        raise
    except Exception as e:
        print(f"❌ Ошибка очистки сессий: {e}")
        traceback.print_exc()

    return (
        f"🗑️ Удалено файлов: {deleted_files}, сессий: {deleted_sessions}; "
        f"автоскип pending: models={skipped_pending['models']}, "
        f"weights={skipped_pending['weights']}, "
        f"gtins={skipped_pending['gtins']}"
    )


# ============================================================
# process_packing_list
# ============================================================
@celery_app.task(name="process_packing_list")
def process_packing_list(session_id: str):
    print(f"🔄 Начинаем обработку Packing List {session_id}")

    try:
        with SessionLocal() as db:
            session = _get_session_or_none(db, session_id)
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            if session.status == "completed" and session.result_file:
                print(f"⏭️ Packing List {session_id} уже завершён, пропускаем")
                return {"status": "completed", "session_id": session_id, "message": "already completed"}

            from app.services.packing_list_parser import (
                parse_packing_list,
                get_product_by_part_number,
                distribute_gross_across_pallets,
            )

            data = parse_packing_list(session.invoice_file)
            items = data.get("items", [])
            print(f"   Найдено позиций: {len(items)}")

            pallet_groups = {}
            for item in items:
                group_id = (
                    item.get("group_id")
                    or item.get("pallet_no")
                    or item.get("box_no")
                    or "1"
                )
                group_id = str(group_id)
                pallet_groups.setdefault(group_id, []).append(item)

            print(f"   Найдено групп (паллет/коробок): {len(pallet_groups)}")

            all_part_numbers = {item.get("part_number") for item in items if item.get("part_number")}

            part_weights = {}
            missing_parts = []
            # Кэш product/model_number, чтобы не звать get_product_by_part_number дважды
            product_cache = {}

            for pn in sorted(all_part_numbers):
                product, model_number = get_product_by_part_number(db, pn)
                product_cache[pn] = (product, model_number)

                description = None
                for item in items:
                    if item.get("part_number") == pn:
                        description = item.get("description_raw")
                        break

                known_weight, source, _ = resolve_weight_extended(
                    db,
                    part_number=pn,
                    model_number=(product.model_number if product else None),
                    description=description,
                )

                if known_weight and known_weight > 0:
                    part_weights[pn] = float(known_weight)
                    print(f"   ✓ {pn}: {known_weight:.4f} ← {source}")
                else:
                    missing_parts.append(pn)
                    print(f"   ✗ {pn}: вес не найден в БД")

            if missing_parts:
                print(f"   ⚠️ Артикулов без веса: {len(missing_parts)}")

                # Идемпотентность: не плодим дубли PendingWeight при повторном запуске
                for pn in missing_parts:
                    product, model_number = product_cache[pn]

                    total_qty = 0
                    first_pallet = None
                    first_box = None
                    for item in items:
                        if item.get("part_number") == pn:
                            total_qty += item.get("qty", 0) or 0
                            if first_pallet is None and item.get("pallet_no"):
                                first_pallet = item.get("pallet_no")
                            if first_box is None and item.get("box_no"):
                                first_box = item.get("box_no")

                    existing = (
                        db.query(PendingWeight)
                        .filter(
                            PendingWeight.session_id == session_id,
                            PendingWeight.part_number == pn,
                            PendingWeight.status == "pending",
                        )
                        .first()
                    )
                    if existing:
                        existing.qty = total_qty
                        existing.model_number = product.model_number if product else model_number
                        existing.pallet_no = first_pallet
                        existing.box_no = first_box
                    else:
                        db.add(
                            PendingWeight(
                                session_id=session_id,
                                part_number=pn,
                                model_number=(product.model_number if product else model_number),
                                qty=total_qty,
                                pallet_no=first_pallet,
                                box_no=first_box,
                                suggested_weight=None,
                                status="pending",
                            )
                        )

                db.commit()
                session.status = "pending_weights"
                db.commit()

                return {
                    "status": "pending_weights",
                    "session_id": session_id,
                    "pending_count": len(missing_parts),
                    "pending_items": missing_parts,
                    "message": f"Найдено {len(missing_parts)} артикулов без веса. Добавьте вес.",
                }

            pallet_weights = {}
            for group_id, group_items in pallet_groups.items():
                pw = 0
                for it in group_items:
                    if it.get("pallet_weight"):
                        pw = float(it["pallet_weight"])
                        break
                pallet_weights[group_id] = pw

            print(f"   📦 Веса паллет: {pallet_weights}")

            try:
                pallet_groups = distribute_gross_across_pallets(
                    pallet_groups=pallet_groups,
                    pallet_weights=pallet_weights,
                    part_weights=part_weights,
                )
            except Exception as e:
                session.status = "error"
                session.errors = f"Ошибка распределения веса: {str(e)}"
                db.commit()
                print(f"❌ Ошибка распределения веса {session_id}: {e}")
                raise

            from app.services.packing_list_generator import generate_packing_list

            all_processed_items = []
            for group_items in pallet_groups.values():
                all_processed_items.extend(group_items)

            output_path = f"/app/output/{session_id}_packing_list.xlsx"
            generate_packing_list(
                items=all_processed_items,
                template_path=session.invoice_file,
                output_path=output_path,
                session_id=session_id,
            )

            session.status = "completed"
            session.result_file = output_path
            session.errors = None
            db.commit()

            print(f"✅ Packing List {session_id} завершён, обработано групп: {len(pallet_groups)}")
            return {"status": "completed", "session_id": session_id, "pallets": len(pallet_groups)}

    except SoftTimeLimitExceeded:
        print(f"⏱️ Soft time limit превышен для {session_id}")
        _handle_soft_time_limit(session_id)
        raise

    except Exception as e:
        print(f"❌ Ошибка обработки {session_id}: {e}")
        traceback.print_exc()
        _mark_session_error(session_id, str(e))
        raise


# ============================================================
# process_chestny_znak
# ============================================================
@celery_app.task(name="process_chestny_znak")
def process_chestny_znak(session_id: str):
    print(f"🔄 Начинаем обработку ЧЗ {session_id}")

    try:
        with SessionLocal() as db:
            session = _get_session_or_none(db, session_id)
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            if session.status == "completed" and session.result_file:
                print(f"⏭️ ЧЗ {session_id} уже завершён, пропускаем")
                return {"status": "completed", "session_id": session_id, "message": "already completed"}

            from app.services.chestny_znak_parser import parse_cz_codes
            from app.services.chestny_znak_generator import (
                generate_cz_specification,
                parse_spec_info,
            )

            print(f"📄 Парсим инвойс: {session.invoice_file}")
            invoice_data = parse_invoice(session.invoice_file)
            items = invoice_data.get("items", [])
            print(f"   Позиций в инвойсе: {len(items)}")

            print(f"📄 Парсим коды ЧЗ: {session.manifest_file}")
            cz_codes = parse_cz_codes(session.manifest_file)
            total_codes = sum(len(v) for v in cz_codes.values())
            print(f"   GTIN в ЧЗ: {len(cz_codes)}, всего кодов: {total_codes}")

            print(f"📄 Парсим спецификацию: {session.template_file}")
            spec_number, _, _ = parse_spec_info(session.template_file)
            print(f"   Номер спецификации: {spec_number}")

            output_path = f"/app/output/{session_id}_cz_spec.xlsx"
            generate_cz_specification(
                spec_template_path=session.template_file,
                output_path=output_path,
                cz_codes=cz_codes,
                invoice_data=invoice_data,
            )

            if not os.path.exists(output_path):
                raise Exception(f"Файл ЧЗ не был создан: {output_path}")

            session.status = "completed"
            session.result_file = output_path
            session.spec_number = spec_number
            session.errors = None
            db.commit()

            print(f"✅ ЧЗ-спецификация создана: {output_path}")
            return {"status": "completed", "session_id": session_id}

    except SoftTimeLimitExceeded:
        print(f"⏱️ Soft time limit превышен для {session_id}")
        _handle_soft_time_limit(session_id)
        raise

    except Exception as e:
        print(f"❌ Ошибка ЧЗ {session_id}: {e}")
        traceback.print_exc()
        _mark_session_error(session_id, str(e))
        raise


# ============================================================
# process_commercial_offer
# ============================================================
@celery_app.task(name="process_commercial_offer")
def process_commercial_offer(session_id: str):
    print(f"🔄 Начинаем генерацию КП {session_id}")

    try:
        with SessionLocal() as db:
            session = _get_session_or_none(db, session_id)
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            if session.status == "completed" and session.result_file:
                print(f"⏭️ КП {session_id} уже завершено, пропускаем")
                return {"status": "completed", "session_id": session_id, "message": "already completed"}

            from app.services.commercial_offer_generator import (
                generate_commercial_offer,
                parse_specification,
            )

            print(f"📄 Парсим спецификацию: {session.template_file}")
            spec_number, invoice_date, items = parse_specification(session.template_file)
            print(f"   Номер спецификации: {spec_number}")
            print(f"   Дата: {invoice_date}")
            print(f"   Позиций: {len(items)}")

            output_path = f"/app/output/{session_id}_co.xlsx"
            generate_commercial_offer(
                spec_path=session.template_file,
                output_path=output_path,
            )

            if not os.path.exists(output_path):
                raise Exception(f"Файл КП не был создан: {output_path}")

            session.status = "completed"
            session.result_file = output_path
            session.spec_number = spec_number
            session.errors = None
            db.commit()

            print(f"✅ КП создано: {output_path}")
            return {"status": "completed", "session_id": session_id}

    except SoftTimeLimitExceeded:
        print(f"⏱️ Soft time limit превышен для {session_id}")
        _handle_soft_time_limit(session_id)
        raise

    except Exception as e:
        print(f"❌ Ошибка КП {session_id}: {e}")
        traceback.print_exc()
        _mark_session_error(session_id, str(e))
        raise


# ============================================================
# process_cz_codes
# ============================================================
@celery_app.task(name="process_cz_codes")
def process_cz_codes(session_id: str):
    print(f"🔄 Начинаем подготовку кодов ЧЗ {session_id}")

    try:
        with SessionLocal() as db:
            session = _get_session_or_none(db, session_id)
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            if session.status == "completed" and session.result_file:
                print(f"⏭️ Коды ЧЗ {session_id} уже подготовлены, пропускаем")
                return {"status": "completed", "session_id": session_id, "message": "already completed"}

            from app.services.cz_codes_generator import generate_cz_codes_zip

            print(f"📄 Обрабатываем: {session.template_file}")
            zip_path, spec_number, files_info = generate_cz_codes_zip(
                cz_spec_path=session.template_file,
                output_dir="/app/output",
                session_id=session_id,
            )

            if not os.path.exists(zip_path):
                raise Exception(f"ZIP не был создан: {zip_path}")

            print(f"📦 Создано файлов: {len(files_info)}")
            for name, count in files_info.items():
                print(f"   - {name}: {count} кодов")

            session.status = "completed"
            session.result_file = zip_path
            session.spec_number = spec_number
            session.errors = None
            db.commit()

            print(f"✅ ZIP создан: {zip_path}")
            return {
                "status": "completed",
                "session_id": session_id,
                "files": files_info,
            }

    except SoftTimeLimitExceeded:
        print(f"⏱️ Soft time limit превышен для {session_id}")
        _handle_soft_time_limit(session_id)
        raise

    except Exception as e:
        print(f"❌ Ошибка {session_id}: {e}")
        traceback.print_exc()
        _mark_session_error(session_id, str(e))
        raise