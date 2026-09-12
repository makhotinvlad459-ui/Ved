import openpyxl
from datetime import datetime
from typing import List, Dict, Any, Optional


def parse_invoice(file_path: str) -> Dict[str, Any]:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    
    # === Дата и номер ===
    invoice_date = None
    invoice_number = None
    
    for row in ws.iter_rows(max_row=30):
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                val = cell.value.strip()
                
                if "Reference" in val:
                    ref_cell = ws.cell(row=cell.row, column=14)
                    if ref_cell.value:
                        invoice_number = str(ref_cell.value).strip()
                        print(f"   📝 Найден номер инвойса: {invoice_number}")
                
                if val == "Date":
                    date_cell = ws.cell(row=cell.row, column=14)
                    if date_cell.value:
                        if isinstance(date_cell.value, datetime):
                            invoice_date = date_cell.value
                        elif isinstance(date_cell.value, str):
                            try:
                                invoice_date = datetime.strptime(date_cell.value, "%d.%m.%Y")
                            except:
                                try:
                                    invoice_date = datetime.strptime(date_cell.value, "%Y-%m-%d")
                                except:
                                    pass
                        print(f"   📝 Найдена дата инвойса: {invoice_date}")
                
                if invoice_date and invoice_number:
                    break
        if invoice_date and invoice_number:
            break
    
    # === Находим ВСЕ заголовки таблиц ===
    header_rows = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        has_model = False
        has_pn = False
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                val = cell.value.strip()
                if val == "Model":
                    has_model = True
                elif "P/N" in val:
                    has_pn = True
        if has_model and has_pn:
            header_rows.append(row[0].row)
    
    print(f"   📋 Найдено блоков: {len(header_rows)} (строки: {header_rows})")
    
    items = []
    
    for idx, header_row in enumerate(header_rows):
        # Определяем колонки
        header_cells = {}
        for col_idx, cell in enumerate(ws[header_row], 1):
            if cell.value:
                val = str(cell.value).strip()
                if val == "Model":
                    header_cells["model"] = col_idx
                elif "P/N" in val or val == "P/N":
                    header_cells["part"] = col_idx
                elif "Description" in val:
                    header_cells["desc"] = col_idx
                elif "Qty" in val:
                    header_cells["qty"] = col_idx
                elif "COO" in val:
                    header_cells["coo"] = col_idx
                elif "UPC" in val:
                    header_cells["upc"] = col_idx
                elif "Price" in val:
                    header_cells["price"] = col_idx
                elif "Total" in val:
                    header_cells["total"] = col_idx
        
        print(f"   📋 Блок {idx+1} (строка {header_row}): {header_cells}")
        
        # Определяем конец блока — либо следующий заголовок, либо конец файла
        if idx + 1 < len(header_rows):
            end_row = header_rows[idx + 1] - 1
        else:
            end_row = ws.max_row
        
        # Читаем строки блока
        for row in ws.iter_rows(min_row=header_row + 1, max_row=end_row):
            part_idx = header_cells.get("part", 4) - 1
            part_cell = row[part_idx] if part_idx < len(row) else None
            
            if not part_cell or not part_cell.value:
                continue
            
            part_number = str(part_cell.value).strip()
            
            if part_number.lower() in ["total", "итого", ""]:
                continue
            
            model_idx = header_cells.get("model", 2) - 1
            model_cell = row[model_idx] if model_idx < len(row) else None
            model_number = str(model_cell.value).strip() if model_cell and model_cell.value else ""
            
            desc_idx = header_cells.get("desc", 7) - 1
            desc_cell = row[desc_idx] if desc_idx < len(row) else None
            description = str(desc_cell.value).strip() if desc_cell and desc_cell.value else ""
            
            qty_idx = header_cells.get("qty", 21) - 1
            qty_cell = row[qty_idx] if qty_idx < len(row) else None
            qty = int(qty_cell.value or 0) if qty_cell else 0
            
            coo_idx = header_cells.get("coo", 28) - 1
            coo_cell = row[coo_idx] if coo_idx < len(row) else None
            coo = str(coo_cell.value).strip() if coo_cell and coo_cell.value else ""
            
            upc_idx = header_cells.get("upc", 29) - 1
            upc_cell = row[upc_idx] if upc_idx < len(row) else None
            upc = str(upc_cell.value).strip() if upc_cell and upc_cell.value else ""
            
            price_idx = header_cells.get("price", 30) - 1
            price_cell = row[price_idx] if price_idx < len(row) else None
            try:
                price = float(price_cell.value or 0) if price_cell else 0
            except:
                price = 0
            
            total_idx = header_cells.get("total", 34) - 1
            total_cell = row[total_idx] if total_idx < len(row) else None
            try:
                total = float(total_cell.value or 0) if total_cell else 0
            except:
                total = 0
            
            items.append({
                "model_number": model_number,
                "part_number": part_number,
                "description": description,
                "qty": qty,
                "coo": coo,
                "upc": upc,
                "price": price,
                "total": total
            })
    
    print(f"   ✅ Всего позиций: {len(items)}")
    
    return {
        "invoice_date": invoice_date,
        "invoice_number": invoice_number,
        "items": items
    }


def parse_manifest(file_path: str) -> Dict[str, List[str]]:
    """
    Парсинг манифеста
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    
    serials_by_part = {}
    imei_by_part = {}
    
    header_row = None
    for row in ws.iter_rows(min_row=1, max_row=10):
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                val = cell.value.strip()
                if "Part Number" in val or "Part" in val:
                    header_row = cell.row
                    break
        if header_row:
            break
    
    if header_row:
        part_col = None
        serial_col = None
        imei_col = None
        
        for col_idx, cell in enumerate(ws[header_row], 1):
            if cell.value:
                val = str(cell.value).strip()
                if "Part" in val:
                    part_col = col_idx
                elif "Serial" in val:
                    serial_col = col_idx
                elif "IMEI" in val:
                    imei_col = col_idx
        
        for row in ws.iter_rows(min_row=header_row + 1):
            if part_col and row[part_col - 1].value:
                part_number = str(row[part_col - 1].value).strip()
                
                if part_number not in serials_by_part:
                    serials_by_part[part_number] = []
                    imei_by_part[part_number] = []
                
                if serial_col and row[serial_col - 1].value:
                    serials_by_part[part_number].append(str(row[serial_col - 1].value).strip())
                
                if imei_col and row[imei_col - 1].value:
                    imei_by_part[part_number].append(str(row[imei_col - 1].value).strip())
    else:
        for row in ws.iter_rows(min_row=2):
            part_number = row[3].value
            if not part_number:
                break
            
            part_key = str(part_number).strip()
            
            if part_key not in serials_by_part:
                serials_by_part[part_key] = []
                imei_by_part[part_key] = []
            
            if row[4].value:
                serials_by_part[part_key].append(str(row[4].value).strip())
            if row[5].value:
                imei_by_part[part_key].append(str(row[5].value).strip())
    
    return {
        "serials": serials_by_part,
        "imei": imei_by_part
    }