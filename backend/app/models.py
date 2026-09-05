# backend/app/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Category(Base):
    """Категории товаров"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # "Компьютер"
    name_eng = Column(String(100))  # "Computer"
    prefix_ru = Column(String(255), nullable=False)  # "Портативный персональный компьютер торговой марки"
    prefix_eng = Column(String(255))  # "Portable personal computer brand"
    
    collect_serials = Column(Boolean, default=True)  # Собирать серийные номера
    serial_source = Column(String(50), default="serial_number")  # serial_number / imei_1 / imei_2
    clean_serial_prefix = Column(Boolean, default=True)  # Удалять "S" из серийников
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Связи
    products = relationship("Product", back_populates="category")


class Color(Base):
    """Цвета и их перевод"""
    __tablename__ = "colors"
    
    id = Column(Integer, primary_key=True, index=True)
    eng = Column(String(50), unique=True, nullable=False)  # "Space Black"
    rus = Column(String(50), nullable=False)  # "Черный"
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Связи
    products = relationship("Product", back_populates="color")


class Product(Base):
    """Модели товаров"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    model_number = Column(String(50), nullable=False)  # "A3428"
    part_number = Column(String(50), nullable=False, index=True)  # "MGEA4LL/A"
    description = Column(Text)  # Полное описание из инвойса
    model_name = Column(String(255))  # "MacBook Pro 16"
    weight = Column(Float, nullable=True)  
    honest_code = Column(String(100), nullable=True)
    
    # Связи с категорией и цветом
    category_id = Column(Integer, ForeignKey("categories.id"))
    color_id = Column(Integer, ForeignKey("colors.id"))
    
    coo = Column(String(100))  # Страна происхождения
    upc = Column(String(50))  # UPC код
    
    # Переопределения правил (если нужно)
    override_prefix_ru = Column(String(255))
    override_serial_source = Column(String(50))
    override_collect_serials = Column(Boolean)
    override_clean_serial = Column(Boolean)
    
    # Ручное название на русском (для новых моделей)
    custom_name_ru = Column(String(500))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Связи
    category = relationship("Category", back_populates="products")
    color = relationship("Color", back_populates="products")


class ProcessingSession(Base):
    """Сессии обработки файлов"""
    __tablename__ = "processing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    status = Column(String(50), default="pending")  # pending/processing/completed/error
    
    invoice_file = Column(String(255))  # Путь к файлу инвойса
    manifest_file = Column(String(255))  # Путь к файлу манифеста
    template_file = Column(String(255))  # Путь к шаблону
    
    spec_number = Column(String(50))  # Номер спецификации (вручную)
    spec_date = Column(DateTime)  # Дата спецификации
    
    invoice_date = Column(DateTime)  # Дата инвойса
    result_file = Column(String(255))  # Путь к результату
    
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    errors = Column(Text, default="")  # JSON с ошибками
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class PendingModel(Base):
    """Новые модели, ожидающие подтверждения пользователя"""
    __tablename__ = "pending_models"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    
    # Данные из инвойса
    part_number = Column(String(50), nullable=False)
    model_number = Column(String(50))
    description = Column(Text)
    coo = Column(String(100))
    
    # Предложенные значения
    suggested_category_id = Column(Integer, ForeignKey("categories.id"))
    suggested_color_id = Column(Integer, ForeignKey("colors.id"))
    suggested_name_ru = Column(String(500))
    
    # Статус: pending/approved/skipped
    status = Column(String(50), default="pending")
    
    # Пользовательские правки
    custom_name_ru = Column(String(500))
    custom_category_id = Column(Integer, ForeignKey("categories.id"))
    custom_color_id = Column(Integer, ForeignKey("colors.id"))
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Связи
    suggested_category = relationship("Category", foreign_keys=[suggested_category_id])
    suggested_color = relationship("Color", foreign_keys=[suggested_color_id])
    custom_category = relationship("Category", foreign_keys=[custom_category_id])
    custom_color = relationship("Color", foreign_keys=[custom_color_id])

class PendingWeight(Base):
    """Модели, ожидающие подтверждения веса для Packing List"""
    __tablename__ = "pending_weights"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    
    # Данные из файла
    part_number = Column(String(50), nullable=False)
    qty = Column(Integer, nullable=False)
    pallet_no = Column(String(50))
    box_no = Column(String(50))
    
    # Информация из БД (если модель найдена)
    model_number = Column(String(50))
    description = Column(Text)
    category_name = Column(String(100))
    color_name = Column(String(50))
    
    # Вес
    suggested_weight = Column(Float)  # Из файла (если есть)
    custom_weight = Column(Float)  # Введённый пользователем
    
    # Статус: pending/approved/skipped
    status = Column(String(50), default="pending")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())  

# ============================================================
# ПОСТАВКИ (SHIPMENTS)
# ============================================================

class Shipment(Base):
    """Поставка — контейнер для всех задач по одной поставке"""
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    shipment_number = Column(String(50), unique=True, nullable=False)  # "Поставка №1"
    invoice_number = Column(String(50))  # "K466"
    invoice_date = Column(DateTime)
    supplier = Column(String(200))  # "KVN Group FZCO"
    
    status = Column(String(50), default="in_progress")  # in_progress / completed / cancelled
    progress = Column(Integer, default=0)  # 0-100
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Связь с задачами
    tasks = relationship("ShipmentTask", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentTask(Base):
    """Задача внутри поставки"""
    __tablename__ = "shipment_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    
    task_key = Column(String(50), nullable=False)  # invoice, declaration_create, etc.
    task_name = Column(String(200), nullable=False)  # "Инвойс", "Создание отправка брокеру"
    parent_task = Column(String(50))  # Для группировки: declaration, cz, etc.
    
    is_done = Column(Boolean, default=False)
    comment = Column(Text)
    order_index = Column(Integer, default=0)  # Порядок отображения
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Связь с поставкой
    shipment = relationship("Shipment", back_populates="tasks")      