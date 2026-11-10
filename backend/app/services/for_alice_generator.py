# backend/app/services/for_alice_generator.py
"""
Генератор xlsx для сервиса For Alice.

Генерирует «живой» Excel с формулами:
- Редактируемые колонки: D (Кол-во), E (Вес), H (Цена AED)
- Всё остальное пересчитывается формулами Excel:
  F = ROUND(E*1.15, 2)
  G = F * D
  I = H * D
  J = ROUND(F * ставка_AED, 2)
  K = H + J
  L = K * D
  M = K (+1.5 если ЧЗ)
  N = M * D
- Блок параметров и ставок — тоже формулы.
"""
import os
from typing import Dict, Any
from decimal import Decimal, ROUND_HALF_UP

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter


OUTPUT_DIR = "/app/output"

# Коэффициенты (синхронизированы с for_alice_calculator.py)
PACKAGING_FACTOR = 1.15
CZ_FEE = 1.5

# Насколько «с запасом» тянем SUM-диапазоны, чтобы новые строки попадали
SUM_TAIL_ROWS = 1000


def _round2(v):
    if v is None:
        return None
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def generate_for_alice_xlsx(
    result: Dict[str, Any],
    session_id: str,
) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Расчёт"

    # === Стили ===
    header_font = Font(bold=True, size=10)
    header_fill = PatternFill(
        start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"
    )
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    edit_fill = PatternFill(
        start_color="FFF9E6", end_color="FFF9E6", fill_type="solid"
    )
    bold = Font(bold=True)

    # === Заголовки ===
    headers = [
        "Код модели",
        "P/N",
        "Наименование",
        "Кол-во",
        "Вес",
        "Вес +15%",
        "Общий вес",
        "Цена (AED)",
        "Стоимость партии",
        "Логистика/ед",
        "Цена + логистика",
        "Стоимость с логистикой",
        "+ЧЗ (AED)",
        "Итог",
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(1, col)
        cell.value = h
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border

    # === Данные ===
    first_data_row = 2
    row = first_data_row

    for r in result["rows"]:
        ws.cell(row, 1).value = r.get("model_number") or ""
        ws.cell(row, 2).value = r.get("part_number") or ""
        ws.cell(row, 3).value = r.get("name") or ""
        ws.cell(row, 4).value = int(r.get("qty") or 0)
        ws.cell(row, 5).value = _round2(r.get("weight")) or 0
        ws.cell(row, 8).value = _round2(r.get("price")) or 0

        ws.cell(row, 6).value = f"=ROUND(E{row}*{PACKAGING_FACTOR},2)"
        ws.cell(row, 7).value = f"=F{row}*D{row}"
        ws.cell(row, 9).value = f"=H{row}*D{row}"
        ws.cell(row, 11).value = f"=H{row}+J{row}"
        ws.cell(row, 12).value = f"=K{row}*D{row}"
        cz = f"+{CZ_FEE}" if r.get("is_cz") else ""
        ws.cell(row, 13).value = f"=K{row}{cz}"
        ws.cell(row, 14).value = f"=M{row}*D{row}"

        for col in range(1, 15):
            cell = ws.cell(row, col)
            cell.border = border
            cell.alignment = left_align if col == 3 else cell_align
            if col in (5, 6, 7, 8, 9, 10, 11, 12, 13, 14):
                cell.number_format = "#,##0.00"
            if col == 4:
                cell.number_format = "#,##0"
            if col in (4, 5, 8):
                cell.fill = edit_fill

        row += 1

    last_data_row = row - 1

    # === Строка итогов прямо под данными (строка 4 в примере) ===
    total_row = row
    ws.cell(total_row, 4).value = f"=SUM(D{first_data_row}:D{last_data_row})"
    ws.cell(total_row, 4).number_format = "#,##0"
    ws.cell(total_row, 7).value = f"=SUM(G{first_data_row}:G{last_data_row})"
    ws.cell(total_row, 7).number_format = "#,##0.00"
    ws.cell(total_row, 9).value = f"=SUM(I{first_data_row}:I{last_data_row})"
    ws.cell(total_row, 9).number_format = "#,##0.00"
    ws.cell(total_row, 14).value = f"=SUM(N{first_data_row}:N{last_data_row})"
    ws.cell(total_row, 14).number_format = "#,##0.00"
    for col in range(1, 15):
        ws.cell(total_row, col).border = border
        ws.cell(total_row, col).font = bold

    row = total_row + 1

    # === Итого вес / Итого сумма: значения в B, подписи в C ===
    ws.cell(row, 2).value = f"=G{total_row}"
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 2).font = bold
    ws.cell(row, 3).value = "Итого вес:"
    ws.cell(row, 3).font = bold
    row += 1

    ws.cell(row, 2).value = f"=N{total_row}"
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 2).font = bold
    ws.cell(row, 3).value = "Итого сумма:"
    ws.cell(row, 3).font = bold
    row += 2

    # === Параметры расчёта: подписи в C, значения в B ===
    ws.cell(row, 3).value = "Параметры расчёта:"
    ws.cell(row, 3).font = bold
    row += 1

    rate_usd_row = row
    ws.cell(row, 2).value = result["totals"]["logistics_rate_usd"]
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 2).fill = edit_fill
    ws.cell(row, 3).value = "Ставка логистики (USD/кг)"
    row += 1

    usd_row = row
    ws.cell(row, 2).value = result["totals"]["usd_to_aed"]
    ws.cell(row, 2).number_format = "#,##0.000"
    ws.cell(row, 2).fill = edit_fill
    ws.cell(row, 3).value = "Курс USD → AED"
    row += 1

    docs_row = row
    ws.cell(row, 2).value = result["totals"]["documents_cost_aed"]
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 2).fill = edit_fill
    ws.cell(row, 3).value = "Расходы на документы (AED)"
    row += 2

    # === Расчёт логистики: подписи в C, значения в B ===
    ws.cell(row, 3).value = "Расчёт логистики:"
    ws.cell(row, 3).font = bold
    row += 1

    log_usd_row = row
    ws.cell(row, 2).value = f"=B{rate_usd_row}*B{total_row - 1}"  # B(итого вес)
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 3).value = "Логистика всего (USD)"
    row += 1

    log_aed_row = row
    ws.cell(row, 2).value = f"=B{log_usd_row}*B{usd_row}"
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 3).value = "Логистика всего (AED)"
    row += 1

    total_log_aed_row = row
    ws.cell(row, 2).value = f"=B{log_aed_row}+B{docs_row}"
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 3).value = "Итого логистика (AED)"
    row += 1

    rate_aed_row = row
    ws.cell(row, 2).value = (
        f"=IF(B{total_row - 1}>0,B{total_log_aed_row}/B{total_row - 1},0)"
    )
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 3).value = "Ставка AED/кг (с документами)"
    row += 1

    rate_usd_per_kg_row = row
    ws.cell(row, 2).value = (
        f"=IF(B{total_row - 1}>0,B{rate_aed_row}/B{usd_row},0)"
    )
    ws.cell(row, 2).number_format = "#,##0.00"
    ws.cell(row, 3).value = "Ставка USD/кг (с документами)"
    row += 1

    # === Заполняем J: логистика/ед = ROUND(F * ставка AED/кг, 2) ===
    for r_idx in range(first_data_row, last_data_row + 1):
        ws.cell(r_idx, 10).value = f"=ROUND(F{r_idx}*$B${rate_aed_row},2)"

    # === Примечание ===
    row += 1
    ws.cell(row, 1).value = (
        "Можно менять жёлтые ячейки: Кол-во (D), Вес (E), Цена (H), "
        "а также параметры расчёта. Остальное пересчитается автоматически."
    )
    ws.cell(row, 1).font = Font(italic=True, size=9, color="666666")

    # === Заморозка шапки и фильтр ===
    ws.freeze_panes = "A2"
    if last_data_row >= first_data_row:
        ws.auto_filter.ref = f"A1:N{last_data_row}"

    # === Ширины колонок ===
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 60
    ws.column_dimensions["D"].width = 8
    for col in range(5, 15):
        ws.column_dimensions[get_column_letter(col)].width = 14

    output_path = os.path.join(OUTPUT_DIR, f"for_alice_{session_id[:8]}.xlsx")
    wb.save(output_path)

    return output_path