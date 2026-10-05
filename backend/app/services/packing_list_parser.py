# backend/app/services/packing_list_parser.py
import openpyxl
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re


# Максимальный коэффициент подъёма веса при недоборе
MAX_RAISE_FACTOR = 2.0

# Жёсткий лимит GROSS/NET по каждой позиции
MAX_GROSS_RATIO = 1.19


def extract_part_number(description: str) -> Optional[str]:
    """
    Извлекает артикул из описания и нормализует: strip + upper.
    Это критично: без нормализации 'MKFC4FE/A ' и 'mkfc4fe/a' считаются
    разными артикулами, и shared-логика ломается.
    """
    if description is None:
        return None

    s = str(description).strip()
    if not s:
        return None

    candidate = None

    matches = re.findall(r'\(([^()]+)\)', s)
    if matches:
        candidate = matches[-1].strip()
        if not re.fullmatch(r'[A-Za-z0-9\-/.]+', candidate):
            candidate = None

    if candidate is None:
        if re.fullmatch(r'[A-Za-z0-9\-/.]+', s):
            candidate = s
        else:
            m = re.search(r'[A-Za-z0-9\-/.]{4,}', s)
            if m:
                candidate = m.group(0)
            else:
                candidate = s

    if candidate is None:
        return None

    return candidate.strip().upper()


def parse_packing_list(file_path: str) -> Dict[str, Any]:
    """
    Парсинг файла Packing List с группировкой по group_id.
    Веса НЕ читаются (в исходном файле их нет) — только part_number, qty, group.
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
            elif "weight (kgs)" in value_clean or value_clean == "weight":
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

        pallet_no = ws.cell(row, headers["pallet_no"]).value if "pallet_no" in headers else None
        box_no = ws.cell(row, headers["box_no"]).value if "box_no" in headers else None
        description = ws.cell(row, headers["description"]).value if "description" in headers else None
        qty = ws.cell(row, headers["qty"]).value if "qty" in headers else None
        pallet_weight_cell = ws.cell(row, headers["pallet_weight"]).value if "pallet_weight" in headers else None
        dimensions = ws.cell(row, headers["dimensions"]).value if "dimensions" in headers else None

        if pallet_no:
            current_group_id = f"pallet:{pallet_no}"
            current_pallet_no = pallet_no
            current_box_no = None
            if pallet_weight_cell:
                try:
                    current_weight = float(pallet_weight_cell)
                except (ValueError, TypeError):
                    current_weight = 0
            if dimensions:
                current_dimensions = str(dimensions)
        elif box_no and pallet_weight_cell:
            current_group_id = f"box:{box_no}"
            current_pallet_no = None
            current_box_no = box_no
            try:
                current_weight = float(pallet_weight_cell)
            except (ValueError, TypeError):
                current_weight = 0
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

        try:
            qty_int = int(qty) if qty else 0
        except (ValueError, TypeError):
            qty_int = 0

        items.append({
            "part_number": part_number,
            "description_raw": str(description).strip(),
            "qty": qty_int,
            "pallet_weight": current_weight or 0,
            "dimensions": current_dimensions,
            "group_id": current_group_id,
            "pallet_no": current_pallet_no,
            "box_no": current_box_no,
        })

    return {"items": items}


def get_product_by_part_number(db, part_number: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Ищет продукт по part_number с нормализацией (upper + strip).
    """
    from app.models import Product
    from sqlalchemy import func

    if not part_number:
        return None, None

    normalized = part_number.strip().upper()

    product = db.query(Product).filter(Product.part_number == part_number).first()
    if product:
        return product, product.model_number

    product = db.query(Product).filter(Product.part_number == normalized).first()
    if product:
        return product, product.model_number

    product = db.query(Product).filter(
        func.upper(Product.part_number) == normalized
    ).first()
    if product:
        return product, product.model_number

    return None, None


def _distribute_proportional_with_cap(
    items: List[Dict],
    target_total_gross: float,
    max_ratio: float = MAX_GROSS_RATIO,
) -> None:
    """
    Распределяет target_total_gross между items пропорционально NET,
    с ограничением gross ≤ net × max_ratio для каждого.
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

    for it in items:
        it["gross"] = it.get("net", 0) or 0

    remaining = target_total_gross - sum(it["gross"] for it in items)

    if remaining <= 0.001:
        return

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


def _compute_free_space(items: List[Dict], target: float, max_ratio: float) -> float:
    """
    Сколько ещё NET можно накинуть в паллете, чтобы Σ GROSS ≤ target
    при cap max_ratio. Если < 0 — перебор.
    """
    sum_net = sum((it.get("net", 0) or 0) for it in items)
    max_gross = sum_net * max_ratio
    return target - max_gross


def distribute_gross_across_pallets(
    pallet_groups: Dict[str, List[Dict]],
    pallet_weights: Dict[str, float],
    part_weights: Dict[str, float],
    max_ratio: float = MAX_GROSS_RATIO,
    max_raise_factor: float = MAX_RAISE_FACTOR,
) -> Dict[str, List[Dict]]:
    """
    Гибридное распределение GROSS по паллетам.

    Веса берутся ТОЛЬКО из part_weights (из БД).

    Алгоритм:
      1. Считаем базовые NET по каждой паллете (weight × qty).
      2. Этап 1 — глобальный подъём shared-артикулов:
         shared можно поднять, только если во ВСЕХ паллетах, где он есть,
         хватает свободного места (Σ GROSS ≤ target при подъёме).
      3. Этап 2 — локальный подъём уникальных артикулов:
         если после Этапа 1 в паллете всё ещё недобор — поднимаем
         weight_per_item у уникальных (только этой паллеты).
      4. Этап 3 — распределение GROSS через _distribute_proportional_with_cap.
      5. Финальные проверки: Σ GROSS == target, GROSS ≤ NET × max_ratio,
         weight shared одинаков во всех паллетах.
    """
    # ============================================================
    # ПРОХОД 1: базовая структура + резолв веса из part_weights
    # ============================================================
    print(f"   📊 Паллет: {len(pallet_groups)}")
    print(f"   📦 Артикулов с весом в БД: {len(part_weights)}")

    missing = set()
    part_to_groups: Dict[str, List[str]] = {}

    for group_id, items in pallet_groups.items():
        for item in items:
            part = item.get("part_number")
            qty = item.get("qty", 0) or 0

            if part not in part_weights:
                missing.add(part)
                item["net"] = 0
                item["weight_per_item"] = 0
                continue

            w = part_weights[part]
            item["weight_per_item"] = w
            item["net"] = w * qty

            part_to_groups.setdefault(part, [])
            if group_id not in part_to_groups[part]:
                part_to_groups[part].append(group_id)

    if missing:
        raise Exception(
            f"Нет веса в БД для артикулов: {sorted(missing)}. "
            f"Сначала заполните веса через pending_weights."
        )

    shared_parts = {p for p, gs in part_to_groups.items() if len(gs) > 1}
    unique_parts = {p for p, gs in part_to_groups.items() if len(gs) == 1}

    print(f"   🔗 Shared-артикулов: {len(shared_parts)}")
    print(f"   🎯 Уникальных: {len(unique_parts)}")

    # ============================================================
    # ПРОХОД 2: Этап 1 — глобальный подъём shared
    # ============================================================
    for group_id, items in pallet_groups.items():
        target = pallet_weights.get(group_id, 0) or 0
        sum_net = sum((it.get("net", 0) or 0) for it in items)
        free = _compute_free_space(items, target, max_ratio)
        print(
            f"   📦 {group_id}: target={target:.2f}, "
            f"Σ NET={sum_net:.2f}, free_space={free:.2f}"
        )

    def recompute_all():
        """Пересчитывает NET и свободное место для всех паллет."""
        for gid, its in pallet_groups.items():
            for it in its:
                part = it.get("part_number")
                qty = it.get("qty", 0) or 0
                if part in part_weights:
                    w = part_weights[part]
                    it["weight_per_item"] = w
                    it["net"] = w * qty

    iteration = 0
    while True:
        iteration += 1
        progress = False

        # Пересчёт free_space по всем паллетам
        free_spaces: Dict[str, float] = {}
        for gid, its in pallet_groups.items():
            target = pallet_weights.get(gid, 0) or 0
            free_spaces[gid] = _compute_free_space(its, target, max_ratio)

        # Паллеты с недобором
        need_groups = {gid for gid, f in free_spaces.items() if f > 0.01}

        if not need_groups:
            break

        # Ищем shared, которые можно поднять
        for part in sorted(shared_parts):
            groups_with_part = part_to_groups[part]

            # Проверяем, есть ли смысл — паллета с этим part в need_groups
            if not any(g in need_groups for g in groups_with_part):
                continue

            # Проверяем, что во ВСЕХ паллетах, где есть part, есть запас
            all_have_room = True
            min_factor = float("inf")

            for gid in groups_with_part:
                free = free_spaces.get(gid, 0)
                if free <= 0.01:
                    all_have_room = False
                    break

                # Насколько можно поднять вес part в этой паллете:
                # qty * (w_new - w_old) * max_ratio ≤ free
                qty_in_group = sum(
                    it.get("qty", 0) or 0
                    for it in pallet_groups[gid]
                    if it.get("part_number") == part
                )
                if qty_in_group <= 0:
                    continue

                w_old = part_weights[part]
                if w_old <= 0:
                    all_have_room = False
                    break

                delta_w_max = free / (qty_in_group * max_ratio)
                factor = (w_old + delta_w_max) / w_old
                min_factor = min(min_factor, factor)

            if not all_have_room or min_factor == float("inf"):
                continue

            if min_factor <= 1.0001:
                continue

            # Ограничение сверху
            if min_factor > max_raise_factor:
                min_factor = max_raise_factor

            w_old = part_weights[part]
            w_new = w_old * min_factor

            part_weights[part] = w_new
            recompute_all()
            progress = True

            print(
                f"   ⬆️ shared {part}: {w_old:.4f} → {w_new:.4f} "
                f"(x{min_factor:.4f})"
            )
            break  # пересчитали — выходим из for, заново оценим free_space

        if not progress:
            break

        if iteration > 50:
            print("   ⚠️ Достигнут лимит итераций подъёма shared")
            break

    # ============================================================
    # ПРОХОД 3: Этап 2 — локальный подъём уникальных
    # ============================================================
    for group_id, items in pallet_groups.items():
        target = pallet_weights.get(group_id, 0) or 0
        free = _compute_free_space(items, target, max_ratio)
        if free <= 0.01:
            continue

        uniques_in_group = [
            it for it in items
            if it.get("part_number") in unique_parts
        ]
        if not uniques_in_group:
            # Нет уникальных — все shared, но места не хватило
            sum_net = sum((it.get("net", 0) or 0) for it in items)
            raise Exception(
                f"Паллета {group_id}: нет уникальных артикулов, "
                f"но не хватает {free:.2f} кг NET. "
                f"Σ NET={sum_net:.2f}, target={target:.2f}, "
                f"макс GROSS={sum_net * max_ratio:.2f}. "
                f"Shared поднять нельзя (ломает другие паллеты)."
            )

        sum_net_uniq = sum((it.get("net", 0) or 0) for it in uniques_in_group)
        if sum_net_uniq <= 0.01:
            raise Exception(
                f"Паллета {group_id}: суммарный NET уникальных ≈ 0, "
                f"но нужно добрать {free:.2f} кг"
            )

        # Нужный фактор: чтобы Σ GROSS всех items = target
        # Σ GROSS = (sum_net_uniq_new + sum_net_shared) * ... — проще:
        # поднимаем NET уникальных так, чтобы суммарный NET * max_ratio >= target
        sum_net_all = sum((it.get("net", 0) or 0) for it in items)
        target_net_all = target / max_ratio
        needed_extra_net = target_net_all - sum_net_all

        if needed_extra_net <= 0.01:
            continue

        # Проверяем порог
        factor = (sum_net_uniq + needed_extra_net) / sum_net_uniq

        if factor > max_raise_factor:
            raise Exception(
                f"Паллета {group_id}: требуется поднять уникальные "
                f"в {factor:.2f} раз (порог {max_raise_factor}). "
                f"Σ NET={sum_net_all:.2f}, target NET={target_net_all:.2f}. "
                f"Данные о весах, скорее всего, некорректны."
            )

        for it in uniques_in_group:
            old_w = it.get("weight_per_item", 0) or 0
            new_w = old_w * factor
            it["weight_per_item"] = new_w
            it["net"] = new_w * (it.get("qty", 0) or 0)

        print(
            f"   ⬆️ {group_id}: уникальные x{factor:.4f} "
            f"(добрали {needed_extra_net:.2f} кг NET)"
        )

    # ============================================================
    # ПРОХОД 4: Этап 3 — распределение GROSS через cap
    # ============================================================
    result_groups: Dict[str, List[Dict]] = {}

    for group_id, items in pallet_groups.items():
        target = pallet_weights.get(group_id, 0) or 0

        sum_net = sum((it.get("net", 0) or 0) for it in items)
        if sum_net <= 0:
            result_groups[group_id] = items
            continue

        if not target or target <= 0:
            for item in items:
                item["gross"] = item.get("net", 0) or 0
                _finalize_item(item)
            result_groups[group_id] = items
            continue

        _distribute_proportional_with_cap(
            items=items,
            target_total_gross=target,
            max_ratio=max_ratio,
        )

        for item in items:
            _finalize_item(item)

        result_groups[group_id] = items

    # ============================================================
    # ПРОХОД 5: финальные проверки
    # ============================================================
    print(f"   ✅ Распределение завершено")
    _verify_result(result_groups, pallet_weights, max_ratio)

    return result_groups


def _verify_result(
    result_groups: Dict[str, List[Dict]],
    pallet_weights: Dict[str, float],
    max_ratio: float,
) -> None:
    """
    Проверки:
      - Σ GROSS == target (по паллете)
      - GROSS ≤ NET × max_ratio (по каждой позиции)
      - weight_per_item shared одинаков во всех паллетах
    """
    shared_weights: Dict[str, List[Tuple[str, float]]] = {}

    for gid, items in result_groups.items():
        target = pallet_weights.get(gid, 0) or 0
        sum_gross = sum((it.get("total_gross", 0) or 0) for it in items)

        if abs(sum_gross - target) > 0.05:
            print(
                f"   ⚠️ {gid}: Σ GROSS={sum_gross:.2f} ≠ target={target:.2f} "
                f"(разница {sum_gross - target:+.2f})"
            )

        for it in items:
            net = it.get("total_net", 0) or 0
            gross = it.get("total_gross", 0) or 0
            if net > 0 and gross > net * max_ratio + 0.01:
                print(
                    f"   ⚠️ {gid}/{it.get('part_number')}: "
                    f"GROSS={gross:.2f} > NET×{max_ratio}={net * max_ratio:.2f}"
                )

            part = it.get("part_number")
            wpi = it.get("weight_per_item", 0) or 0
            shared_weights.setdefault(part, []).append((gid, wpi))

    for part, entries in shared_weights.items():
        if len(entries) <= 1:
            continue
        weights = {round(w, 6) for _, w in entries}
        if len(weights) > 1:
            print(
                f"   ⚠️ shared {part}: разные веса по паллетам: {entries}"
            )


def redistribute_gross(items: List[Dict], pallet_weight: float) -> List[Dict]:
    """Устаревшая функция — оставлена для совместимости."""
    if not items or pallet_weight <= 0:
        return items

    for item in items:
        item["net"] = item.get("net", 0) or 0

    try:
        _distribute_proportional_with_cap(items, pallet_weight, max_ratio=MAX_GROSS_RATIO)
    except Exception as e:
        print(f"⚠️ redistribute_gross: {e}")
        return items

    for item in items:
        _finalize_item(item)

    return items