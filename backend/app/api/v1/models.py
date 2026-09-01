# backend/app/api/v1/models.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from app.database import get_db
from app.models import Product, Category, Color, PendingModel, ProcessingSession
from app.schemas import (
    ProductResponse, ProductCreate, ProductUpdate,
    PendingModelResponse, PendingModelApprove,
    CategoryResponse, ColorResponse
)

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("/", response_model=List[ProductResponse])
async def get_all_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Product).where(Product.is_active == True).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Модель не найдена")
    
    return product


@router.post("/", response_model=ProductResponse)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Product).where(Product.part_number == data.part_number)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Модель с таким артикулом уже существует")
    
    product = Product(**data.dict())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Модель не найдена")
    
    for key, value in data.dict(exclude_unset=True).items():
        setattr(product, key, value)
    
    await db.commit()
    await db.refresh(product)
    
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Модель не найдена")
    
    product.is_active = False
    await db.commit()
    
    return {"message": "Модель удалена"}


# ============================================
# РАБОТА С НОВЫМИ МОДЕЛЯМИ (PENDING)
# ============================================

@router.get("/pending/{session_id}")
async def get_pending_models(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получить список новых моделей, ожидающих подтверждения"""
    stmt = select(PendingModel).where(
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    pendings = result.scalars().all()
    
    if not pendings:
        return {"session_id": session_id, "new_models": [], "message": "Нет новых моделей"}
    
    new_models = []
    for p in pendings:
        # Получаем категорию
        category_name = None
        if p.suggested_category_id:
            cat_stmt = select(Category).where(Category.id == p.suggested_category_id)
            cat_result = await db.execute(cat_stmt)
            cat = cat_result.scalar_one_or_none()
            category_name = cat.name if cat else None
        
        # Получаем цвет
        color_name = None
        if p.suggested_color_id:
            col_stmt = select(Color).where(Color.id == p.suggested_color_id)
            col_result = await db.execute(col_stmt)
            col = col_result.scalar_one_or_none()
            color_name = col.eng if col else None
        
        new_models.append({
            "id": p.id,
            "part_number": p.part_number,
            "model_number": p.model_number,
            "description": p.description,
            "coo": p.coo,
            "suggested_category_id": p.suggested_category_id,
            "suggested_category_name": category_name,
            "suggested_color_id": p.suggested_color_id,
            "suggested_color_name": color_name,
            "suggested_name_ru": p.suggested_name_ru,
            "custom_name_ru": p.custom_name_ru,
            "status": p.status
        })
    
    # Получаем все категории и цвета для выпадающих списков
    categories = await db.execute(select(Category).where(Category.is_active == True))
    colors = await db.execute(select(Color).where(Color.is_active == True))
    
    return {
        "session_id": session_id,
        "new_models": new_models,
        "all_categories": [
            {"id": c.id, "name": c.name, "prefix_ru": c.prefix_ru}
            for c in categories.scalars().all()
        ],
        "all_colors": [
            {"id": c.id, "eng": c.eng, "rus": c.rus}
            for c in colors.scalars().all()
        ]
    }


@router.post("/pending/{session_id}/{pending_id}/approve")
async def approve_pending_model(
    session_id: str,
    pending_id: int,
    data: PendingModelApprove,
    db: AsyncSession = Depends(get_db)
):
    """Подтвердить новую модель и добавить в БД"""
    stmt = select(PendingModel).where(
        PendingModel.id == pending_id,
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Модель не найдена или уже обработана")
    
    category_id = data.custom_category_id or pending.suggested_category_id
    color_id = data.custom_color_id or pending.suggested_color_id
    name_ru = data.custom_name_ru or pending.suggested_name_ru
    
    # Проверяем, что категория существует
    if category_id:
        cat_stmt = select(Category).where(Category.id == category_id)
        cat_result = await db.execute(cat_stmt)
        if not cat_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Указанная категория не найдена")
    
    # Проверяем, что цвет существует
    if color_id:
        col_stmt = select(Color).where(Color.id == color_id)
        col_result = await db.execute(col_stmt)
        if not col_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Указанный цвет не найден")
    
    product = Product(
        part_number=pending.part_number,
        model_number=pending.model_number,
        description=pending.description,
        coo=pending.coo,
        category_id=category_id,
        color_id=color_id,
        custom_name_ru=name_ru,
        is_active=True
    )
    db.add(product)
    
    pending.status = "approved"
    pending.custom_name_ru = name_ru
    pending.custom_category_id = category_id
    pending.custom_color_id = color_id
    
    await db.commit()
    await db.refresh(product)
    
    # Проверяем остальные
    stmt = select(PendingModel).where(
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    remaining = result.scalars().all()
    
    # Если больше нет новых моделей, возобновляем обработку
    if not remaining:
        stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session and session.status == "pending_approval":
            session.status = "pending"
            await db.commit()
            from app.celery.tasks import process_invoice
            process_invoice.delay(session_id)
    
    return {
        "message": "Модель подтверждена и добавлена в БД",
        "product": {
            "id": product.id,
            "part_number": product.part_number,
            "custom_name_ru": product.custom_name_ru
        },
        "remaining_pending": len(remaining)
    }


@router.delete("/pending/{session_id}/{pending_id}/skip")
async def skip_pending_model(
    session_id: str,
    pending_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Пропустить новую модель (не добавлять в БД)"""
    stmt = select(PendingModel).where(
        PendingModel.id == pending_id,
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Модель не найдена или уже обработана")
    
    pending.status = "skipped"
    await db.commit()
    
    stmt = select(PendingModel).where(
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    remaining = result.scalars().all()
    
    if not remaining:
        stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session and session.status == "pending_approval":
            session.status = "error"
            session.errors = "Все новые модели были пропущены, обработка невозможна"
            await db.commit()
    
    return {
        "message": "Модель пропущена",
        "remaining_pending": len(remaining)
    }


@router.post("/pending/{session_id}/approve-all")
async def approve_all_pending(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Подтвердить все новые модели сразу"""
    stmt = select(PendingModel).where(
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    pendings = result.scalars().all()
    
    if not pendings:
        raise HTTPException(status_code=404, detail="Нет новых моделей для подтверждения")
    
    approved_count = 0
    for pending in pendings:
        product = Product(
            part_number=pending.part_number,
            model_number=pending.model_number,
            description=pending.description,
            coo=pending.coo,
            category_id=pending.suggested_category_id,
            color_id=pending.suggested_color_id,
            custom_name_ru=pending.suggested_name_ru,
            is_active=True
        )
        db.add(product)
        pending.status = "approved"
        approved_count += 1
    
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session and session.status == "pending_approval":
        session.status = "pending"
        await db.commit()
        from app.celery.tasks import process_invoice
        process_invoice.delay(session_id)
    
    await db.commit()
    
    return {
        "message": f"Подтверждено {approved_count} моделей",
        "approved_count": approved_count
    }


@router.get("/pending/status/{session_id}")
async def get_pending_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получить статус новых моделей для сессии"""
    stmt = select(PendingModel).where(
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    pending_count = len(result.scalars().all())
    
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    return {
        "session_id": session_id,
        "session_status": session.status if session else None,
        "pending_models_count": pending_count,
        "has_pending": pending_count > 0
    }


@router.get("/pending/categories-colors")
async def get_categories_and_colors(
    db: AsyncSession = Depends(get_db)
):
    """Получить все категории и цвета для выпадающих списков"""
    categories = await db.execute(select(Category).where(Category.is_active == True))
    colors = await db.execute(select(Color).where(Color.is_active == True))
    
    return {
        "categories": [
            {"id": c.id, "name": c.name, "prefix_ru": c.prefix_ru}
            for c in categories.scalars().all()
        ],
        "colors": [
            {"id": c.id, "eng": c.eng, "rus": c.rus}
            for c in colors.scalars().all()
        ]
    }