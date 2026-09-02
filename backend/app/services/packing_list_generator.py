import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from typing import List, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


def generate_packing_list(
    items: List[Dict[str, Any]],
    template_path: str,
    output_path: str,
    session_id: str
) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    
    # === СТИЛИ ===
    header_font = Font(bold=True, size=10)
    header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    header_alignment = Alignment(horizontal='center', vertical='center')
    cell_alignment = Alignment(horizontal='center', vertical='center')
    left_alignment = Alignment(horizontal='left', vertical='center')
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # === ШАПКА ===
    ws.merge_cells('A1:I1')
    ws.cell(1, 1).value = "Packing List"
    ws.cell(1, 1).font = Font(bold=True, size=16)
    ws.cell(1, 1).alignment = Alignment(horizontal='center')
    
    # Тёмная полоса под заголовком (строка 2)
    dark_fill = PatternFill(start_color="333333", end_color="333333", fill_type="solid")
    for col in range(1, 10):
        cell = ws.cell(2, col)
        cell.fill = dark_fill
        cell.border = border
    
    # Дата, PL NO, AWB NO
    ws.cell(7, 8).value = "DATE :"
    ws.cell(7, 8).font = Font(bold=True)
    ws.cell(7, 9).value = datetime.now().strftime("%Y-%m-%d")
    
    ws.cell(8, 8).value = "PL NO.:"
    ws.cell(8, 8).font = Font(bold=True)
    ws.cell(8, 9).value = datetime.now().strftime("%Y%m%d") + "-001"
    
    ws.cell(9, 8).value = "AWB NO:"
    ws.cell(9, 8).font = Font(bold=True)
    ws.cell(9, 9).value = "555-16530496"
    
    # Seller / Consignee
    ws.cell(12, 2).value = "SELLER:"
    ws.cell(12, 2).font = Font(bold=True)
    ws.cell(13, 2).value = "KVN Group FZCO"
    ws.cell(14, 2).value = "Add: 6WA 12,661, First Floor, 6 West A,"
    ws.cell(15, 2).value = "Dubai Airport, UAE"
    
    ws.cell(12, 7).value = "Ship To (Consignee) :"
    ws.cell(12, 7).font = Font(bold=True)
    ws.cell(13, 7).value = "KOMBYTTECH LLC"
    ws.cell(14, 7).value = "127410, Moscow, 79A Altufevskoe"
    ws.cell(15, 7).value = "Highway, building 2,66, office 6/2,66/2,"
    ws.cell(16, 7).value = "INN 772,662,66289481 KPP 771501001"
    ws.cell(17, 7).value = "Tel:+7(926)62,669 46 99"
    
    # === ЗАГОЛОВКИ ТАБЛИЦЫ ===
    headers = [
        "Pallet no.",
        "Box No.",
        "Description of Items",
        "WEIGHT PER 1",
        "Qty.",
        "NET",
        "GROSS",
        "Weight (KGs)",
        "Dimensions"
    ]
    
    header_row = 19
    for col, header in enumerate(headers, 1):
        cell = ws.cell(header_row, col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border
    
    # === ДАННЫЕ ===
    current_row = header_row + 1
    total_net_sum = 0
    total_gross_sum = 0
    total_weight_sum = 0
    total_qty_sum = 0
    
    all_data = {i: [] for i in range(1, 10)}
    for header in headers:
        all_data[headers.index(header) + 1].append(header)
    
    pallet_groups = {}
    for item in items:
        pallet = str(item.get('pallet_no', '1'))
        if pallet not in pallet_groups:
            pallet_groups[pallet] = []
        pallet_groups[pallet].append(item)
    
    for pallet, pallet_items in pallet_groups.items():
        pallet_weight = None
        dimensions = None
        pallet_start_row = current_row
        
        for idx, item in enumerate(pallet_items):
            if idx == 0:
                pallet_weight = item.get('pallet_weight')
                dimensions = item.get('dimensions')
            
            row_data = []
            for col in range(1, 10):
                if col == 1:
                    val = pallet if idx == 0 else ''
                elif col == 2:
                    val = item.get('box_no', '')
                elif col == 3:
                    val = item.get('part_number', '')
                elif col == 4:
                    val = Decimal(str(item.get('weight_per_item', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if item.get('weight_per_item', 0) else ''
                elif col == 5:
                    val = item.get('qty', 0)
                    total_qty_sum += item.get('qty', 0)
                elif col == 6:
                    val = Decimal(str(item.get('total_net', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if item.get('total_net', 0) else ''
                    total_net_sum += item.get('total_net', 0)
                elif col == 7:
                    val = Decimal(str(item.get('total_gross', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if item.get('total_gross', 0) else ''
                    total_gross_sum += item.get('total_gross', 0)
                elif col == 8:
                    if idx == 0 and pallet_weight:
                        val = Decimal(str(pallet_weight)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        total_weight_sum += pallet_weight
                    else:
                        val = ''
                elif col == 9:
                    val = dimensions if idx == 0 and dimensions else ''
                
                all_data[col].append(str(val) if val else '')
                row_data.append(val)
            
            for col, val in enumerate(row_data, 1):
                cell = ws.cell(current_row, col)
                cell.border = border
                cell.alignment = cell_alignment
                cell.value = val
                if col == 3:
                    cell.alignment = left_alignment
                if col in [4, 6, 7, 8]:
                    cell.number_format = '#,##0.00'
                if col == 5:
                    cell.number_format = '#,##0'
            
            current_row += 1
        
        pallet_end_row = current_row - 1
        
        if pallet_end_row > pallet_start_row:
            ws.merge_cells(start_row=pallet_start_row, start_column=1, end_row=pallet_end_row, end_column=1)
            ws.cell(pallet_start_row, 1).alignment = Alignment(horizontal='center', vertical='center')
            ws.cell(pallet_start_row, 1).border = border
            
            if pallet_weight:
                ws.merge_cells(start_row=pallet_start_row, start_column=8, end_row=pallet_end_row, end_column=8)
                ws.cell(pallet_start_row, 8).alignment = Alignment(horizontal='center', vertical='center')
                ws.cell(pallet_start_row, 8).border = border
            
            if dimensions:
                ws.merge_cells(start_row=pallet_start_row, start_column=9, end_row=pallet_end_row, end_column=9)
                ws.cell(pallet_start_row, 9).alignment = Alignment(horizontal='center', vertical='center')
                ws.cell(pallet_start_row, 9).border = border
        
        box_groups = {}
        for idx, item in enumerate(pallet_items):
            box_no = item.get('box_no', '')
            if box_no:
                if box_no not in box_groups:
                    box_groups[box_no] = []
                box_groups[box_no].append(pallet_start_row + idx)
        
        for box_no, rows in box_groups.items():
            if len(rows) > 1:
                ws.merge_cells(start_row=rows[0], start_column=2, end_row=rows[-1], end_column=2)
                ws.cell(rows[0], 2).alignment = Alignment(horizontal='center', vertical='center')
                ws.cell(rows[0], 2).border = border
        
        current_row += 1
    
    # === ИТОГ ===
    for col in range(1, 10):
        cell = ws.cell(current_row, col)
        cell.border = border
        cell.alignment = cell_alignment
        cell.font = Font(bold=True)
    
    ws.cell(current_row, 1).value = "TOTAL"
    ws.cell(current_row, 5).value = total_qty_sum
    ws.cell(current_row, 5).number_format = '#,##0'
    ws.cell(current_row, 8).value = Decimal(str(total_weight_sum)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    ws.cell(current_row, 8).number_format = '#,##0.00'
    ws.cell(current_row, 8).font = Font(bold=True)
    
    # === ШИРИНА КОЛОНОК ===
    for col in range(1, 10):
        max_len = 0
        for val in all_data[col]:
            if val:
                try:
                    if isinstance(val, (int, float, Decimal)):
                        val_str = f"{val:.2f}"
                    else:
                        val_str = str(val)
                    max_len = max(max_len, len(val_str))
                except:
                    max_len = max(max_len, len(str(val)))
        
        width = min(max(max_len + 3, 10), 40)
        ws.column_dimensions[get_column_letter(col)].width = width
    
    wb.save(output_path)
    return output_path
