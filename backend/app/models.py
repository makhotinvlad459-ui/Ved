# backend/app/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
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