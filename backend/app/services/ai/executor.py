# backend/app/services/ai/executor.py
"""
Исполнитель tools.
- READ_TOOLS выполняются сразу, возвращают данные.
- WRITE_TOOLS делают preview (SELECT + валидация) и возвращают
  {requires_confirmation: True, preview: {...}, action: {...}}
  Выполнение — отдельно, после POST /ai/confirm.
"""

import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, or_, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload  # <-- ДОБАВЛЕНО ДЛЯ ЛЕНИВОЙ ЗАГРУЗКИ

from app.models import Product, Category
from app.services.ai.tools import LIMITS


# ============================================================
# УТИЛИТЫ
# ============================================================

class ToolError(Exception):
    """Ошибка выполнения tool — возвращается модели как текст."""
    pass


def _product_to_dict(p: Product) -> Dict[str, Any]:
    return {
        "id": p.id,
        "part_number": p.part_number,
        "model_number": p.model_number,
        "description": p.description,
        "weight": p.weight,
        "category_id": p.category_id,
        "category": p.category.name if p.category else None,
        "color_id": p.color_id,
        "is_active": p.is_active,
    }


async def _get_category_by_name(
    db: AsyncSession, name: str
) -> Optional[Category]:
    stmt = select(Category).where(
        func.lower(Category.name) == name.lower().strip(),
        Category.is_active == True,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _validate_pattern(pattern: Optional[str]) -> Optional[str]:
    """Валидация pattern: min 3 символа, не пустой."""
    if pattern is None:
        return None
    p = pattern.strip()
    if len(p) < LIMITS["pattern_min_length"]:
        raise ToolError(
            f"pattern слишком короткий ({len(p)} символов). "
            f"Минимум {LIMITS['pattern_min_length']}. Уточни запрос."
        )
    return p


# ============================================================
# READ TOOLS — выполняются сразу
# ============================================================

async def count_products(
    db: AsyncSession,
    category_name: Optional[str] = None,
    has_weight: Optional[bool] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    stmt = select(func.count(Product.id)).where(Product.is_active == True)

    if category_name:
        cat = await _get_category_by_name(db, category_name)
        if not cat:
            raise ToolError(f"Категория '{category_name}' не найдена.")
        stmt = stmt.where(Product.category_id == cat.id)

    if has_weight is True:
        stmt = stmt.where(Product.weight.isnot(None), Product.weight > 0)
    elif has_weight is False:
        stmt = stmt.where(or_(Product.weight.is_(None), Product.weight <= 0))

    if pattern:
        p = _validate_pattern(pattern)
        stmt = stmt.where(Product.description.ilike(f"%{p}%"))

    result = await db.execute(stmt)
    count = result.scalar() or 0

    return {
        "count": count,
        "filters": {
            "category_name": category_name,
            "has_weight": has_weight,
            "pattern": pattern,
        },
    }


async def search_products(
    db: AsyncSession,
    query: str,
    limit: int = 8,
) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        raise ToolError("query пустой.")

    limit = min(int(limit or 20), LIMITS["search_products"])
    pattern = f"%{q}%"

    stmt = (
        select(Product)
        # ДОБАВЛЕНО: подгружаем связи сразу, чтобы не было ошибок async lazy-load
        .options(selectinload(Product.category), selectinload(Product.color))
        .where(
            Product.is_active == True,
            or_(
                Product.part_number.ilike(pattern),
                Product.description.ilike(pattern),
            ),
        )
        .order_by(Product.part_number)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "query": q,
        "count": len(items),
        "items": [_product_to_dict(p) for p in items],
    }


async def find_missing_part_numbers(
    db: AsyncSession,
    part_numbers: List[str],
) -> Dict[str, Any]:
    if not part_numbers:
        raise ToolError("part_numbers пустой.")

    cleaned = [str(x).strip().upper() for x in part_numbers if str(x).strip()]
    if not cleaned:
        raise ToolError("part_numbers пустой после очистки.")

    stmt = select(Product.part_number).where(
        func.upper(Product.part_number).in_(cleaned)
    )
    result = await db.execute(stmt)
    found = {row[0].upper() for row in result.all()}

    missing = [pn for pn in cleaned if pn not in found]

    return {
        "total": len(cleaned),
        "found_count": len(found),
        "missing_count": len(missing),
        "found": sorted(found),
        "missing": missing,
    }


async def check_products_exist(
    db: AsyncSession,
    products: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not products:
        raise ToolError("products пустой.")
    if len(products) > LIMITS["check_products_exist"]:
        raise ToolError(
            f"Слишком много позиций ({len(products)}). "
            f"Максимум {LIMITS['check_products_exist']} за раз."
        )

    # Собираем part_numbers (upper)
    input_items = []
    for it in products:
        pn = str(it.get("part_number", "")).strip().upper()
        if not pn:
            continue
        input_items.append({
            "part_number": pn,
            "description": str(it.get("description", "")).strip(),
        })

    if not input_items:
        raise ToolError("Нет валидных part_number.")

    unique_pns = list({it["part_number"] for it in input_items})

    stmt = (
        select(Product)
        # ДОБАВЛЕНО: подгружаем связи
        .options(selectinload(Product.category), selectinload(Product.color))
        .where(func.upper(Product.part_number).in_(unique_pns))
    )
    result = await db.execute(stmt)
    db_products = {p.part_number.upper(): p for p in result.scalars().all()}

    found = []
    missing = []
    for it in input_items:
        pn = it["part_number"]
        if pn in db_products:
            p = db_products[pn]
            found.append({
                "part_number": p.part_number,
                "description": p.description,
                "category": p.category.name if p.category else None,
                "weight": p.weight,
                "has_weight": p.weight is not None and p.weight > 0,
            })
        else:
            missing.append({
                "part_number": it["part_number"],
                "description": it["description"],
            })

    return {
        "total": len(input_items),
        "found_count": len(found),
        "missing_count": len(missing),
        "found": found,
        "missing": missing,
    }


async def get_product_weight(
    db: AsyncSession,
    part_number: str,
) -> Dict[str, Any]:
    pn = (part_number or "").strip()
    if not pn:
        raise ToolError("part_number пустой.")

    stmt = (
        select(Product)
        # ДОБАВЛЕНО: подгружаем связи
        .options(selectinload(Product.category), selectinload(Product.color))
        .where(func.upper(Product.part_number) == pn.upper())
    )
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        return {"found": False, "part_number": pn}

    return {
        "found": True,
        "part_number": product.part_number,
        "description": product.description,
        "weight": product.weight,
        "has_weight": product.weight is not None and product.weight > 0,
        "category": product.category.name if product.category else None,
    }


async def list_categories(db: AsyncSession) -> Dict[str, Any]:
    stmt = select(Category).where(Category.is_active == True).order_by(Category.name)
    result = await db.execute(stmt)
    cats = result.scalars().all()

    return {
        "count": len(cats),
        "categories": [
            {"id": c.id, "name": c.name, "prefix_ru": c.prefix_ru}
            for c in cats
        ],
    }


# ============================================================
# WRITE TOOLS — preview (без изменений в БД)
# ============================================================

async def update_product_weight_preview(
    db: AsyncSession,
    new_weight: float,
    part_number: Optional[str] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    if part_number and pattern:
        raise ToolError("Укажи либо part_number, либо pattern, не оба.")
    if not part_number and not pattern:
        raise ToolError("Нужен part_number или pattern.")
    if new_weight is None or new_weight <= 0:
        raise ToolError("new_weight должен быть > 0.")

    # Найти товары
    if part_number:
        stmt = (
            select(Product)
            # ДОБАВЛЕНО: подгружаем связи
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                func.upper(Product.part_number) == part_number.strip().upper(),
                Product.is_active == True,
            )
        )
    else:
        p = _validate_pattern(pattern)
        stmt = (
            select(Product)
            # ДОБАВЛЕНО: подгружаем связи
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                Product.is_active == True,
                Product.description.ilike(f"%{p}%"),
            )
            .limit(LIMITS["update_product_weight"] + 1)
        )

    result = await db.execute(stmt)
    products = result.scalars().all()

    if not products:
        raise ToolError("Товары не найдены. Уточни запрос.")

    if len(products) > LIMITS["update_product_weight"]:
        raise ToolError(
            f"Найдено больше {LIMITS['update_product_weight']} товаров. "
            f"Уточни pattern (сейчас '{pattern}')."
        )

    # Предпросмотр изменений
    preview = []
    for p in products:
        preview.append({
            "id": p.id,
            "part_number": p.part_number,
            "description": p.description,
            "old_weight": p.weight,
            "new_weight": new_weight,
        })

    return {
        "requires_confirmation": True,
        "action": {
            "tool": "update_product_weight",
            "args": {
                "part_number": part_number,
                "pattern": pattern,
                "new_weight": new_weight,
            },
        },
        "preview": {
            "count": len(products),
            "items": preview,
        },
        "message": f"Найдено {len(products)} товаров. Обновить вес на {new_weight} кг?",
    }


async def update_product_category_preview(
    db: AsyncSession,
    category_name: str,
    part_numbers: Optional[List[str]] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    if part_numbers and pattern:
        raise ToolError("Укажи либо part_numbers, либо pattern, не оба.")
    if not part_numbers and not pattern:
        raise ToolError("Нужен part_numbers или pattern.")

    cat = await _get_category_by_name(db, category_name)
    if not cat:
        raise ToolError(f"Категория '{category_name}' не найдена.")

    if part_numbers:
        cleaned = [str(x).strip().upper() for x in part_numbers if str(x).strip()]
        if not cleaned:
            raise ToolError("part_numbers пустой после очистки.")
        if len(cleaned) > LIMITS["update_product_category"]:
            raise ToolError(f"Слишком много part_numbers ({len(cleaned)}). Максимум {LIMITS['update_product_category']}.")
        stmt = (
            select(Product)
            # ДОБАВЛЕНО: подгружаем связи
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                func.upper(Product.part_number).in_(cleaned),
                Product.is_active == True,
            )
        )
    else:
        p = _validate_pattern(pattern)
        stmt = (
            select(Product)
            # ДОБАВЛЕНО: подгружаем связи
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                Product.is_active == True,
                Product.description.ilike(f"%{p}%"),
            )
            .limit(LIMITS["update_product_category"] + 1)
        )

    result = await db.execute(stmt)
    products = result.scalars().all()

    if not products:
        raise ToolError("Товары не найдены.")
    if len(products) > LIMITS["update_product_category"]:
        raise ToolError(f"Найдено больше {LIMITS['update_product_category']} товаров. Уточни pattern.")

    preview = []
    for p in products:
        preview.append({
            "id": p.id,
            "part_number": p.part_number,
            "description": p.description,
            "old_category": p.category.name if p.category else None,
            "new_category": cat.name,
        })

    return {
        "requires_confirmation": True,
        "action": {
            "tool": "update_product_category",
            "args": {
                "part_numbers": part_numbers,
                "pattern": pattern,
                "category_name": category_name,
            },
        },
        "preview": {
            "count": len(products),
            "items": preview,
        },
        "message": f"Найдено {len(products)} товаров. Назначить категорию '{cat.name}'?",
    }


async def create_category_preview(
    db: AsyncSession,
    name: str,
    prefix_ru: str,
    name_eng: Optional[str] = None,
) -> Dict[str, Any]:
    n = (name or "").strip()
    p = (prefix_ru or "").strip()
    if not n or not p:
        raise ToolError("name и prefix_ru обязательны.")

    existing = await _get_category_by_name(db, n)
    if existing:
        raise ToolError(f"Категория '{n}' уже существует (id={existing.id}).")

    return {
        "requires_confirmation": True,
        "action": {
            "tool": "create_category",
            "args": {"name": n, "prefix_ru": p, "name_eng": name_eng},
        },
        "preview": {
            "name": n,
            "prefix_ru": p,
            "name_eng": name_eng,
        },
        "message": f"Создать категорию '{n}' с префиксом '{p}'?",
    }


async def create_products_preview(
    db: AsyncSession,
    products: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not products:
        raise ToolError("products пустой.")
    if len(products) > LIMITS["create_products"]:
        raise ToolError(f"Слишком много товаров ({len(products)}). Максимум {LIMITS['create_products']} за раз.")

    # Валидация + подстановка category_id
    prepared = []
    for it in products:
        pn = str(it.get("part_number", "")).strip()
        desc = str(it.get("description", "")).strip()
        if not pn or not desc:
            raise ToolError(f"У товара отсутствует part_number или description: {it}")

        cat_id = None
        cat_name = it.get("category_name")
        if cat_name:
            cat = await _get_category_by_name(db, cat_name)
            if not cat:
                raise ToolError(f"Категория '{cat_name}' не найдена (товар {pn}).")
            cat_id = cat.id

        weight = it.get("weight")
        if weight is not None:
            try:
                weight = float(weight)
                if weight <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                raise ToolError(f"Некорректный weight у {pn}: {it.get('weight')}")

        prepared.append({
            "part_number": pn,
            "description": desc,
            "model_number": it.get("model_number"),
            "category_id": cat_id,
            "category_name": cat_name,
            "weight": weight,
            "coo": it.get("coo"),
        })

    # Проверить дубли в БД
    pns = [p["part_number"].upper() for p in prepared]
    stmt = select(Product.part_number).where(func.upper(Product.part_number).in_(pns))
    result = await db.execute(stmt)
    existing = {row[0].upper() for row in result.all()}
    duplicates = [p["part_number"] for p in prepared if p["part_number"].upper() in existing]

    if duplicates:
        raise ToolError(
            f"Эти артикулы уже есть в базе: {duplicates}. "
            f"Если нужно обновить — используй update_product_weight / update_product_category."
        )

    return {
        "requires_confirmation": True,
        "action": {
            "tool": "create_products",
            "args": {"products": prepared},
        },
        "preview": {
            "count": len(prepared),
            "items": prepared,
        },
        "message": f"Создать {len(prepared)} товаров?",
    }
async def find_products_without_weight(
    db: AsyncSession,
    limit: int = 20,
) -> Dict[str, Any]:
    limit = min(int(limit or 20), LIMITS["search_products"])
    
    stmt = (
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.color))
        .where(
            Product.is_active == True,
            or_(Product.weight.is_(None), Product.weight <= 0)
        )
        .order_by(Product.part_number)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "count": len(items),
        "items": [_product_to_dict(p) for p in items],
    }


# ============================================================
# ДИСПЕТЧЕР
# ============================================================

async def execute_tool(
    db: AsyncSession,
    name: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Точка входа для read-tools.
    Для write-tools возвращает preview (requires_confirmation=True).
    Выполнение write-tools — через execute_write_tool (после confirm).
    """
    try:
        if name == "count_products":
            return await count_products(db, **args)
        elif name == "search_products":
            return await search_products(db, **args)
        elif name == "find_missing_part_numbers":
            return await find_missing_part_numbers(db, **args)
        elif name == "check_products_exist":
            return await check_products_exist(db, **args)
        elif name == "get_product_weight":
            return await get_product_weight(db, **args)
        elif name == "find_products_without_weight":  # <-- добавили
            return await find_products_without_weight(db, **args)
        elif name == "list_categories":
            return await list_categories(db)

        # WRITE — preview
        elif name == "update_product_weight":
            return await update_product_weight_preview(db, **args)
        elif name == "update_product_category":
            return await update_product_category_preview(db, **args)
        elif name == "create_category":
            return await create_category_preview(db, **args)
        elif name == "create_products":
            return await create_products_preview(db, **args)

        else:
            raise ToolError(f"Неизвестный tool: {name}")
    except ToolError as e:
        return {"error": str(e)}
    except Exception as e:
        # ДОБАВЛЕНО: чтобы хотя бы в консоль падал трейсбек, а не просто "внутренняя ошибка"
        import traceback
        traceback.print_exc()
        return {"error": f"Внутренняя ошибка: {e}"}


# ============================================================
# ВЫПОЛНЕНИЕ WRITE TOOLS (после confirm)
# ============================================================

async def execute_write_tool(
    db: AsyncSession,
    name: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Выполняет write-tool. Вызывается только после подтверждения.
    Args — те же, что в preview.action.args.
    """
    if name == "update_product_weight":
        return await _do_update_weight(db, **args)
    elif name == "update_product_category":
        return await _do_update_category(db, **args)
    elif name == "create_category":
        return await _do_create_category(db, **args)
    elif name == "create_products":
        return await _do_create_products(db, **args)
    else:
        raise ToolError(f"Неизвестный write-tool: {name}")


async def _do_update_weight(
    db: AsyncSession,
    new_weight: float,
    part_number: Optional[str] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    if part_number:
        stmt = (
            select(Product)
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                func.upper(Product.part_number) == part_number.strip().upper(),
                Product.is_active == True,
            )
        )
    else:
        p = _validate_pattern(pattern)
        stmt = (
            select(Product)
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                Product.is_active == True,
                Product.description.ilike(f"%{p}%"),
            )
            .limit(LIMITS["update_product_weight"] + 1)
        )

    result = await db.execute(stmt)
    products = result.scalars().all()

    if not products:
        raise ToolError("Товары не найдены.")
    if len(products) > LIMITS["update_product_weight"]:
        raise ToolError(f"Слишком много товаров ({len(products)}).")

    for p in products:
        p.weight = new_weight

    await db.commit()

    return {
        "updated_count": len(products),
        "part_numbers": [p.part_number for p in products],
        "new_weight": new_weight,
    }


async def _do_update_category(
    db: AsyncSession,
    category_name: str,
    part_numbers: Optional[List[str]] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    cat = await _get_category_by_name(db, category_name)
    if not cat:
        raise ToolError(f"Категория '{category_name}' не найдена.")

    if part_numbers:
        cleaned = [str(x).strip().upper() for x in part_numbers if str(x).strip()]
        stmt = (
            select(Product)
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                func.upper(Product.part_number).in_(cleaned),
                Product.is_active == True,
            )
        )
    else:
        p = _validate_pattern(pattern)
        stmt = (
            select(Product)
            .options(selectinload(Product.category), selectinload(Product.color))
            .where(
                Product.is_active == True,
                Product.description.ilike(f"%{p}%"),
            )
            .limit(LIMITS["update_product_category"] + 1)
        )

    result = await db.execute(stmt)
    products = result.scalars().all()

    if not products:
        raise ToolError("Товары не найдены.")
    if len(products) > LIMITS["update_product_category"]:
        raise ToolError(f"Слишком много товаров ({len(products)}).")

    for prod in products:
        prod.category_id = cat.id

    await db.commit()

    return {
        "updated_count": len(products),
        "part_numbers": [p.part_number for p in products],
        "category_name": cat.name,
    }


async def _do_create_category(
    db: AsyncSession,
    name: str,
    prefix_ru: str,
    name_eng: Optional[str] = None,
) -> Dict[str, Any]:
    existing = await _get_category_by_name(db, name)
    if existing:
        raise ToolError(f"Категория '{name}' уже существует.")

    cat = Category(
        name=name.strip(),
        prefix_ru=prefix_ru.strip(),
        name_eng=name_eng,
        is_active=True,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    return {
        "created": True,
        "category_id": cat.id,
        "name": cat.name,
        "prefix_ru": cat.prefix_ru,
    }


async def _do_create_products(
    db: AsyncSession,
    products: List[Dict[str, Any]],
) -> Dict[str, Any]:
    created = []
    for it in products:
        prod = Product(
            part_number=it["part_number"],
            description=it["description"],
            model_number=it.get("model_number"),
            category_id=it.get("category_id"),
            weight=it.get("weight"),
            coo=it.get("coo"),
            is_active=True,
        )
        db.add(prod)
        created.append(it["part_number"])

    await db.commit()

    return {
        "created_count": len(created),
        "part_numbers": created,
    }