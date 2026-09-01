# backend/app/services/matcher.py
from sqlalchemy.orm import Session
from app.models import Product, Category, Color


def find_or_create_product(
    db: Session,
    part_number: str,
    model_number: str,
    description: str,
    coo: str
):
    """Поиск или создание модели товара"""
    product = db.query(Product).filter(Product.part_number == part_number).first()
    
    if product:
        return product
    
    # Если не найдена, возвращаем None — пользователь создаст вручную
    return None
