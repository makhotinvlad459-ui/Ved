# backend/app/api/v1/for_alice.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine, select
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
    name: Optional[str] = None
    weight: float


# ============================================================
# РАСЧЁТ
# ============================================================

@router.post("/process")
async def process_for_alice(
    data: ForAliceRequest,
    db: AsyncSession = Depends(get_db),
):
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
# СОХРАНЕНИЕ ВЕСА (с автосозданием товара)
# ============================================================

@router.post("/save-weight")
async def save_weight(
    data: SaveWeightRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Сохраняет вес для Product по part_number.
    Если товара нет — создаёт новый с указанным весом.
    """
    if not data.part_number:
        raise HTTPException(status_code=400, detail="part_number обязателен")
    if data.weight is None or data.weight <= 0:
        raise HTTPException(status_code=400, detail="Вес должен быть > 0")

    stmt = select(Product).where(Product.part_number == data.part_number)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if product:
        # Обновляем существующий
        product.weight = data.weight
        if data.name and not product.description:
            product.description = data.name
        await db.commit()
        return {
            "message": "Вес обновлён",
            "created": False,
            "part_number": data.part_number,
            "weight": data.weight,
            "product_id": product.id,
        }
    else:
        # Ищем sibling с таким же description, у которого есть категория
        inherited_category_id = None
        inherited_color_id = None

        if data.name:
            sibling_stmt = select(Product).where(
                Product.description == data.name,
                Product.category_id.isnot(None),
            ).limit(1)
            sibling_result = await db.execute(sibling_stmt)
            sibling = sibling_result.scalar_one_or_none()

            if sibling:
                inherited_category_id = sibling.category_id
                inherited_color_id = sibling.color_id

        new_product = Product(
            part_number=data.part_number,
            model_number="",
            description=data.name or data.part_number,
            weight=data.weight,
            category_id=inherited_category_id,
            color_id=inherited_color_id,
            is_active=True,
        )
        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)
        return {
            "message": "Товар создан" + (
                " (категория унаследована)" if inherited_category_id else ""
            ),
            "created": True,
            "part_number": data.part_number,
            "weight": data.weight,
            "product_id": new_product.id,
            "inherited_category_id": inherited_category_id,
            "inherited_color_id": inherited_color_id,
        }


# ============================================================
# ГЕНЕРАЦИЯ XLSX
# ============================================================

@router.post("/generate")
async def generate_for_alice(
    data: ForAliceRequest,
    db: AsyncSession = Depends(get_db),
):
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
    path = os.path.join(OUTPUT_DIR, f"for_alice_{session_id[:8]}.xlsx")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        path=path,
        filename=f"For_Alice_{session_id[:8]}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )