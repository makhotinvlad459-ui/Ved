# backend/app/api/v1/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from datetime import datetime
import shutil

from app.database import get_db
from app.models import ProcessingSession, PendingModel
from app.celery.tasks import process_invoice

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = "/app/uploads"
TEMPLATE_DIR = "/app/templates"
OUTPUT_DIR = "/app/output"
TEMP_DIR = "/app/temp"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


@router.post("/")
async def upload_files(
    invoice: UploadFile = File(...),
    manifest: UploadFile = File(...),
    template: UploadFile = File(...),
    spec_number: str = Form(default=""),
    db: AsyncSession = Depends(get_db)
):
    session_id = str(uuid.uuid4())
    
    invoice_path = os.path.join(UPLOAD_DIR, f"{session_id}_invoice.xlsx")
    manifest_path = os.path.join(UPLOAD_DIR, f"{session_id}_manifest.xlsx")
    template_path = os.path.join(TEMPLATE_DIR, f"{session_id}_template.xlsx")
    
    with open(invoice_path, "wb") as f:
        f.write(await invoice.read())
    with open(manifest_path, "wb") as f:
        f.write(await manifest.read())
    with open(template_path, "wb") as f:
        f.write(await template.read())
    
    session = ProcessingSession(
        session_id=session_id,
        status="pending",
        invoice_file=invoice_path,
        manifest_file=manifest_path,
        template_file=template_path,
        spec_number=spec_number,
        created_at=datetime.utcnow()
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    process_invoice.delay(session_id)
    
    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Файлы загружены, обработка запущена"
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
    
    # Считаем количество новых моделей (если есть)
    pending_count = 0
    if session.status == "pending_approval":
        pending_stmt = select(PendingModel).where(
            PendingModel.session_id == session_id,
            PendingModel.status == "pending"
        )
        pending_result = await db.execute(pending_stmt)
        pending_count = len(pending_result.scalars().all())
    
    return {
        "session_id": session.session_id,
        "status": session.status,
        "spec_number": session.spec_number,
        "total_items": session.total_items,
        "processed_items": session.processed_items,
        "errors": session.errors,
        "result_file": session.result_file,
        "created_at": session.created_at,
        "invoice_date": session.invoice_date,
        "spec_date": session.spec_date,
        "pending_models_count": pending_count if session.status == "pending_approval" else 0,
        "message": f"Ожидается подтверждение {pending_count} новых моделей" if pending_count > 0 else None
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
    
    filename = f"specification_{session.spec_number or session_id}.xlsx"
    
    return FileResponse(
        path=result_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.delete("/cleanup/{session_id}")
async def cleanup_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Полная очистка всех файлов сессии"""
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    files_to_delete = [
        session.invoice_file,
        session.manifest_file,
        session.template_file,
        session.result_file
    ]
    
    deleted = []
    errors = []
    
    for file_path in files_to_delete:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted.append(os.path.basename(file_path))
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")
    
    # Также удаляем записи о новых моделях
    pending_stmt = select(PendingModel).where(PendingModel.session_id == session_id)
    pending_result = await db.execute(pending_stmt)
    pendings = pending_result.scalars().all()
    for p in pendings:
        p.status = "cleaned"
    
    session.status = "cleaned"
    await db.commit()
    
    return {
        "message": f"Удалено файлов: {len(deleted)}",
        "files": deleted,
        "errors": errors if errors else None,
        "session_id": session_id
    }


@router.get("/pending-count/{session_id}")
async def get_pending_count(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получить количество новых моделей, ожидающих подтверждения"""
    stmt = select(PendingModel).where(
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    )
    result = await db.execute(stmt)
    pending_count = len(result.scalars().all())
    
    return {
        "session_id": session_id,
        "pending_models_count": pending_count,
        "has_pending": pending_count > 0
    }