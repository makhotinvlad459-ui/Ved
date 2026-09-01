import openpyxl
from datetime import datetime
from typing import List, Dict, Any, Optional


def parse_invoice(file_path: str) -> Dict[str, Any]:
    """
    Парсинг инвойса
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    
    # ============================================
    # 1. Находим дату и номер инвойса
    # ============================================
    invoice_date = None
    invoice_number = None
    
    for row in ws.iter_rows(max_row=30):
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                val = cell.value.strip()
                
                # Ищем Reference (номер инвойса) — данные в колонке 13
                if "Reference" in val:
                    ref_cell = ws.cell(row=cell.row, column=14)
                    if ref_cell.value:
                        invoice_number = str(ref_cell.value).strip()
                        print(f"   📝 Найден номер инвойса: {invoice_number}")
                
                # Ищем Date (дата инвойса) — данные в колонке 13
                if "Date" in val:
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
    
    # ============================================
    # 2. Находим строку с заголовками
    # ============================================
    header_row = None
    for row in ws.iter_rows(min_row=1, max_row=30):
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                val = cell.value.strip()
                if "Model" in val or "P/N" in val or "Description" in val:
                    header_row = cell.row
                    break
        if header_row:
            break
    
    if not header_row:
        for row_idx in range(20, 30):
            row = ws[row_idx]
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    if "Model" in cell.value or "P/N" in cell.value:
                        header_row = row_idx
                        break
            if header_row:
                break
    
    items = []
    if header_row:
        header_cells = {}
        for col_idx, cell in enumerate(ws[header_row], 1):
            if cell.value:
                val = str(cell.value).strip()
                if "Model" in val:
                    header_cells["model"] = col_idx
                elif "P/N" in val or "Part" in val:
                    header_cells["part"] = col_idx
                elif "Description" in val or "description" in val:
                    header_cells["desc"] = col_idx
                elif "Qty" in val or "Quantity" in val:
                    header_cells["qty"] = col_idx
                elif "COO" in val or "Country" in val:
                    header_cells["coo"] = col_idx
                elif "UPC" in val or "code" in val:
                    header_cells["upc"] = col_idx
                elif "Price" in val or "Unit" in val:
                    header_cells["price"] = col_idx
                elif "Total" in val:
                    header_cells["total"] = col_idx
        
        for row in ws.iter_rows(min_row=header_row + 1):
            model_cell = row[header_cells.get("model", 1) - 1]
            if not model_cell.value or not str(model_cell.value).strip():
                break
            
            try:
                item = {
                    "model_number": str(model_cell.value).strip(),
                    "part_number": str(row[header_cells.get("part", 3) - 1].value or "").strip(),
                    "description": str(row[header_cells.get("desc", 5) - 1].value or "").strip(),
                    "qty": int(row[header_cells.get("qty", 20) - 1].value or 0),
                    "coo": str(row[header_cells.get("coo", 27) - 1].value or "").strip(),
                    "upc": str(row[header_cells.get("upc", 28) - 1].value or "").strip(),
                    "price": float(row[header_cells.get("price", 29) - 1].value or 0),
                    "total": float(row[header_cells.get("total", 33) - 1].value or 0),
                }
                items.append(item)
            except Exception as e:
                print(f"⚠️ Ошибка парсинга строки: {e}")
                continue
    
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