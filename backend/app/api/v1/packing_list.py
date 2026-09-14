from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from datetime import datetime

from app.database import get_db
from app.models import ProcessingSession, PendingWeight, Product
from app.celery.tasks import process_packing_list

router = APIRouter(prefix="/packing-list", tags=["Packing List"])

UPLOAD_DIR = "/app/uploads"
OUTPUT_DIR = "/app/output"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@router.post("/upload")
async def upload_packing_list(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}_packing_list.xlsx")
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    session = ProcessingSession(
        session_id=session_id,
        status="pending",
        invoice_file=file_path,
        created_at=datetime.utcnow()
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    process_packing_list.delay(session_id)
    
    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Файл загружен, обработка запущена"
    }


@router.get("/status/{session_id}")
async def get_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    pending_stmt = select(PendingWeight).where(
        PendingWeight.session_id == session_id,
        PendingWeight.status == "pending"
    )
    pending_result = await db.execute(pending_stmt)
    pending_count = len(pending_result.scalars().all())
    
    return {
        "session_id": session.session_id,
        "status": session.status,
        "errors": session.errors,
        "result_file": session.result_file,
        "pending_weights_count": pending_count,
        "created_at": session.created_at
    }


@router.get("/pending/{session_id}")
async def get_pending_weights(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PendingWeight).where(
        PendingWeight.session_id == session_id,
        PendingWeight.status == "pending"
    )
    result = await db.execute(stmt)
    pendings = result.scalars().all()
    
    pending_list = []
    for p in pendings:
        pending_list.append({
            "id": p.id,
            "part_number": p.part_number,
            "model_number": p.model_number,
            "qty": p.qty,
            "pallet_no": p.pallet_no,
            "box_no": p.box_no,
            "suggested_weight": p.suggested_weight,
            "status": p.status
        })
    
    return {
        "session_id": session_id,
        "pending_weights": pending_list
    }


@router.post("/pending/{pending_id}/approve")
async def approve_weight(
    pending_id: int,
    weight: float,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PendingWeight).where(
        PendingWeight.id == pending_id,
        PendingWeight.status == "pending"
    )
    result = await db.execute(stmt)
    pending = result.scalar_one_or_none()

    if not pending:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    pending.custom_weight = weight
    pending.status = "approved"

    # Обновляем вес у Product — сначала по part_number, если нет — по model_number
    products = []
    if pending.part_number:
        product_stmt = select(Product).where(Product.part_number == pending.part_number)
        product_result = await db.execute(product_stmt)
        products = product_result.scalars().all()

    if not products and pending.model_number:
        product_stmt = select(Product).where(Product.model_number == pending.model_number)
        product_result = await db.execute(product_stmt)
        products = product_result.scalars().all()

    for product in products:
        product.weight = weight

    if not products:
        print(f"⚠️ Product не найден для part_number={pending.part_number}, "
              f"model_number={pending.model_number}")

    await db.commit()

    remaining_stmt = select(PendingWeight).where(
        PendingWeight.session_id == pending.session_id,
        PendingWeight.status == "pending"
    )
    remaining_result = await db.execute(remaining_stmt)
    remaining = remaining_result.scalars().all()

    if not remaining:
        from app.celery.tasks import process_packing_list
        process_packing_list.delay(pending.session_id)

    return {
        "message": "Вес подтверждён",
        "pending_id": pending_id,
        "products_updated": len(products),
        "remaining": len(remaining)
    }


@router.get("/download/{session_id}")
async def download_result(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Обработка еще не завершена")
    
    result_path = session.result_file
    if not result_path or not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Файл результата не найден")
    
    filename = f"packing_list_{session_id[:8]}.xlsx"
    
    return FileResponse(
        path=result_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
