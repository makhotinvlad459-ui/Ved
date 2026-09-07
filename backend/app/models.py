# backend/app/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    name_eng = Column(String(100))
    prefix_ru = Column(String(255), nullable=False)
    prefix_eng = Column(String(255))
    
    collect_serials = Column(Boolean, default=True)
    serial_source = Column(String(50), default="serial_number")
    clean_serial_prefix = Column(Boolean, default=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    products = relationship("Product", back_populates="category")


class Color(Base):
    __tablename__ = "colors"
    
    id = Column(Integer, primary_key=True, index=True)
    eng = Column(String(50), unique=True, nullable=False)
    rus = Column(String(50), nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    products = relationship("Product", back_populates="color")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    model_number = Column(String(50), nullable=False)
    part_number = Column(String(50), nullable=False, index=True)
    description = Column(Text)
    model_name = Column(String(255))
    weight = Column(Float, nullable=True)
    honest_code = Column(String(100), nullable=True)
    
    category_id = Column(Integer, ForeignKey("categories.id"))
    color_id = Column(Integer, ForeignKey("colors.id"))
    
    coo = Column(String(100))
    upc = Column(String(50))
    
    override_prefix_ru = Column(String(255))
    override_serial_source = Column(String(50))
    override_collect_serials = Column(Boolean)
    override_clean_serial = Column(Boolean)
    
    custom_name_ru = Column(String(500))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    category = relationship("Category", back_populates="products")
    color = relationship("Color", back_populates="products")


class ProcessingSession(Base):
    __tablename__ = "processing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    status = Column(String(50), default="pending")
    
    invoice_file = Column(String(255))
    manifest_file = Column(String(255))
    template_file = Column(String(255))
    
    spec_number = Column(String(50))
    spec_date = Column(DateTime)
    
    invoice_date = Column(DateTime)
    result_file = Column(String(255))
    
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    errors = Column(Text, default="")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class PendingModel(Base):
    __tablename__ = "pending_models"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    
    part_number = Column(String(50), nullable=False)
    model_number = Column(String(50))
    description = Column(Text)
    coo = Column(String(100))
    
    suggested_category_id = Column(Integer, ForeignKey("categories.id"))
    suggested_color_id = Column(Integer, ForeignKey("colors.id"))
    suggested_name_ru = Column(String(500))
    
    status = Column(String(50), default="pending")
    
    custom_name_ru = Column(String(500))
    custom_category_id = Column(Integer, ForeignKey("categories.id"))
    custom_color_id = Column(Integer, ForeignKey("colors.id"))
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    suggested_category = relationship("Category", foreign_keys=[suggested_category_id])
    suggested_color = relationship("Color", foreign_keys=[suggested_color_id])
    custom_category = relationship("Category", foreign_keys=[custom_category_id])
    custom_color = relationship("Color", foreign_keys=[custom_color_id])


class PendingWeight(Base):
    __tablename__ = "pending_weights"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    
    part_number = Column(String(50), nullable=False)
    qty = Column(Integer, nullable=False)
    pallet_no = Column(String(50))
    box_no = Column(String(50))
    
    model_number = Column(String(50))
    description = Column(Text)
    category_name = Column(String(100))
    color_name = Column(String(50))
    
    suggested_weight = Column(Float)
    custom_weight = Column(Float)
    
    status = Column(String(50), default="pending")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    shipment_number = Column(String(50), unique=True, nullable=False)
    invoice_number = Column(String(50))
    invoice_date = Column(DateTime)
    supplier = Column(String(200))
    
    status = Column(String(50), default="in_progress")
    progress = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    tasks = relationship("ShipmentTask", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentTask(Base):
    __tablename__ = "shipment_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    
    task_key = Column(String(50), nullable=False)
    task_name = Column(String(200), nullable=False)
    parent_task = Column(String(50))
    
    is_done = Column(Boolean, default=False)
    comment = Column(Text)
    order_index = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    shipment = relationship("Shipment", back_populates="tasks")


class GtinProduct(Base):
    __tablename__ = "gtin_products"
    
    id = Column(Integer, primary_key=True, index=True)
    gtin = Column(String(14), unique=True, nullable=False, index=True)
    part_number = Column(String(50))
    model_number = Column(String(50))
    coo = Column(String(50))
    product_name = Column(String(200))
    category_name = Column(String(100))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class PendingGtin(Base):
    __tablename__ = "pending_gtins"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    gtin = Column(String(14), nullable=False, index=True)
    code_count = Column(Integer, default=0)
    suggested_name = Column(String(200))
    
    part_number = Column(String(50))
    model_number = Column(String(50))
    coo = Column(String(50))
    product_name = Column(String(200))
    category_name = Column(String(100))
    
    status = Column(String(50), default="pending")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())