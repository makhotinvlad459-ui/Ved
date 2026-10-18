# backend/app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import (
    upload, models, categories, colors, packing_list,
    chestny_znak, commercial_offer, cz_codes,
    cz, for_alice,
)

from app.database import get_db

# ============================================================
# НАСТРОЙКИ БЕЗОПАСНОСТИ
# ============================================================

# Разрешённые origin для CORS.
# Замени/добавь свои домены, если появятся.
ALLOWED_ORIGINS = [
    "http://89.38.131.221",
    "http://89.38.131.221:80",
    "https://89.38.131.221",
    "http://localhost",
    "http://localhost:80",
    "http://127.0.0.1",
    "http://127.0.0.1:80",
]

app = FastAPI(
    title="VED Excel Processor",
    version="0.1.0",
    # Отключаем публичные доки — они светят структуру API
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS — только конкретные origin, без "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ============================================================
# РОУТЕРЫ
# ============================================================

app.include_router(upload.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(colors.router, prefix="/api/v1")
app.include_router(packing_list.router, prefix="/api/v1")
app.include_router(chestny_znak.router, prefix="/api/v1")
app.include_router(commercial_offer.router, prefix="/api/v1")
app.include_router(cz_codes.router, prefix="/api/v1")
app.include_router(cz.router, prefix="/api/v1")
app.include_router(for_alice.router, prefix="/api/v1")


# ============================================================
# СЛУЖЕБНЫЕ ЭНДПОИНТЫ
# ============================================================

@app.get("/")
async def root():
    return {"message": "VED Excel Processor API"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    from app.models import Category
    stmt = select(Category).where(Category.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/v1/colors")
async def get_colors(db: AsyncSession = Depends(get_db)):
    from app.models import Color
    stmt = select(Color).where(Color.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()