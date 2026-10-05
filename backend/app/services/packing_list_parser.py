# backend/app/services/packing_list_parser.py
import openpyxl
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re


def extract_part_number(description: str) -> Optional[str]:
    """
    Извлекает артикул из описания.
    """
    if description is None:
        return None

    s = str(description).strip()
    if not s:
        return None

    matches = re.findall(r'\(([^()]+)\)', s)
    if matches:
        candidate = matches[-1].strip()
        if re.fullmatch(r'[A-Za-z0-9\-/.]+', candidate):
            return candidate

    if re.fullmatch(r'[A-Za-z0-9\-/.]+', s):
        return s

    m = re.search(r'[A-Za-z0-9\-/.]{4,}', s)
    if m:
        return m.group(0)

    return s


def parse_packing_list(file_path: str) -> Dict[str, Any]:
    """
    Парсинг файла Packing List с группировкой по group_id.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    header_row = None
    headers = {}

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
    current_group_id = None
    current_pallet_no = None
    current_box_no = None
    current_weight = 0
    current_dimensions = None

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

        if pallet_no:
            current_group_id = f"pallet:{pallet_no}"
            current_pallet_no = pallet_no
            current_box_no = None
            if pallet_weight_cell:
                current_weight = float(pallet_weight_cell)
            if dimensions:
                current_dimensions = str(dimensions)
        elif box_no and pallet_weight_cell:
            current_group_id = f"box:{box_no}"
            current_pallet_no = None
            current_box_no = box_no
            current_weight = float(pallet_weight_cell)
            if dimensions:
                current_dimensions = str(dimensions)
        elif box_no:
            current_box_no = box_no
            if current_group_id is None:
                current_group_id = f"box:{box_no}"
                current_pallet_no = None
                current_box_no = box_no

        if description and str(description).strip().isdigit():
            continue
        if description and "TOTAL" in str(description).upper():
            continue

        if not description:
            continue

        if current_group_id is None:
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


def _distribute_proportional_with_cap(
    items: List[Dict],
    target_total_gross: float,
    max_ratio: float = 1.19,
) -> None:
    """
    Распределяет target_total_gross между items пропорционально NET,
    но с ограничением gross ≤ net × max_ratio для каждого.
    Если max_total < target_total_gross — ошибка.
    Модифицирует items in-place.
    """
    total_net = sum((it.get("net", 0) or 0) for it in items)
    if total_net <= 0:
        return

    max_total = sum((it.get("net", 0) or 0) * max_ratio for it in items)

    if max_total < target_total_gross - 0.001:
        raise Exception(
            f"Невозможно собрать {target_total_gross:.2f} кг "
            f"при лимите {((max_ratio - 1) * 100):.1f}%. "
            f"Максимум: {max_total:.2f} кг. "
            f"Сумма NET: {total_net:.2f}. "
            f"Дефицит: {target_total_gross - max_total:.2f} кг."
        )

    # 1. База: gross = net
    for it in items:
        it["gross"] = it.get("net", 0) or 0

    remaining = target_total_gross - sum(it["gross"] for it in items)

    if remaining <= 0.001:
        return

    # 2. Итеративно раскидываем остаток с учётом cap
    for _ in range(200):
        if remaining <= 0.001:
            break

        available = []
        for it in items:
            net = it.get("net", 0) or 0
            gross = it.get("gross", 0) or 0
            cap = net * max_ratio
            room = cap - gross
            if room > 0.001:
                available.append((it, room, net))

        if not available:
            break

        total_net_avail = sum(net for (_, _, net) in available if net > 0)

        if total_net_avail <= 0:
            share = remaining / len(available)
            for it, room, _ in available:
                add = min(share, room)
                it["gross"] = (it.get("gross", 0) or 0) + add
                remaining -= add
            continue

        added_total = 0.0
        for it, room, net in available:
            if net <= 0:
                continue
            want = (net / total_net_avail) * remaining
            add = min(want, room)
            it["gross"] = (it.get("gross", 0) or 0) + add
            added_total += add

        remaining -= added_total

        if added_total < 0.001:
            share = remaining / len(available)
            for it, room, _ in available:
                add = min(share, room)
                it["gross"] = (it.get("gross", 0) or 0) + add
                remaining -= add
            break

    if remaining > 0.01:
        raise Exception(
            f"Не удалось распределить {remaining:.2f} кг "
            f"при лимите {((max_ratio - 1) * 100):.1f}%"
        )


def distribute_gross_across_pallets(
    pallet_groups: Dict[str, List[Dict]],
    pallet_weights: Dict[str, float],
    max_ratio: float = 1.19,
) -> Dict[str, List[Dict]]:
    """
    Распределение GROSS по паллетам с учётом shared-артикулов.
    """
    # ==================== ПРОХОД 1 ====================
    part_pallet_stats: Dict[str, List[Dict]] = {}

    for group_id, items in pallet_groups.items():
        for item in items:
            part = item.get("part_number")
            qty = item.get("qty", 0) or 0
            wp = item.get("weight_per_item", 0) or 0

            net_base = wp * qty
            item["net"] = net_base

            part_pallet_stats.setdefault(part, []).append({
                "group_id": group_id,
                "net_base": net_base,
                "qty": qty,
                "weight_per_item": wp,
            })

    # ==================== ПРОХОД 2 ====================
    shared_parts = {p: s for p, s in part_pallet_stats.items() if len(s) > 1}
    fixed_weights: Dict[str, float] = {}

    for part, stats in shared_parts.items():
        best_share = -1.0
        best_weight = 0.0

        for s in stats:
            gid = s["group_id"]
            total_net_in_group = sum(
                (it.get("net", 0) or 0)
                for it in pallet_groups[gid]
            )
            if total_net_in_group <= 0:
                continue
            share = s["net_base"] / total_net_in_group
            if share > best_share:
                best_share = share
                best_weight = s["weight_per_item"]

        if best_share < 0:
            best_weight = max(s["weight_per_item"] for s in stats)

        fixed_weights[part] = best_weight

    print(f"   🔗 Shared-артикулов: {len(fixed_weights)}")
    for part, w in list(fixed_weights.items())[:10]:
        print(f"      - {part}: эталонный вес {w}")

    # ==================== ПРОХОД 3 ====================
    result_groups: Dict[str, List[Dict]] = {}

    for group_id, items in pallet_groups.items():
        pallet_weight = pallet_weights.get(group_id, 0) or 0

        for item in items:
            part = item.get("part_number")
            qty = item.get("qty", 0) or 0

            if part in fixed_weights:
                wp = fixed_weights[part]
                item["net"] = wp * qty
                item["weight_per_item"] = wp

        total_net = sum((it.get("net", 0) or 0) for it in items)
        if total_net <= 0:
            result_groups[group_id] = items
            continue

        if not pallet_weight or pallet_weight <= 0:
            for item in items:
                item["gross"] = item.get("net", 0) or 0
            for item in items:
                _finalize_item(item)
            result_groups[group_id] = items
            continue

        try:
            _distribute_proportional_with_cap(
                items=items,
                target_total_gross=pallet_weight,
                max_ratio=max_ratio,
            )
        except Exception as e:
            raise Exception(
                f"Паллета {group_id}: {str(e)}"
            )

        for item in items:
            _finalize_item(item)

        result_groups[group_id] = items

    return result_groups


def _finalize_item(item: Dict) -> None:
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


def redistribute_gross(items: List[Dict], pallet_weight: float) -> List[Dict]:
    """Устаревшая функция."""
    if not items or pallet_weight <= 0:
        return items

    for item in items:
        item["net"] = item.get("net", 0) or 0

    try:
        _distribute_proportional_with_cap(items, pallet_weight, max_ratio=1.19)
    except Exception as e:
        print(f"⚠️ redistribute_gross: {e}")
        return items

    for item in items:
        _finalize_item(item)

    return items