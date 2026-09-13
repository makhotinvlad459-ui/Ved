import re
from typing import Optional
from app.models import Product, Category, Color

# Список брендов для дедупликации
BRANDS = [
    'Apple', 'Samsung', 'Xiaomi', 'Huawei', 'Lenovo',
    'HP', 'Dell', 'Asus', 'Acer', 'Google',
    'DJI', 'Insta360', 'Sony', 'Microsoft',
]


def extract_color_from_description(description: str, color_mapping: dict) -> Optional[str]:
    """Извлекает цвет из описания"""
    for eng_color in color_mapping.keys():
        if eng_color in description:
            return eng_color
    return None


def extract_article_from_description(description: str) -> Optional[str]:
    """Извлекает артикул из описания (в скобках в конце)"""
    match = re.search(r'\(([^)]+)\)$', description)
    if match:
        return match.group(1)
    return None


def _dedupe_brand(prefix: str, text: str) -> str:
    """
    Убирает дублирование бренда в начале text,
    если он уже есть в конце prefix.
    
    Пример:
        prefix = "Персональный компьютер торговой марки Apple"
        text   = "Apple iMac 24\" Silver..."
        →       "iMac 24\" Silver..."
    """
    if not prefix or not text:
        return text
    p_low = prefix.lower().rstrip()
    for brand in BRANDS:
        b_low = brand.lower()
        if p_low.endswith(b_low):
            # Совпадение начала text с брендом (с учётом пробелов/кавычек)
            t_low = text.lstrip()
            if t_low.lower().startswith(b_low + ' ') or t_low.lower() == b_low:
                cut = len(brand)
                # Учитываем начальные пробелы в text
                leading = len(text) - len(text.lstrip())
                return text[:leading] + text[leading + cut:].lstrip()
    return text


def transform_product_name(
    description: str,
    category: Optional[Category] = None,
    color: Optional[Color] = None,
    color_mapping: dict = None
) -> str:
    """
    Трансформация названия для спецификации.
    
    Пример:
    Вход:  Apple MacBook Pro 16" Space Black (...) (MGEA4LL/A)
    Выход: Портативный персональный компьютер торговой марки 
           Apple MacBook Pro 16" "Черный" (...) (MGEA4LL/A) / 
           Apple MacBook Pro 16" Space Black (...) (MGEA4LL/A)
    """
    if not description:
        return ""

    if not color_mapping:
        color_mapping = {}

    # Находим цвет в описании
    color_eng = extract_color_from_description(description, color_mapping)
    color_rus = color_mapping.get(color_eng, color_eng) if color_eng else None

    # Создаём описание с русским цветом
    russian_description = description
    if color_eng and color_rus:
        russian_description = description.replace(color_eng, f'"{color_rus}"')

    # Префикс категории
    prefix = ""
    if category and category.prefix_ru:
        prefix = category.prefix_ru.strip()

    # ⚠️ Защита от двойного бренда
    russian_description = _dedupe_brand(prefix, russian_description)

    russian_part = f"{prefix} {russian_description}".strip()
    result = f"{russian_part} / {description}"

    return result


def clean_serial(serial: str, category: Optional[Category] = None, product: Optional[Product] = None) -> str:
    """Очистка серийного номера (удаление первой буквы 'S')"""
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