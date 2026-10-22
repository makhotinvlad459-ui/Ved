# backend/app/services/for_alice_calculator.py
"""
Калькулятор для сервиса «For Alice».
Принимает строки (название, кол-во, цена), считает все формулы.
"""
import re
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Product, Category


# ============================================================
# КАТЕГОРИИ, ПОДЛЕЖАЩИЕ МАРКИРОВКЕ ЧЗ (+1.5 AED за единицу)
# ВАЖНО: имена должны ТОЧНО совпадать с БД (см. таблицу categories)
# ============================================================
CZ_CATEGORIES = {
    "Телефоны APPLE",
    "Телефоны Samsung",
    "Планшеты APLLE",   # в БД опечатка APLLE — оставляем как есть
    "Планшеты APPLE",   # на всякий случай, если переименуют
    "Ноутбуки APPLE",
    "Ноутбуки Lenovo",
}

# Коэффициент упаковки
PACKAGING_FACTOR = 1.15

# Фиксированная надбавка за маркировку ЧЗ (AED)
CZ_FEE = 1.5


def extract_part_number(name: str) -> Optional[str]:
    """Извлекает артикул из названия — последние скобки."""
    if not name:
        return None
    matches = re.findall(r'\(([^()]+)\)', str(name))
    if matches:
        candidate = matches[-1].strip()
        if re.fullmatch(r'[A-Za-z0-9\-/. ]+', candidate):
            return candidate.upper()
    return None


def extract_model_from_name(name: str) -> Optional[str]:
    """Извлекает модель из названия (для fallback-поиска веса)."""
    if not name:
        return None
    d = name

    m = re.search(
        r'iPhone\s+\d+(?:\s+(?:Pro\s+Max|Pro|Plus|Air|Mini|e|Duo))?',
        d, re.IGNORECASE
    )
    if m:
        return m.group(0).strip()

    m = re.search(r'Galaxy\s+[A-Z]\d+(?:\s+(?:Ultra|Plus))?(?:\+)?', d)
    if m:
        return m.group(0).strip()

    m = re.search(
        r'MacBook\s+(?:Pro|Air|Neo)(?:\s+\d+(?:\.\d+)?["\u201d\u2033]?)?',
        d
    )
    if m:
        return m.group(0).strip()

    m = re.search(
        r'iPad\s+(?:Pro|Air|Mini)?(?:\s+\d+(?:\.\d+)?["\u201d\u2033]?)?',
        d
    )
    if m:
        return m.group(0).strip()

    m = re.search(r'Apple Watch\s+(?:Series|SE|Ultra)\s+\d+', d)
    if m:
        return m.group(0).strip()

    m = re.search(r'AirPods(?:\s+Pro)?(?:\s+\(\d[^)]*\))?', d)
    if m:
        return m.group(0).strip()

    m = re.search(r'Mac\s+(?:Mini|Studio)(?:\s+Silver|\s+[A-Za-z]+)?', d)
    if m:
        return m.group(0).strip()

    m = re.search(r'Beats\s+Powerbeats\s+(?:Pro|Fit)', d)
    if m:
        return m.group(0).strip()

    return None


def resolve_weight(
    db: Session,
    part_number: Optional[str],
    name: Optional[str],
) -> Tuple[Optional[float], Optional[str], Optional[Product]]:
    """Ищет вес по part_number и названию. Подгружает категорию."""
    if not part_number and not name:
        return None, None, None

    product = None
    if part_number:
        product = db.query(Product).filter(
            Product.part_number == part_number
        ).first()

    # 1. По part_number
    if product and product.weight:
        return float(product.weight), "product", product

    # 2. Sibling по model_number
    if product and product.model_number:
        sibling = db.query(Product).filter(
            Product.model_number == product.model_number,
            Product.weight.isnot(None),
            Product.weight > 0,
        ).first()
        if sibling:
            return float(sibling.weight), f"model:{product.model_number}", product

    # 3. По имени модели из названия
    if name:
        model_name = extract_model_from_name(name)
        if model_name:
            pattern = f"%{model_name}%"
            sibling = db.query(Product).filter(
                Product.description.ilike(pattern),
                Product.weight.isnot(None),
                Product.weight > 0,
            ).first()
            if sibling:
                return float(sibling.weight), f"model_name:{model_name}", sibling

    return None, None, product


def is_cz_category(product: Optional[Product]) -> bool:
    """Проверяет, подлежит ли товар маркировке ЧЗ."""
    if not product:
        return False
    if not product.category_id:
        return False

    # Категория может быть не загружена (lazy) — получаем явно
    category = product.category
    if not category:
        return False

    return category.name in CZ_CATEGORIES


def round2(value: float) -> float:
    """Округление до 2 знаков."""
    return round(float(value) + 1e-9, 2)


def calculate_for_alice(
    items: List[Dict[str, Any]],
    logistics_rate_usd: float,
    usd_to_aed: float,
    documents_cost_aed: float,
    db: Session,
) -> Dict[str, Any]:
    """
    Считает все формулы для сервиса For Alice.

    items: [{name, qty, price}]
    logistics_rate_usd: ставка логистики USD/кг
    usd_to_aed: курс USD → AED (обычно 3.674)
    documents_cost_aed: расходы на документы AED
    """
    # === 1. Обогащаем строки: part_number, model_number, weight, category ===
    enriched = []
    missing = []

    for idx, item in enumerate(items):
        name = (item.get("name") or "").strip()
        qty = int(item.get("qty") or 0)
        price = float(item.get("price") or 0)

        part_number = extract_part_number(name)
        weight, source, product = resolve_weight(db, part_number, name)

        if weight is None or weight <= 0:
            missing.append({
                "row": idx,
                "name": name,
                "part_number": part_number,
                "qty": qty,
                "price": price,
            })
            enriched.append({
                "row": idx,
                "name": name,
                "part_number": part_number,
                "model_number": None,
                "qty": qty,
                "price": price,
                "weight": None,
                "weight_source": None,
                "is_cz": False,
                "product_id": None,
            })
            continue

        is_cz = is_cz_category(product)

        enriched.append({
            "row": idx,
            "name": name,
            "part_number": part_number,
            "model_number": product.model_number if product else None,
            "qty": qty,
            "price": price,
            "weight": float(weight),
            "weight_source": source,
            "is_cz": is_cz,
            "product_id": product.id if product else None,
        })

    # === 2. Первый проход: считаем G, H, и общий вес ===
    total_weight = 0.0

    for row in enriched:
        if row["weight"] is None:
            row["g"] = None
            row["h"] = None
            continue
        g = round2(row["weight"] * PACKAGING_FACTOR)
        h = g * row["qty"]
        row["g"] = g
        row["h"] = h
        total_weight += h

    # === 3. Ставка логистики в AED за кг (с учётом документов) ===
    if total_weight <= 0:
        rate_aed_per_kg = 0.0
        logistics_total_usd = 0.0
        logistics_total_aed = 0.0
        total_logistics_aed = 0.0
        rate_usd_per_kg = 0.0
    else:
        # F66: логистика в USD (ставка × общий вес)
        logistics_total_usd = logistics_rate_usd * total_weight

        # F67: логистика в AED (F66 × курс)
        logistics_total_aed = logistics_total_usd * usd_to_aed

        # F68: итого логистика AED (F67 + документы)
        total_logistics_aed = logistics_total_aed + documents_cost_aed

        # E69: ставка AED/кг (F68 / общий вес)
        rate_aed_per_kg = total_logistics_aed / total_weight

        # F69: ставка USD/кг (E69 / курс)
        rate_usd_per_kg = rate_aed_per_kg / usd_to_aed

    # === 4. Второй проход: все формулы ===
    total_sum = 0.0

    for row in enriched:
        if row["weight"] is None:
            row["l"] = None
            row["m"] = None
            row["n"] = None
            row["o"] = None
            row["p"] = None
            continue

        g = row["g"]
        qty = row["qty"]
        price = row["price"]

        # Логистика за единицу (K, округлено)
        l = round2(g * rate_aed_per_kg)
        # Цена + логистика
        m = price + l
        # Стоимость партии с логистикой
        n = m * qty
        # +1.5 AED если ЧЗ
        o = m + CZ_FEE if row["is_cz"] else m
        # Итог партии
        p = o * qty

        row["l"] = l
        row["m"] = m
        row["n"] = n
        row["o"] = o
        row["p"] = p

        total_sum += p

    return {
        "rows": enriched,
        "missing": missing,
        "totals": {
            "total_weight": total_weight,
            "total_sum": total_sum,
            "rate_aed_per_kg": rate_aed_per_kg,
            "rate_usd_per_kg": rate_usd_per_kg,
            "logistics_rate_usd": logistics_rate_usd,
            "usd_to_aed": usd_to_aed,
            "documents_cost_aed": documents_cost_aed,
            "logistics_total_usd": logistics_total_usd,
            "logistics_total_aed": logistics_total_aed,
            "total_logistics_aed": total_logistics_aed,
        },
    }