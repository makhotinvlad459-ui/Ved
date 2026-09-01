# backend/app/api/v1/colors.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Color
from app.schemas import ColorCreate, ColorResponse

router = APIRouter(prefix="/colors", tags=["Colors"])


@router.post("/", response_model=ColorResponse)
async def create_color(
    data: ColorCreate,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем, существует ли уже
    stmt = select(Color).where(Color.eng == data.eng)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Цвет уже существует")
    
    color = Color(**data.dict())
    db.add(color)
    await db.commit()
    await db.refresh(color)
    return color


@router.get("/", response_model=list[ColorResponse])
async def get_all_colors(
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Color).where(Color.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()