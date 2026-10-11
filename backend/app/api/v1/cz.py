# backend/app/api/v1/cz.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as sync_sessionmaker
from typing import List, Optional
import os
import uuid
from datetime import datetime

from app.database import get_db
from app.models import (
    CzCardProduct, CzColorMapping, CzCategoryMapping,
    ProcessingSession,
)
from app.schemas import (
    CzCardProductCreate, CzCardProductUpdate, CzCardProductResponse,
    CzColorMappingCreate, CzColorMappingUpdate, CzColorMappingResponse,
    CzCategoryMappingCreate, CzCategoryMappingUpdate, CzCategoryMappingResponse,
    CzParseResponse, CzParsedItem,
    CzGenerateRequest, CzGenerateResponse,
)

router = APIRouter(prefix="/cz", tags=["Chestny Znak — Card Data"])

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# CZ CARD PRODUCTS
# ============================================================

@router.get("/card-products", response_model=List[CzCardProductResponse])
async def get_card_products(
    q: Optional[str] = None,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzCardProduct)
    if not include_inactive:
        stmt = stmt.where(CzCardProduct.is_active == True)
    if q:
        q = q.strip()
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                or_(
                    CzCardProduct.part_number.ilike(pattern),
                    CzCardProduct.model_name.ilike(pattern),
                    CzCardProduct.brand.ilike(pattern),
                )
            )
    stmt = stmt.order_by(
        CzCardProduct.brand,
        CzCardProduct.model_name,
        CzCardProduct.part_number,
    ).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/card-products/{product_id}", response_model=CzCardProductResponse)
async def get_card_product(product_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(CzCardProduct).where(CzCardProduct.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


@router.post("/card-products", response_model=CzCardProductResponse)
async def create_card_product(
    data: CzCardProductCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzCardProduct).where(CzCardProduct.part_number == data.part_number)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Товар с таким part_number уже существует")

    product = CzCardProduct(**data.dict())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/card-products/{product_id}", response_model=CzCardProductResponse)
async def update_card_product(
    product_id: int,
    data: CzCardProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzCardProduct).where(CzCardProduct.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    update_data = data.dict(exclude_unset=True)

    if "part_number" in update_data and update_data["part_number"] != product.part_number:
        stmt = select(CzCardProduct).where(
            CzCardProduct.part_number == update_data["part_number"]
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Товар с таким part_number уже существует",
            )

    for key, value in update_data.items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/card-products/{product_id}")
async def delete_card_product(product_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(CzCardProduct).where(CzCardProduct.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    product.is_active = False
    await db.commit()
    return {"message": "Товар удалён"}


# ============================================================
# CZ COLOR MAPPINGS
# ============================================================

@router.get("/color-mappings", response_model=List[CzColorMappingResponse])
async def get_color_mappings(
    q: Optional[str] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzColorMapping)
    if not include_inactive:
        stmt = stmt.where(CzColorMapping.is_active == True)
    if q:
        q = q.strip()
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                or_(
                    CzColorMapping.eng.ilike(pattern),
                    CzColorMapping.cz_value.ilike(pattern),
                )
            )
    stmt = stmt.order_by(CzColorMapping.eng)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/color-mappings", response_model=CzColorMappingResponse)
async def create_color_mapping(
    data: CzColorMappingCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzColorMapping).where(CzColorMapping.eng == data.eng)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Цвет уже существует")

    color = CzColorMapping(**data.dict())
    db.add(color)
    await db.commit()
    await db.refresh(color)
    return color


@router.put("/color-mappings/{color_id}", response_model=CzColorMappingResponse)
async def update_color_mapping(
    color_id: int,
    data: CzColorMappingUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzColorMapping).where(CzColorMapping.id == color_id)
    result = await db.execute(stmt)
    color = result.scalar_one_or_none()
    if not color:
        raise HTTPException(status_code=404, detail="Цвет не найден")

    update_data = data.dict(exclude_unset=True)
    if "eng" in update_data and update_data["eng"] != color.eng:
        stmt = select(CzColorMapping).where(CzColorMapping.eng == update_data["eng"])
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Цвет с таким eng уже существует")

    for key, value in update_data.items():
        setattr(color, key, value)

    await db.commit()
    await db.refresh(color)
    return color


@router.delete("/color-mappings/{color_id}")
async def delete_color_mapping(color_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(CzColorMapping).where(CzColorMapping.id == color_id)
    result = await db.execute(stmt)
    color = result.scalar_one_or_none()
    if not color:
        raise HTTPException(status_code=404, detail="Цвет не найден")
    color.is_active = False
    await db.commit()
    return {"message": "Цвет удалён"}


# ============================================================
# CZ CATEGORY MAPPINGS
# ============================================================

@router.get("/category-mappings", response_model=List[CzCategoryMappingResponse])
async def get_category_mappings(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzCategoryMapping)
    if not include_inactive:
        stmt = stmt.where(CzCategoryMapping.is_active == True)
    stmt = stmt.order_by(CzCategoryMapping.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/category-mappings", response_model=CzCategoryMappingResponse)
async def create_category_mapping(
    data: CzCategoryMappingCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzCategoryMapping).where(CzCategoryMapping.name == data.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Категория уже существует")

    cat = CzCategoryMapping(**data.dict())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/category-mappings/{cat_id}", response_model=CzCategoryMappingResponse)
async def update_category_mapping(
    cat_id: int,
    data: CzCategoryMappingUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CzCategoryMapping).where(CzCategoryMapping.id == cat_id)
    result = await db.execute(stmt)
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    update_data = data.dict(exclude_unset=True)
    if "name" in update_data and update_data["name"] != cat.name:
        stmt = select(CzCategoryMapping).where(CzCategoryMapping.name == update_data["name"])
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Категория с таким именем уже есть")

    for key, value in update_data.items():
        setattr(cat, key, value)

    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/category-mappings/{cat_id}")
async def delete_category_mapping(cat_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(CzCategoryMapping).where(CzCategoryMapping.id == cat_id)
    result = await db.execute(stmt)
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    cat.is_active = False
    await db.commit()
    return {"message": "Категория удалена"}


# ============================================================
# ПАРСИНГ ИНВОЙСА
# ============================================================

@router.post("/cards/parse-invoice", response_model=CzParseResponse)
async def parse_cz_invoice(
    invoice: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    from app.services.cz_invoice_parser import parse_invoice_for_cz

    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}_cz_invoice.xlsx")

    with open(file_path, "wb") as f:
        f.write(await invoice.read())

    session = ProcessingSession(
        session_id=session_id,
        status="parsed",
        invoice_file=file_path,
        created_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()

    try:
        items = parse_invoice_for_cz(file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга: {e}")

    return {
        "session_id": session_id,
        "total": len(items),
        "items": [CzParsedItem(**it) for it in items],
    }


# ============================================================
# ГЕНЕРАЦИЯ K3-ФАЙЛОВ
# ============================================================

@router.post("/cards/generate", response_model=CzGenerateResponse)
async def generate_cz_cards(
    data: CzGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.cz_invoice_parser import parse_invoice_for_cz
    from app.services.cz_card_generator import generate_cz_cards_zip

    stmt = select(ProcessingSession).where(
        ProcessingSession.session_id == data.session_id
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if not session.invoice_file or not os.path.exists(session.invoice_file):
        raise HTTPException(status_code=404, detail="Файл инвойса не найден")

    try:
        parsed_items = parse_invoice_for_cz(session.invoice_file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка парсинга: {e}")

    DATABASE_URL = os.getenv("DATABASE_URL")
    sync_engine = create_engine(DATABASE_URL)
    SyncSession = sync_sessionmaker(bind=sync_engine)

    try:
        with SyncSession() as sync_db:
            zip_path, files_info = generate_cz_cards_zip(
                session_id=data.session_id,
                parsed_items=parsed_items,
                selected_part_numbers=data.part_numbers,
                db=sync_db,
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка генерации: {e}")
    finally:
        sync_engine.dispose()

    session.status = "completed"
    session.result_file = zip_path
    await db.commit()

    return {
        "session_id": data.session_id,
        "status": "completed",
        "files": files_info,
        "zip_name": os.path.basename(zip_path),
    }


@router.get("/cards/download/{session_id}")
async def download_cz_cards(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProcessingSession).where(
        ProcessingSession.session_id == session_id
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if not session.result_file or not os.path.exists(session.result_file):
        raise HTTPException(status_code=404, detail="Файл результата не найден")

    filename = os.path.basename(session.result_file)

    return FileResponse(
        path=session.result_file,
        filename=filename,
        media_type="application/zip",
    )