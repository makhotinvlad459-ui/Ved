# backend/app/api/v1/chestny_znak.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from datetime import datetime

from app.database import get_db
from app.models import ProcessingSession
from app.celery.tasks import process_chestny_znak

router = APIRouter(prefix="/chestny-znak", tags=["Chestny Znak"])

UPLOAD_DIR = "/app/uploads"
OUTPUT_DIR = "/app/output"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@router.post("/upload")
async def upload_cz_files(
    invoice: UploadFile = File(...),
    specification: UploadFile = File(...),
    cz_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    session_id = str(uuid.uuid4())

    invoice_path = os.path.join(UPLOAD_DIR, f"{session_id}_cz_invoice.xlsx")
    spec_path = os.path.join(UPLOAD_DIR, f"{session_id}_cz_spec.xlsx")
    cz_path = os.path.join(UPLOAD_DIR, f"{session_id}_cz_codes.xlsx")

    with open(invoice_path, "wb") as f:
        f.write(await invoice.read())
    with open(spec_path, "wb") as f:
        f.write(await specification.read())
    with open(cz_path, "wb") as f:
        f.write(await cz_file.read())

    session = ProcessingSession(
        session_id=session_id,
        status="pending",
        invoice_file=invoice_path,       # инвойс
        manifest_file=cz_path,           # файл ЧЗ
        template_file=spec_path,         # спецификация-шаблон
        created_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    process_chestny_znak.delay(session_id)

    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Файлы загружены, обработка запущена",
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

    filename = f"ЧЗ - код №{session.spec_number or session_id[:8]}.xlsx"

    return FileResponse(
        path=result_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )