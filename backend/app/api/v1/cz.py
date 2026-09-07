from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import Response, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from datetime import datetime

from app.database import get_db
from app.models import ProcessingSession, GtinProduct, PendingGtin
from app.celery.tasks import process_cz
from app.schemas import PendingGtinApprove

router = APIRouter(prefix="/cz", tags=["Chessny Znak"])

UPLOAD_DIR = "/app/uploads"
OUTPUT_DIR = "/app/output"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@router.post("/upload")
async def upload_cz_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}_cz.xlsx")
    
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
    
    process_cz.delay(session_id)
    
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
    
    pending_stmt = select(PendingGtin).where(
        PendingGtin.session_id == session_id,
        PendingGtin.status == "pending"
    )
    pending_result = await db.execute(pending_stmt)
    pending_count = len(pending_result.scalars().all())
    
    return {
        "session_id": session.session_id,
        "status": session.status,
        "errors": session.errors,
        "result_file": session.result_file,
        "pending_gtins_count": pending_count if session.status == "pending_gtins" else 0,
        "created_at": session.created_at
    }


@router.get("/pending/{session_id}")
async def get_pending_gtins(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PendingGtin).where(
        PendingGtin.session_id == session_id,
        PendingGtin.status == "pending"
    )
    result = await db.execute(stmt)
    pendings = result.scalars().all()
    
    return {
        "session_id": session_id,
        "pending_gtins": [
            {
                "id": p.id,
                "gtin": p.gtin,
                "code_count": p.code_count,
                "suggested_name": p.suggested_name,
                "status": p.status
            }
            for p in pendings
        ]
    }


@router.post("/pending/{pending_id}/approve")
async def approve_gtin(
    pending_id: int,
    data: PendingGtinApprove,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PendingGtin).where(PendingGtin.id == pending_id)
    result = await db.execute(stmt)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    gtin_stmt = select(GtinProduct).where(GtinProduct.gtin == pending.gtin)
    gtin_result = await db.execute(gtin_stmt)
    if gtin_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="GTIN уже существует в БД")
    
    product = GtinProduct(
        gtin=pending.gtin,
        part_number=data.part_number,
        model_number=data.model_number,
        coo=data.coo,
        product_name=data.product_name,
        category_name=data.category_name,
        is_active=True
    )
    db.add(product)
    
    pending.status = "approved"
    pending.part_number = data.part_number
    pending.model_number = data.model_number
    pending.coo = data.coo
    pending.product_name = data.product_name
    pending.category_name = data.category_name
    
    await db.commit()
    
    remaining_stmt = select(PendingGtin).where(
        PendingGtin.session_id == pending.session_id,
        PendingGtin.status == "pending"
    )
    remaining_result = await db.execute(remaining_stmt)
    remaining = remaining_result.scalars().all()
    
    if not remaining:
        from app.celery.tasks import process_cz
        process_cz.delay(pending.session_id)
    
    return {
        "message": "GTIN привязан к товару",
        "pending_id": pending_id,
        "remaining": len(remaining)
    }


@router.delete("/pending/{pending_id}/skip")
async def skip_gtin(
    pending_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PendingGtin).where(PendingGtin.id == pending_id)
    result = await db.execute(stmt)
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    pending.status = "skipped"
    await db.commit()
    
    return {"message": "GTIN пропущен"}


@router.get("/download/{session_id}")
async def download_result(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    import zipfile
    import io
    
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Обработка еще не завершена")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename in os.listdir(OUTPUT_DIR):
            if filename.startswith(session_id):
                file_path = os.path.join(OUTPUT_DIR, filename)
                arcname = filename.replace(f"{session_id}_", "")
                zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=cz_{session_id[:8]}.zip"}
    )
