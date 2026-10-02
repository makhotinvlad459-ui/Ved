# backend/app/celery/tasks.py
from .worker import celery_app
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime, timedelta

from app.models import ProcessingSession, Product, Category, Color, PendingModel
from app.services.parser import parse_invoice, parse_manifest
from app.services.transformer import transform_product_name, clean_serial
from app.services.generator import generate_specification
from app.services.model_detector import save_pending_models, get_pending_models_by_session


def resolve_weight(db, part_number=None, model_number=None):
    """
    Единая точка поиска веса.
    1. Product.weight по part_number
    2. Вес "сестринского" Product с тем же model_number
    3. История PendingWeight(approved) по part_number
    4. История PendingWeight(approved) по model_number
    """
    from app.models import Product, PendingWeight

    product = None
    if part_number:
        product = db.query(Product).filter(Product.part_number == part_number).first()

    if product and product.weight:
        return float(product.weight), "product", product

    effective_model = (product.model_number if product and product.model_number else None) or model_number

    if effective_model:
        sibling = db.query(Product).filter(
            Product.model_number == effective_model,
            Product.weight.isnot(None),
            Product.weight > 0,
        ).first()
        if sibling:
            return float(sibling.weight), f"model:{effective_model}", product

    if part_number:
        pw = db.query(PendingWeight).filter(
            PendingWeight.part_number == part_number,
            PendingWeight.status == "approved",
            PendingWeight.custom_weight.isnot(None),
        ).order_by(PendingWeight.updated_at.desc()).first()
        if pw:
            return float(pw.custom_weight), "pending_part", product

    if effective_model:
        pw = db.query(PendingWeight).filter(
            PendingWeight.model_number == effective_model,
            PendingWeight.status == "approved",
            PendingWeight.custom_weight.isnot(None),
        ).order_by(PendingWeight.updated_at.desc()).first()
        if pw:
            return float(pw.custom_weight), "pending_model", product

    return None, None, product


@celery_app.task(name="process_invoice")
def process_invoice(session_id: str):
    print(f"🔄 Начинаем обработку сессии {session_id}")

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:apple_samsung_2024@postgres:5432/ved")
    sync_engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=sync_engine)

    try:
        with SessionLocal() as db:
            from app.models import ProcessingSession
            stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
            result = db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            print(f"📄 Парсим инвойс: {session.invoice_file}")
            invoice_data = parse_invoice(session.invoice_file)
            invoice_date = invoice_data.get("invoice_date", datetime.now())
            invoice_number = invoice_data.get("invoice_number", "")
            items = invoice_data.get("items", [])
            print(f"   Найдено позиций: {len(items)}")
            print(f"   Номер инвойса: {invoice_number}")
            print(f"   Дата инвойса: {invoice_date}")

            print(f"📄 Парсим манифест: {session.manifest_file}")
            manifest_data = parse_manifest(session.manifest_file)
            serials_dict = manifest_data.get("serials", {})
            imei_dict = manifest_data.get("imei", {})
            print(f"   Найдено серийников: {sum(len(v) for v in serials_dict.values())}")
            print(f"   Найдено IMEI: {sum(len(v) for v in imei_dict.values())}")

            categories = db.query(Category).all()
            colors = db.query(Color).all()
            color_mapping = {c.eng: c.rus for c in colors}
            category_map = {c.name: c for c in categories}

            print(f"🔍 Проверяем новые модели...")
            pending_models = save_pending_models(
                items=items,
                categories=categories,
                colors=colors,
                db=db,
                session_id=session_id
            )

            # === Проверяем, что для ВСЕХ товаров инвойса есть Product в БД ===
            missing_part_numbers = []
            for item in items:
                pn = item.get("part_number", "")
                if not pn:
                    continue
                exists = db.query(Product).filter(Product.part_number == pn).first()
                if not exists:
                    missing_part_numbers.append(pn)

            if pending_models or missing_part_numbers:
                if pending_models:
                    print(f"   Найдено {len(pending_models)} новых моделей")
                if missing_part_numbers:
                    print(f"   ⚠️ Товаров без Product в БД: {len(missing_part_numbers)} → {missing_part_numbers}")
                db.commit()
                session.status = "pending_approval"
                db.commit()
                print(f"⏳ Сессия {session_id} ожидает подтверждения новых моделей")
                pending_list = get_pending_models_by_session(db, session_id)
                return {
                    "status": "pending_approval",
                    "session_id": session_id,
                    "new_models": pending_list,
                    "missing_part_numbers": missing_part_numbers,
                    "message": f"Ожидается подтверждение {len(missing_part_numbers)} новых моделей."
                }

            print(f"   ✅ Все модели найдены в БД, продолжаем обработку...")
            result_data = []

            # === Курсоры для распределения серийников между строками
            #     с одинаковым part_number (чтобы не было дублей) ===
            serial_cursor = {}   # для serial_number
            imei_cursor = {}     # для imei_1

            for item in items:
                part_number = item.get("part_number", "")
                description = item.get("description", "")

                product = db.query(Product).filter(
                    Product.part_number == part_number
                ).first()

                category = None
                if product and product.category_id:
                    category = db.query(Category).filter(Category.id == product.category_id).first()

                if not category:
                    from app.services.model_detector import detect_category
                    category = detect_category(description, categories)

                color = None
                if product and product.color_id:
                    color = db.query(Color).filter(Color.id == product.color_id).first()
                else:
                    for c in colors:
                        if c.eng in description:
                            color = c
                            break

                if product and product.custom_name_ru:
                    # custom_name_ru может содержать английские цвета.
                    # Ищем САМОЕ ДЛИННОЕ совпадение, заменяем ТОЛЬКО его.
                    # Остальные цвета не трогаем — чтобы не было "Navy Blue" → "Тёмно-синий" "Голубой".
                    import re as _re
                    custom_ru_with_color = product.custom_name_ru

                    sorted_colors = sorted(
                        color_mapping.items(),
                        key=lambda kv: len(kv[0] or ""),
                        reverse=True,
                    )

                    for eng_color, rus_color in sorted_colors:
                        if not eng_color:
                            continue
                        # \b — граница слова, чтобы "Olive" не находилось внутри "OliveGreen"
                        if _re.search(rf'\b{_re.escape(eng_color)}\b', custom_ru_with_color):
                            custom_ru_with_color = _re.sub(
                                rf'\b{_re.escape(eng_color)}\b',
                                f'"{rus_color}"',
                                custom_ru_with_color,
                                count=1,   # только первое
                            )
                            break   # ВЫХОДИМ, остальные цвета не трогаем

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
                        color_mapping=color_mapping
                    )

                # === Распределяем серийники между строками с одинаковым part_number ===
                qty = item.get("qty", 0) or 0

                is_imei = bool(category and category.serial_source == "imei_1")
                source_dict = imei_dict if is_imei else serials_dict
                cursor = imei_cursor if is_imei else serial_cursor

                all_serials = source_dict.get(part_number, [])
                start = cursor.get(part_number, 0)
                serials = all_serials[start:start + qty] if qty > 0 else []
                cursor[part_number] = start + len(serials)

                cleaned_serials = [clean_serial(s, category, product) for s in serials]

                # Заглушка для недостающих серийников
                if qty > 0:
                    missing = qty - len(cleaned_serials)
                    if missing > 0:
                        cleaned_serials.extend(["N/A"] * missing)

                serials_str = "\n".join(cleaned_serials) if cleaned_serials else "Не заполняется"

                if len(serials) != qty:
                    print(f"⚠️ Расхождение: {part_number} - инвойс: {qty}, серийников: {len(serials)}")

                result_item = {
                    "name": transformed_name,
                    "model": item.get("model_number", ""),
                    "coo": item.get("coo", ""),
                    "article": item.get("part_number", ""),
                    "serials": serials_str,
                    "qty": item.get("qty", 0),
                    "price": item.get("price", 0),
                    "total": item.get("total", 0)
                }
                result_data.append(result_item)

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
                output_path=output_path
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
            db.commit()

            print(f"✅ Сессия {session_id} завершена")

            upload_files = [session.invoice_file, session.manifest_file]
            for file_path in upload_files:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🗑️ Удален временный файл: {file_path}")
                    except Exception as e:
                        print(f"❌ Не удалось удалить {file_path}: {e}")

            return {"status": "completed", "session_id": session_id, "items": len(result_data)}

    except Exception as e:
        print(f"❌ Ошибка обработки {session_id}: {e}")
        import traceback
        traceback.print_exc()

        with SessionLocal() as db:
            from app.models import ProcessingSession
            stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
            result = db.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                session.status = "error"
                session.errors = str(e)
                db.commit()

        raise e
    finally:
        sync_engine.dispose()


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files():
    import os
    import time

    directories = ['/app/uploads', '/app/templates', '/app/output']
    deleted = 0
    threshold = time.time() - 86400

    for directory in directories:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < threshold:
                        os.remove(filepath)
                        deleted += 1
                        print(f'🗑️ Удален: {filename}')

    return f'🗑️ Удалено {deleted} файлов старше 1 дня'


@celery_app.task(name="process_packing_list")
def process_packing_list(session_id: str):
    print(f"🔄 Начинаем обработку Packing List {session_id}")

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:apple_samsung_2024@postgres:5432/ved")
    sync_engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=sync_engine)

    try:
        with SessionLocal() as db:
            from app.models import ProcessingSession, Product, PendingWeight

            stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
            result = db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            from app.services.packing_list_parser import parse_packing_list, get_product_by_part_number
            data = parse_packing_list(session.invoice_file)
            items = data.get("items", [])

            print(f"   Найдено позиций: {len(items)}")

            # Группируем по паллетам
            pallet_groups = {}
            for item in items:
                pallet = item.get("pallet_no", "1")
                if pallet not in pallet_groups:
                    pallet_groups[pallet] = []
                pallet_groups[pallet].append(item)

            all_processed_items = []
            pending_items = []

            # === ОБРАБОТКА КАЖДОЙ ПАЛЛЕТЫ ===
            for pallet, pallet_items in pallet_groups.items():
                pallet_weight = pallet_items[0].get("pallet_weight", 0)

                for item in pallet_items:
                    part_number = item.get("part_number")
                    qty = item.get("qty", 0)

                    product, model_number = get_product_by_part_number(db, part_number)

                    known_weight, source, product = resolve_weight(
                        db, part_number, model_number
                    )

                    if known_weight:
                        if product and not product.weight:
                            product.weight = known_weight
                            print(f"   ♻️ Product {part_number}: вес {known_weight} ← {source}")

                        item["net"] = known_weight * qty
                        item["weight_per_item"] = known_weight
                        item["model_number"] = (
                            product.model_number if product and product.model_number
                            else model_number
                        )
                        item["description"] = (
                            product.description if product
                            else item.get("description_raw")
                        )
                        item["category_name"] = (
                            product.category.name
                            if product and product.category else None
                        )
                        item["color_name"] = (
                            product.color.rus
                            if product and product.color else None
                        )
                    else:
                        pending_items.append({
                            **item,
                            "model_number": model_number
                        })

                if pallet_weight > 0:
                    from app.services.packing_list_parser import redistribute_gross
                    pallet_items = redistribute_gross(pallet_items, pallet_weight)

                all_processed_items.extend(pallet_items)

            # === ЕСЛИ ЕСТЬ ТОВАРЫ БЕЗ ВЕСА — ОСТАНАВЛИВАЕМСЯ ===
            if pending_items:
                seen_parts = set()
                unique_pending = []
                for item in pending_items:
                    pn = item.get("part_number")
                    if pn and pn not in seen_parts:
                        seen_parts.add(pn)
                        unique_pending.append(item)

                for item in unique_pending:
                    pending_weight = PendingWeight(
                        session_id=session_id,
                        part_number=item.get("part_number"),
                        model_number=item.get("model_number"),
                        qty=item.get("qty", 0),
                        pallet_no=item.get("pallet_no"),
                        box_no=item.get("box_no"),
                        suggested_weight=item.get("weight_per_1"),
                        status="pending"
                    )
                    db.add(pending_weight)

                db.commit()
                session.status = "pending_weights"
                db.commit()
                return {
                    "status": "pending_weights",
                    "session_id": session_id,
                    "pending_count": len(unique_pending),
                    "pending_items": [item.get("part_number") for item in unique_pending],
                    "message": f"Найдено {len(unique_pending)} моделей без веса. Добавьте вес."
                }

            # === ГЕНЕРИРУЕМ ФИНАЛЬНЫЙ PACKING LIST ===
            from app.services.packing_list_generator import generate_packing_list

            output_path = f"/app/output/{session_id}_packing_list.xlsx"
            generate_packing_list(
                items=all_processed_items,
                template_path=session.invoice_file,
                output_path=output_path,
                session_id=session_id
            )

            session.status = "completed"
            session.result_file = output_path
            db.commit()

            print(f"✅ Packing List {session_id} завершён, обработано паллет: {len(pallet_groups)}")
            return {"status": "completed", "session_id": session_id, "pallets": len(pallet_groups)}

    except Exception as e:
        print(f"❌ Ошибка обработки {session_id}: {e}")
        import traceback
        traceback.print_exc()

        with SessionLocal() as db:
            session = db.query(ProcessingSession).filter(
                ProcessingSession.session_id == session_id
            ).first()
            if session:
                session.status = "error"
                session.errors = str(e)
                db.commit()

        raise e
    finally:
        sync_engine.dispose()


@celery_app.task(name="process_chestny_znak")
def process_chestny_znak(session_id: str):
    print(f"🔄 Начинаем обработку ЧЗ {session_id}")

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:apple_samsung_2024@postgres:5432/ved")
    sync_engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=sync_engine)

    try:
        with SessionLocal() as db:
            stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
            session = db.execute(stmt).scalar_one_or_none()
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            from app.services.parser import parse_invoice
            from app.services.chestny_znak_parser import parse_cz_codes
            from app.services.chestny_znak_generator import (
                generate_cz_specification, parse_spec_info
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
            db.commit()

            print(f"✅ ЧЗ-спецификация создана: {output_path}")
            return {"status": "completed", "session_id": session_id}

    except Exception as e:
        print(f"❌ Ошибка ЧЗ {session_id}: {e}")
        import traceback
        traceback.print_exc()
        with SessionLocal() as db:
            session = db.query(ProcessingSession).filter(
                ProcessingSession.session_id == session_id
            ).first()
            if session:
                session.status = "error"
                session.errors = str(e)
                db.commit()
        raise e
    finally:
        sync_engine.dispose()

@celery_app.task(name="process_commercial_offer")
def process_commercial_offer(session_id: str):
    print(f"🔄 Начинаем генерацию КП {session_id}")

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:apple_samsung_2024@postgres:5432/ved")
    sync_engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=sync_engine)

    try:
        with SessionLocal() as db:
            stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
            session = db.execute(stmt).scalar_one_or_none()
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

            from app.services.commercial_offer_generator import (
                generate_commercial_offer, parse_specification
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
            db.commit()

            print(f"✅ КП создано: {output_path}")
            return {"status": "completed", "session_id": session_id}

    except Exception as e:
        print(f"❌ Ошибка КП {session_id}: {e}")
        import traceback
        traceback.print_exc()
        with SessionLocal() as db:
            session = db.query(ProcessingSession).filter(
                ProcessingSession.session_id == session_id
            ).first()
            if session:
                session.status = "error"
                session.errors = str(e)
                db.commit()
        raise e
    finally:
        sync_engine.dispose()

@celery_app.task(name="process_cz_codes")
def process_cz_codes(session_id: str):
    print(f"🔄 Начинаем подготовку кодов ЧЗ {session_id}")

    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:apple_samsung_2024@postgres:5432/ved")
    sync_engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=sync_engine)

    try:
        with SessionLocal() as db:
            stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
            session = db.execute(stmt).scalar_one_or_none()
            if not session:
                print(f"❌ Сессия {session_id} не найдена")
                return {"error": "Session not found"}

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
            db.commit()

            print(f"✅ ZIP создан: {zip_path}")
            return {
                "status": "completed",
                "session_id": session_id,
                "files": files_info,
            }

    except Exception as e:
        print(f"❌ Ошибка {session_id}: {e}")
        import traceback
        traceback.print_exc()
        with SessionLocal() as db:
            session = db.query(ProcessingSession).filter(
                ProcessingSession.session_id == session_id
            ).first()
            if session:
                session.status = "error"
                session.errors = str(e)
                db.commit()
        raise e
    finally:
        sync_engine.dispose()