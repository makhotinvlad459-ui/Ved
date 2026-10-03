# backend/app/services/packing_list_parser.py
import openpyxl
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re


def extract_part_number(description: str) -> Optional[str]:
    """
    Извлекает артикул из описания.

    Примеры:
        "MDV94LL/A"                              -> "MDV94LL/A"
        "Google Fitbit Air Berry (840353943414)" -> "840353943414"
        "Apple MacBook Air 15 (MDV94LL/A)"       -> "MDV94LL/A"
        "Some product (ABC-123) extra"           -> "ABC-123"
    """
    if description is None:
        return None

    s = str(description).strip()
    if not s:
        return None

    # 1) Содержимое последних скобок
    matches = re.findall(r'\(([^()]+)\)', s)
    if matches:
        candidate = matches[-1].strip()
        if re.fullmatch(r'[A-Za-z0-9\-/.]+', candidate):
            return candidate

    # 2) Вся строка — артикул
    if re.fullmatch(r'[A-Za-z0-9\-/.]+', s):
        return s

    # 3) Fallback: первое «похожее на артикул» слово длиной >= 4
    m = re.search(r'[A-Za-z0-9\-/.]{4,}', s)
    if m:
        return m.group(0)

    # 4) Совсем не распознали — вернуть как есть
    return s


def parse_packing_list(file_path: str) -> Dict[str, Any]:
    """
    Парсинг файла Packing List.

    Логика группировки (ключ — group_id):

    1. Если в строке заполнен "Pallet no." — начинается НОВАЯ ПАЛЛЕТА.
       Все последующие строки, пока не появится новый Pallet no. —
       относятся к этой паллете. Коробки внутри неё (Box No.) — часть
       паллеты, своего веса не имеют.

    2. Если "Pallet no." пусто, а "Box No." заполнено:
       - и в строке ЕСТЬ вес — это КОРОБКА ВНЕ ПАЛЛЕТЫ. Она становится
         самостоятельной единицей (своя группа, свой вес).
       - и в строке НЕТ веса — это КОРОБКА ВНУТРИ текущей паллеты.
         Её группа — текущая паллета, вес берётся с паллеты.

    3. Если и Pallet no., и Box No. пусто — строка относится к текущей
       группе (паллете или коробке-как-единице).

    Поля в каждом item:
      - group_id:    ключ группировки (всегда заполнен)
      - pallet_no:   для отображения в колонке A (может быть None)
      - box_no:      для отображения в колонке B (может быть None)
      - pallet_weight: вес группы (всегда число, не None)
      - dimensions:  габариты группы (может быть None)
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    header_row = None
    headers = {}

    # Ищем строку заголовков
    for row in range(1, min(ws.max_row, 20)):
        for col in range(1, ws.max_column + 1):
            cell_value = ws.cell(row, col).value
            if cell_value and isinstance(cell_value, str):
                if "Pallet no." in cell_value or "Pallet" in cell_value:
                    header_row = row
                    break
        if header_row:
            break

    if not header_row:
        for row in range(1, min(ws.max_row, 20)):
            for col in range(1, ws.max_column + 1):
                cell_value = ws.cell(row, col).value
                if cell_value and isinstance(cell_value, str):
                    if "Description" in cell_value:
                        header_row = row
                        break
            if header_row:
                break

    if not header_row:
        raise Exception("Не удалось найти заголовки таблицы")

    for col in range(1, ws.max_column + 1):
        value = ws.cell(header_row, col).value
        if value and isinstance(value, str):
            value_clean = value.strip().lower()
            if "pallet" in value_clean:
                headers["pallet_no"] = col
            elif "box" in value_clean:
                headers["box_no"] = col
            elif "description" in value_clean or "items" in value_clean:
                headers["description"] = col
            elif "qty" in value_clean or "quantity" in value_clean:
                headers["qty"] = col
            elif "weight per 1" in value_clean or "weight per" in value_clean:
                headers["weight_per_1"] = col
            elif "net" in value_clean:
                headers["net"] = col
            elif "gross" in value_clean:
                headers["gross"] = col
            elif "weight (kgs)" in value_clean or "weight" in value_clean:
                headers["pallet_weight"] = col
            elif "dimensions" in value_clean:
                headers["dimensions"] = col

    items = []

    current_group_id = None       # ключ группировки
    current_pallet_no = None      # что показывать в колонке A
    current_box_no = None         # что показывать в колонке B
    current_weight = 0            # вес группы
    current_dimensions = None     # габариты группы

    for row in range(header_row + 1, ws.max_row + 1):
        row_empty = True
        for col in range(1, ws.max_column + 1):
            if ws.cell(row, col).value:
                row_empty = False
                break

        if row_empty:
            continue

        pallet_no = ws.cell(row, headers.get("pallet_no", 1)).value if "pallet_no" in headers else None
        box_no = ws.cell(row, headers.get("box_no", 2)).value if "box_no" in headers else None
        description = ws.cell(row, headers.get("description", 3)).value if "description" in headers else None
        qty = ws.cell(row, headers.get("qty", 4)).value if "qty" in headers else None
        weight_per_1 = ws.cell(row, headers.get("weight_per_1", 5)).value if "weight_per_1" in headers else None
        net = ws.cell(row, headers.get("net", 6)).value if "net" in headers else None
        gross = ws.cell(row, headers.get("gross", 7)).value if "gross" in headers else None
        pallet_weight_cell = ws.cell(row, headers.get("pallet_weight", 8)).value if "pallet_weight" in headers else None
        dimensions = ws.cell(row, headers.get("dimensions", 9)).value if "dimensions" in headers else None

        # === Обновляем состояние группы ===
        if pallet_no:
            # Начало новой паллеты
            current_group_id = f"pallet:{pallet_no}"
            current_pallet_no = pallet_no
            current_box_no = None
            if pallet_weight_cell:
                current_weight = float(pallet_weight_cell)
            if dimensions:
                current_dimensions = str(dimensions)
        elif box_no and pallet_weight_cell:
            # Коробка с весом → самостоятельная единица вне паллеты
            current_group_id = f"box:{box_no}"
            current_pallet_no = None
            current_box_no = box_no
            current_weight = float(pallet_weight_cell)
            if dimensions:
                current_dimensions = str(dimensions)
        elif box_no:
            # Коробка без веса → часть текущей паллеты (если она есть)
            current_box_no = box_no
            # current_group_id не меняется — остаётся текущая паллета
            if current_group_id is None:
                # Нет активной паллеты — считаем коробку как единицу (на всякий случай)
                current_group_id = f"box:{box_no}"
                current_pallet_no = None
                current_box_no = box_no
        # иначе — продолжаем текущую группу, ничего не меняем

        # === Пропускаем итоговую строку ===
        if description and str(description).strip().isdigit():
            continue
        if description and "TOTAL" in str(description).upper():
            continue

        if not description:
            continue

        if current_group_id is None:
            # Не можем определить группу — пропускаем
            continue

        part_number = extract_part_number(str(description))
        if not part_number:
            continue

        items.append({
            "part_number": part_number,
            "description_raw": str(description).strip(),
            "qty": int(qty) if qty else 0,
            "weight_per_1": float(weight_per_1) if weight_per_1 else None,
            "net": float(net) if net else None,
            "gross": float(gross) if gross else None,
            "pallet_weight": current_weight or 0,
            "dimensions": current_dimensions,
            "group_id": current_group_id,
            "pallet_no": current_pallet_no,
            "box_no": current_box_no,
        })

    return {"items": items}


def get_product_by_part_number(db, part_number: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Ищет продукт по part_number с несколькими уровнями нормализации.
    Возвращает (product, model_number).
    """
    from app.models import Product

    if not part_number:
        return None, None

    product = db.query(Product).filter(Product.part_number == part_number).first()
    if product:
        return product, product.model_number

    normalized = part_number.strip().upper()
    product = db.query(Product).filter(Product.part_number == normalized).first()
    if product:
        return product, product.model_number

    from sqlalchemy import func
    product = db.query(Product).filter(
        func.lower(Product.part_number) == normalized.lower()
    ).first()
    if product:
        return product, product.model_number

    m = re.findall(r'\(([^()]+)\)', str(part_number))
    if m:
        candidate = m[-1].strip()
        product = db.query(Product).filter(Product.part_number == candidate).first()
        if product:
            return product, product.model_number

    return None, None


def redistribute_gross(items: List[Dict], pallet_weight: float) -> List[Dict]:
    """
    Выравнивание GROSS между позициями с учётом 19% ограничения
    """
    if not items or pallet_weight <= 0:
        return items

    total_net = sum(item.get("net", 0) or 0 for item in items)
    if total_net == 0:
        return items

    for item in items:
        net = item.get("net", 0) or 0
        item["gross"] = (net / total_net) * pallet_weight

    max_iterations = 100
    for _ in range(max_iterations):
        diffs = []
        for item in items:
            net = item.get("net", 0) or 0
            gross = item.get("gross", 0) or 0
            if net > 0:
                diff = (gross - net) / net * 100
                diffs.append((item, diff, net, gross))
            else:
                diffs.append((item, 0, net, gross))

        max_diff_item, max_diff, max_net, max_gross = max(diffs, key=lambda x: x[1])
        min_diff_item, min_diff, min_net, min_gross = min(diffs, key=lambda x: x[1])

        if max_diff - min_diff < 0.5:
            break

        if max_diff <= 19 and min_diff >= 0:
            break

        transfer = 0.1

        if min_gross - transfer >= min_net:
            min_diff_item["gross"] = min_gross - transfer
        else:
            min_diff_item["gross"] = min_net

        max_diff_item["gross"] = max_gross + transfer

        new_max_gross = max_diff_item.get("gross", 0)
        if max_net > 0:
            new_max_diff = (new_max_gross - max_net) / max_net * 100
            if new_max_diff > 19:
                max_diff_item["gross"] = max_gross
                min_diff_item["gross"] = min_gross
                break

    for item in items:
        net = item.get("net", 0) or 0
        gross = item.get("gross", 0) or 0
        if net > 0:
            diff = (gross - net) / net * 100
            if diff > 19:
                new_net = gross / 1.19
                item["net"] = new_net

    for item in items:
        net = item.get("net", 0) or 0
        qty = item.get("qty", 0) or 0
        gross = item.get("gross", 0) or 0

        if qty > 0:
            item["weight_per_item"] = net / qty
            item["total_net"] = net
            item["total_gross"] = gross
            if net > 0:
                item["difference_percent"] = (gross - net) / net * 100
            else:
                item["difference_percent"] = 0

    return items