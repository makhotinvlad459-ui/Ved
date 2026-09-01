# backend/app/api/v1/categories.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Category
from app.schemas import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем, существует ли уже
    stmt = select(Category).where(Category.name == data.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Категория уже существует")
    
    category = Category(**data.dict())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/", response_model=list[CategoryResponse])
async def get_all_categories(
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Category).where(Category.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()