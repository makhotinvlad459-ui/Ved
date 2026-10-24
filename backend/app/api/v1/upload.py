# backend/app/api/v1/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
from datetime import datetime
import shutil
import re
import tempfile

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
    
    filename = os.path.basename(result_path)

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


# ============================================================
# НОВЫЙ ЭНДПОИНТ ДЛЯ ДЕКЛАРИРОВАНИЯ (ПОСТ + ОДИН ФАЙЛ)
# ============================================================
@router.post("/declaration-text")
async def get_declaration_text(
    invoice: UploadFile = File(...)
):
    from app.services.parser import parse_invoice

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await invoice.read())
        tmp_path = tmp.name

    try:
        invoice_data = parse_invoice(tmp_path)
        items = invoice_data.get("items", [])
        
        summary = {}
        
        for item in items:
            desc = item.get("description", "")
            model_num = item.get("model_number", "")
            qty = item.get("qty", 0)
            
            if not desc or qty <= 0:
                continue

            clean_name = desc.split(" (")[0].strip()
            clean_name = re.sub(r'^(Apple|Samsung|Google|Beats)\s+', '', clean_name, flags=re.IGNORECASE)
            
            # === 1. СПЕЦИАЛЬНЫЕ ПРАВИЛА ===
            if re.search(r'Watch (SE|Series)', clean_name, re.IGNORECASE):
                m = re.search(r'Watch (?:SE|Series)\s+\d+', clean_name, re.IGNORECASE)
                if m:
                    clean_name = re.sub(r'\s+', ' ', m.group(0)).strip()
                else:
                    clean_name = "Apple Watch"

            elif "Band for Apple Watch" in clean_name:
                clean_name = "Band for Apple Watch"

            elif re.search(r'AirPods', clean_name, re.IGNORECASE):
                if "Wireless" in clean_name:
                    clean_name = "AirPods with Wireless Charging Case"
                else:
                    clean_name = "AirPods"

            elif re.search(r'Fitbit', clean_name, re.IGNORECASE):
                clean_name = "Google Fitbit Air"

            elif "Crossbody Strap" in clean_name:
                clean_name = "Crossbody Strap"

            elif re.search(r'iPad Pro \d+', clean_name, re.IGNORECASE):
                m = re.search(r'iPad Pro \d+["\u201d\u2033]?', clean_name, re.IGNORECASE)
                if m:
                    clean_name = m.group(0).replace('"', '').strip()
                else:
                    clean_name = "iPad Pro"
                    
            elif re.search(r'MacBook (Air|Pro)', clean_name, re.IGNORECASE):
                m = re.search(r'MacBook (?:Air|Pro)\s+\d+["\u201d\u2033]?', clean_name, re.IGNORECASE)
                if m:
                    clean_name = m.group(0).replace('"', '').strip()
                    
            elif "Mac Mini" in clean_name:
                clean_name = "Mac Mini"
                
            elif "iPhone" in clean_name:
                if "Duo" in clean_name:
                    clean_name = "iPhone Duo"
                else:
                    m = re.search(r'iPhone\s+\d+(?:\s+(?:Pro|Max|Plus|Air|Mini))?', clean_name, re.IGNORECASE)
                    if m:
                        clean_name = m.group(0)
                    else:
                        clean_name = "iPhone"

            # === 2. ОБЩАЯ ОЧИСТКА ===
            else:
                # Убираем память
                clean_name = re.sub(r'\b\d+(?:Gb|GB|Tb|TB|Гб|Тб)\b', '', clean_name, flags=re.IGNORECASE)
                # Убираем цвета
                colors = ["Black", "White", "Silver", "Blue", "Green", "Yellow", "Pink", "Purple", 
                          "Gold", "Grey", "Gray", "Midnight", "Starlight", "Space", "Burgundy", 
                          "Red", "Orange", "Glacier", "Star", "Crisp", "Sand", "Taupe", "Olive"]
                for color in colors:
                    clean_name = re.sub(rf'\b{re.escape(color)}\b', '', clean_name, flags=re.IGNORECASE)
                # Убираем "with ..."
                clean_name = re.sub(r'\bwith\b.*$', '', clean_name, flags=re.IGNORECASE)
                # Убираем размеры типа 44mm, 13"
                clean_name = re.sub(r'\b\d+mm\b', '', clean_name, flags=re.IGNORECASE)
                clean_name = re.sub(r'\b\d+["\u201d\u2033]\b', '', clean_name, flags=re.IGNORECASE)
                
                # Чистим хвосты (дефисы, пробелы)
                clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                clean_name = re.sub(r'^[\s\-\/,]+|[\s\-\/,]+$', '', clean_name).strip()

            if not clean_name or len(clean_name) < 2:
                clean_name = desc.split(" (")[0].strip()

            # === 3. ГРУППИРОВКА ===
            key = clean_name
            if key not in summary:
                summary[key] = {}
                
            if model_num:
                # Если модель имеет несколько слов (A3531 A3532 A3530), объединяем их для сортировки
                model_clean = " ".join(sorted(model_num.split()))
                summary[key][model_clean] = summary[key].get(model_clean, 0) + qty
            else:
                summary[key]["—"] = summary[key].get("—", 0) + qty

        lines = []
        for model_name, models_dict in summary.items():
            if len(models_dict) == 1 and "—" in models_dict:
                lines.append(f"{model_name} - {list(models_dict.values())[0]} шт.;")
            else:
                models_str = ", ".join([f"модель {m} - {q} шт." for m, q in sorted(models_dict.items()) if m != "—"])
                if "—" in models_dict:
                     models_str += f", без модели - {models_dict['—']} шт."
                lines.append(f"{model_name}, {models_str};")
            
        text = "\n".join(lines)
        return {"text": text}
        
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)