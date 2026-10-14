# backend/app/api/v1/for_alice.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as sync_sessionmaker
from typing import List, Optional
from pydantic import BaseModel
import os
import uuid

from app.database import get_db
from app.models import Product, ProcessingSession


router = APIRouter(prefix="/for-alice", tags=["For Alice"])

OUTPUT_DIR = "/app/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# СХЕМЫ
# ============================================================

class ForAliceItem(BaseModel):
    name: str
    qty: int
    price: float


class ForAliceRequest(BaseModel):
    items: List[ForAliceItem]
    logistics_rate_usd: float
    usd_to_aed: float = 3.674
    documents_cost_aed: float


class SaveWeightRequest(BaseModel):
    part_number: Optional[str] = None
    weight: float


# ============================================================
# РАСЧЁТ
# ============================================================

@router.post("/process")
async def process_for_alice(
    data: ForAliceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Принимает строки + параметры, возвращает результат расчёта.
    """
    from app.services.for_alice_calculator import calculate_for_alice

    DATABASE_URL = os.getenv("DATABASE_URL")
    sync_engine = create_engine(DATABASE_URL)
    SyncSession = sync_sessionmaker(bind=sync_engine)

    try:
        with SyncSession() as sync_db:
            result = calculate_for_alice(
                items=[it.dict() for it in data.items],
                logistics_rate_usd=data.logistics_rate_usd,
                usd_to_aed=data.usd_to_aed,
                documents_cost_aed=data.documents_cost_aed,
                db=sync_db,
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Ошибка расчёта: {e}")
    finally:
        sync_engine.dispose()

    return result


# ============================================================
# СОХРАНЕНИЕ ВЕСА
# ============================================================

@router.post("/save-weight")
async def save_weight(
    data: SaveWeightRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Сохраняет вес для Product по part_number.
    Если part_number нет в БД — ошибка.
    """
    if not data.part_number:
        raise HTTPException(status_code=400, detail="part_number обязателен")

    from sqlalchemy import select
    stmt = select(Product).where(Product.part_number == data.part_number)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Товар {data.part_number} не найден в БД",
        )

    product.weight = data.weight
    await db.commit()

    return {
        "message": "Вес сохранён",
        "part_number": data.part_number,
        "weight": data.weight,
    }


# ============================================================
# ГЕНЕРАЦИЯ XLSX
# ============================================================

@router.post("/generate")
async def generate_for_alice(
    data: ForAliceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Считает + генерирует xlsx. Возвращает session_id для скачивания.
    """
    from app.services.for_alice_calculator import calculate_for_alice
    from app.services.for_alice_generator import generate_for_alice_xlsx

    session_id = str(uuid.uuid4())

    DATABASE_URL = os.getenv("DATABASE_URL")
    sync_engine = create_engine(DATABASE_URL)
    SyncSession = sync_sessionmaker(bind=sync_engine)

    try:
        with SyncSession() as sync_db:
            result = calculate_for_alice(
                items=[it.dict() for it in data.items],
                logistics_rate_usd=data.logistics_rate_usd,
                usd_to_aed=data.usd_to_aed,
                documents_cost_aed=data.documents_cost_aed,
                db=sync_db,
            )

            if result["missing"]:
                return {
                    "status": "missing_weights",
                    "missing": result["missing"],
                    "rows": result["rows"],
                    "totals": result["totals"],
                }

            xlsx_path = generate_for_alice_xlsx(result, session_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Ошибка генерации: {e}")
    finally:
        sync_engine.dispose()

    return {
        "status": "completed",
        "session_id": session_id,
        "rows": result["rows"],
        "totals": result["totals"],
    }


@router.get("/download/{session_id}")
async def download_for_alice(session_id: str):
    """Скачать готовый xlsx."""
    path = os.path.join(OUTPUT_DIR, f"for_alice_{session_id[:8]}.xlsx")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        path=path,
        filename=f"For_Alice_{session_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )