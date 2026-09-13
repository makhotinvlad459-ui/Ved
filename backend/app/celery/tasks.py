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

            # === НОВОЕ: проверяем, что для ВСЕХ товаров инвойса есть Product в БД ===
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
                    # Используем общие правила из model_detector
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
                    name_with_article = f"{product.custom_name_ru} ({part_number})"
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

                serials = []
                if category and category.serial_source == "imei_1":
                    serials = imei_dict.get(part_number, [])
                else:
                    serials = serials_dict.get(part_number, [])

                cleaned_serials = [clean_serial(s, category, product) for s in serials]
                serials_str = "\n".join(cleaned_serials) if cleaned_serials else "Не заполняется"

                if len(serials) != item.get("qty", 0):
                    print(f"⚠️ Расхождение: {part_number} - инвойс: {item.get('qty')}, серийников: {len(serials)}")

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

            output_path = f"/app/output/{session_id}_specification.xlsx"
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

            pallet_groups = {}
            for item in items:
                pallet = item.get("pallet_no", "1")
                if pallet not in pallet_groups:
                    pallet_groups[pallet] = []
                pallet_groups[pallet].append(item)

            all_processed_items = []
            pending_items = []

            for pallet, pallet_items in pallet_groups.items():
                pallet_weight = pallet_items[0].get("pallet_weight", 0)

                for item in pallet_items:
                    part_number = item.get("part_number")
                    qty = item.get("qty", 0)

                    product, model_number = get_product_by_part_number(db, part_number)

                    if product and product.weight:
                        net = product.weight * qty
                        item["net"] = net
                        item["weight_per_item"] = product.weight
                        item["model_number"] = product.model_number
                        item["description"] = product.description
                        item["category_name"] = product.category.name if product.category else None
                        item["color_name"] = product.color.rus if product.color else None
                    else:
                        pending_items.append({
                            **item,
                            "model_number": model_number
                        })

                if pending_items:
                    for item in pending_items:
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
                        "pending_count": len(pending_items),
                        "pending_items": [item.get("part_number") for item in pending_items],
                        "message": f"Найдено {len(pending_items)} моделей без веса. Добавьте вес."
                    }

                if pallet_weight > 0:
                    from app.services.packing_list_parser import redistribute_gross
                    pallet_items = redistribute_gross(pallet_items, pallet_weight)

                all_processed_items.extend(pallet_items)

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

            print(f"✅ Packing List {session_id} завершён")
            return {"status": "completed", "session_id": session_id}

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


