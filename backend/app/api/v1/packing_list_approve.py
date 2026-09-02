# Добавь в конец approve_weight после проверки remaining

    if not remaining:
        # Генерируем результат
        from app.services.packing_list_generator import generate_packing_list
        from app.services.packing_list_parser import parse_packing_list, get_product_by_part_number
        
        # Получаем сессию
        session_stmt = select(ProcessingSession).where(
            ProcessingSession.session_id == pending.session_id
        )
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()
        
        if session:
            # Парсим файл заново
            data = parse_packing_list(session.invoice_file)
            items = data.get("items", [])
            
            # Добавляем веса из БД
            processed_items = []
            for item in items:
                part_number = item.get("part_number")
                product, model_number = get_product_by_part_number(db, part_number)
                
                if product and product.weight:
                    qty = item.get("qty", 0)
                    item["weight_per_item"] = product.weight
                    item["total_net"] = product.weight * qty
                    item["model_number"] = product.model_number
                    processed_items.append(item)
            
            output_path = f"/app/output/{session.session_id}_packing_list.xlsx"
            generate_packing_list(
                items=processed_items,
                template_path=session.invoice_file,
                output_path=output_path,
                session_id=session.session_id
            )
            session.result_file = output_path
            session.status = "completed"
            await db.commit()
