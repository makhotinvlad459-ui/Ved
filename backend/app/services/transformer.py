import re
from typing import Optional
from app.models import Product, Category, Color


def extract_color_from_description(description: str, color_mapping: dict) -> Optional[str]:
    """
    Извлекает цвет из описания
    """
    for eng_color in color_mapping.keys():
        if eng_color in description:
            return eng_color
    return None


def extract_article_from_description(description: str) -> Optional[str]:
    """
    Извлекает артикул из описания (в скобках в конце)
    Apple MacBook Pro 16\" Space Black (...) (MGEA4LL/A) → MGEA4LL/A
    """
    match = re.search(r'\(([^)]+)\)$', description)
    if match:
        return match.group(1)
    return None


def transform_product_name(
    description: str,
    category: Optional[Category] = None,
    color: Optional[Color] = None,
    color_mapping: dict = None
) -> str:
    """
    Трансформация названия для спецификации
    
    Пример:
    Вход: Apple MacBook Pro 16\" Space Black (...) (MGEA4LL/A)
    Выход: Портативный персональный компьютер торговой марки 
           Apple MacBook Pro 16\" Черный (...) (MGEA4LL/A) / 
           Apple MacBook Pro 16\" Space Black (...) (MGEA4LL/A)
    """
    if not description:
        return ""
    
    if not color_mapping:
        color_mapping = {}
    
    # Извлекаем артикул из описания
    article = extract_article_from_description(description)
    
    # Находим цвет в описании
    color_eng = extract_color_from_description(description, color_mapping)
    color_rus = color_mapping.get(color_eng, color_eng) if color_eng else None
    
    # Создаем описание с русским цветом
    russian_description = description
    if color_eng and color_rus:
        russian_description = description.replace(color_eng, f'\"{color_rus}\"')
    
    # Добавляем префикс категории (с проверкой на None)
    prefix = ""
    if category and category.prefix_ru:
        prefix = category.prefix_ru
    
    # Формируем результат: русская часть / оригинал
    if article:
        russian_part = f"{prefix} {russian_description}"
    else:
        russian_part = f"{prefix} {russian_description}"
    
    result = f"{russian_part} / {description}"
    
    return result


def clean_serial(serial: str, category: Optional[Category] = None, product: Optional[Product] = None) -> str:
    """
    Очистка серийного номера (удаление первой буквы 'S')
    """
    if not serial:
        return ""
    
    clean_prefix = True
    if product and product.override_clean_serial is not None:
        clean_prefix = product.override_clean_serial
    elif category and category.clean_serial_prefix is not None:
        clean_prefix = category.clean_serial_prefix
    
    if clean_prefix and serial.startswith('S'):
        return serial[1:]
    
    return serial