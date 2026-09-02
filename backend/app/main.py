# backend/app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import upload, models, categories, colors, packing_list

from app.database import get_db

app = FastAPI(
    title="VED Excel Processor",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(upload.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")  
app.include_router(colors.router, prefix="/api/v1")   
app.include_router(packing_list.router, prefix="/api/v1")   


@app.get("/")
async def root():
    return {"message": "VED Excel Processor API"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Получить все категории"""
    from app.models import Category
    stmt = select(Category).where(Category.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/v1/colors")
async def get_colors(db: AsyncSession = Depends(get_db)):
    """Получить все цвета"""
    from app.models import Color
    stmt = select(Color).where(Color.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()