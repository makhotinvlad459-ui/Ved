# backend/app/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# === Category ===
class CategoryBase(BaseModel):
    name: str
    name_eng: Optional[str] = None
    prefix_ru: str
    prefix_eng: Optional[str] = None
    collect_serials: bool = True
    serial_source: str = "serial_number"
    clean_serial_prefix: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    name_eng: Optional[str] = None
    prefix_ru: Optional[str] = None
    prefix_eng: Optional[str] = None
    collect_serials: Optional[bool] = None
    serial_source: Optional[str] = None
    clean_serial_prefix: Optional[bool] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# === Color ===
class ColorBase(BaseModel):
    eng: str
    rus: str


class ColorCreate(ColorBase):
    pass


class ColorUpdate(BaseModel):
    eng: Optional[str] = None
    rus: Optional[str] = None
    is_active: Optional[bool] = None


class ColorResponse(ColorBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# === Product ===
class ProductBase(BaseModel):
    model_number: str
    part_number: str
    description: Optional[str] = None
    model_name: Optional[str] = None
    category_id: Optional[int] = None
    color_id: Optional[int] = None
    coo: Optional[str] = None
    upc: Optional[str] = None
    override_prefix_ru: Optional[str] = None
    override_serial_source: Optional[str] = None
    override_collect_serials: Optional[bool] = None
    override_clean_serial: Optional[bool] = None
    weight: Optional[float] = None
    honest_code: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    model_number: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    model_name: Optional[str] = None
    category_id: Optional[int] = None
    color_id: Optional[int] = None
    coo: Optional[str] = None
    upc: Optional[str] = None
    override_prefix_ru: Optional[str] = None
    override_serial_source: Optional[str] = None
    override_collect_serials: Optional[bool] = None
    override_clean_serial: Optional[bool] = None
    is_active: Optional[bool] = None
    weight: Optional[float] = None
    honest_code: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[CategoryResponse] = None
    color: Optional[ColorResponse] = None
    
    class Config:
        from_attributes = True


# === Processing Session ===
class ProcessingSessionResponse(BaseModel):
    session_id: str
    status: str
    spec_number: Optional[str] = None
    spec_date: Optional[datetime] = None
    invoice_date: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    errors: Optional[str] = None
    result_file: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class PendingModelBase(BaseModel):
    part_number: str
    model_number: Optional[str] = None
    description: Optional[str] = None
    coo: Optional[str] = None
    suggested_category_id: Optional[int] = None
    suggested_color_id: Optional[int] = None
    suggested_name_ru: Optional[str] = None


class PendingModelResponse(PendingModelBase):
    id: int
    session_id: str
    status: str
    custom_name_ru: Optional[str] = None
    custom_category_id: Optional[int] = None
    custom_color_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PendingModelApprove(BaseModel):
    custom_name_ru: Optional[str] = None
    custom_category_id: Optional[int] = None
    custom_color_id: Optional[int] = None        

class PendingWeightBase(BaseModel):
    part_number: str
    qty: int
    pallet_no: Optional[str] = None
    box_no: Optional[str] = None
    model_number: Optional[str] = None
    description: Optional[str] = None
    category_name: Optional[str] = None
    color_name: Optional[str] = None
    suggested_weight: Optional[float] = None


class PendingWeightResponse(PendingWeightBase):
    id: int
    session_id: str
    status: str
    custom_weight: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PendingWeightApprove(BaseModel):
    custom_weight: float    