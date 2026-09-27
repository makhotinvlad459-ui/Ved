# backend/app/api/v1/cz_codes.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from datetime import datetime

from app.database import get_db
from app.models import ProcessingSession
from app.celery.tasks import process_cz_codes

router = APIRouter(prefix="/cz-codes", tags=["CZ Codes"])

UPLOAD_DIR = "/app/uploads"
OUTPUT_DIR = "/app/output"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@router.post("/upload")
async def upload_cz_spec(
    cz_spec: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}_cz_codes.xlsx")

    with open(file_path, "wb") as f:
        f.write(await cz_spec.read())

    session = ProcessingSession(
        session_id=session_id,
        status="pending",
        template_file=file_path,
        created_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    process_cz_codes.delay(session_id)

    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Файл загружен, обработка запущена",
    }


@router.get("/status/{session_id}")
async def get_status(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    return {
        "session_id": session.session_id,
        "status": session.status,
        "errors": session.errors,
        "result_file": session.result_file,
        "spec_number": session.spec_number,
        "created_at": session.created_at,
    }


@router.get("/download/{session_id}")
async def download_result(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ProcessingSession).where(ProcessingSession.session_id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Обработка ещё не завершена")

    result_path = session.result_file
    if not result_path or not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Файл результата не найден")

    filename = os.path.basename(result_path)

    return FileResponse(
        path=result_path,
        filename=filename,
        media_type="application/zip",
    )