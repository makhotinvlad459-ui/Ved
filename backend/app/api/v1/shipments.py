# backend/app/api/v1/shipments.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database import get_db
from app.models import Shipment, ShipmentTask
from app.schemas import (
    ShipmentCreate, ShipmentUpdate, ShipmentResponse,
    ShipmentTaskCreate, ShipmentTaskUpdate, ShipmentTaskResponse
)

router = APIRouter(prefix="/shipments", tags=["Shipments"])

# ========== ПОСТАВКИ ==========

@router.post("/", response_model=ShipmentResponse)
async def create_shipment(
    data: ShipmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новую поставку с задачами"""
    shipment = Shipment(**data.dict())
    db.add(shipment)
    await db.flush()
    
    # Создаём задачи по умолчанию
    default_tasks = [
        # Инвойс
        {"task_key": "invoice", "task_name": "Инвойс - сверка, редактирование, отправка брокеру", "parent_task": None, "order_index": 1},
        
        # Декларация
        {"task_key": "declaration_create", "task_name": "Создание отправка брокеру", "parent_task": "declaration", "order_index": 10},
        {"task_key": "declaration_certificates", "task_name": "Файл сертификации", "parent_task": "declaration", "order_index": 11},
        {"task_key": "declaration_application", "task_name": "Заявление", "parent_task": "declaration", "order_index": 12},
        {"task_key": "declaration_fsa", "task_name": "Создание на FSA", "parent_task": "declaration", "order_index": 13},
        
        # Честный знак
        {"task_key": "cz_card", "task_name": "Создание карточки/редактирование", "parent_task": "cz", "order_index": 20},
        {"task_key": "cz_qr_order", "task_name": "Заказ QR кодов", "parent_task": "cz", "order_index": 21},
        {"task_key": "cz_qr_export", "task_name": "Выгрузка кодов брокеру", "parent_task": "cz", "order_index": 22},
        {"task_key": "cz_qr_send", "task_name": "Отправка кодов брокеру на основе спецификации", "parent_task": "cz", "order_index": 23},
        
        # Остальные
        {"task_key": "specification", "task_name": "Спецификация", "parent_task": None, "order_index": 30},
        {"task_key": "complectation", "task_name": "Комплектация", "parent_task": None, "order_index": 40},
        {"task_key": "packing_list", "task_name": "Упаковочный лист", "parent_task": None, "order_index": 50},
        {"task_key": "order_1c", "task_name": "1С заказ поставщику", "parent_task": None, "order_index": 60},
        {"task_key": "warehouse_send", "task_name": "Отправка на склад (паркинг лист + авианакладная)", "parent_task": None, "order_index": 70},
        {"task_key": "gtd_vane", "task_name": "ГТД - Ване", "parent_task": None, "order_index": 80},
        {"task_key": "gtd_invoice", "task_name": "Счет за ГТД - Ирина Анатольевна", "parent_task": None, "order_index": 90},
        {"task_key": "commissioning", "task_name": "Ввод в эксплуатацию", "parent_task": None, "order_index": 100},
        {"task_key": "expenses", "task_name": "Расходы - Жанна", "parent_task": None, "order_index": 110},
        {"task_key": "jetro_sign", "task_name": "Jetro - подпись", "parent_task": None, "order_index": 120},
    ]
    
    for task_data in default_tasks:
        task = ShipmentTask(
            shipment_id=shipment.id,
            **task_data
        )
        db.add(task)
    
    await db.commit()
    await db.refresh(shipment)
    return shipment


@router.get("/", response_model=List[ShipmentResponse])
async def get_shipments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех поставок"""
    stmt = select(Shipment).order_by(Shipment.id.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить поставку с задачами"""
    stmt = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(stmt)
    shipment = result.scalar_one_or_none()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Поставка не найдена")
    
    return shipment


@router.put("/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: int,
    data: ShipmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить поставку"""
    stmt = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(stmt)
    shipment = result.scalar_one_or_none()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Поставка не найдена")
    
    for key, value in data.dict(exclude_unset=True).items():
        setattr(shipment, key, value)
    
    await db.commit()
    await db.refresh(shipment)
    return shipment


@router.delete("/{shipment_id}")
async def delete_shipment(
    shipment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удалить поставку"""
    stmt = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(stmt)
    shipment = result.scalar_one_or_none()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Поставка не найдена")
    
    await db.delete(shipment)
    await db.commit()
    return {"message": "Поставка удалена"}


# ========== ЗАДАЧИ ==========

@router.put("/tasks/{task_id}", response_model=ShipmentTaskResponse)
async def update_task(
    task_id: int,
    data: ShipmentTaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить задачу (отметить выполненной, добавить комментарий)"""
    stmt = select(ShipmentTask).where(ShipmentTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Обновляем поля
    if data.is_done is not None:
        task.is_done = data.is_done
    
    if data.comment is not None:
        task.comment = data.comment
    
    await db.commit()
    await db.refresh(task)
    
    # Пересчитываем прогресс поставки
    await _update_shipment_progress(task.shipment_id, db)
    
    return task


async def _update_shipment_progress(shipment_id: int, db: AsyncSession):
    """Пересчитать прогресс поставки"""
    stmt = select(ShipmentTask).where(ShipmentTask.shipment_id == shipment_id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    
    total = len(tasks)
    done = sum(1 for t in tasks if t.is_done)
    
    progress = int((done / total) * 100) if total > 0 else 0
    
    stmt = select(Shipment).where(Shipment.id == shipment_id)
    result = await db.execute(stmt)
    shipment = result.scalar_one_or_none()
    
    if shipment:
        shipment.progress = progress
        if progress == 100:
            shipment.status = "completed"
        elif shipment.status == "completed":
            shipment.status = "in_progress"
        await db.commit()

@router.get("/{shipment_id}/tasks")
async def get_shipment_tasks(
    shipment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить все задачи поставки"""
    stmt = select(ShipmentTask).where(ShipmentTask.shipment_id == shipment_id)
    result = await db.execute(stmt)
    return result.scalars().all()
