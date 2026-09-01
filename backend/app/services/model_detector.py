# backend/app/services/model_detector.py
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models import Category, Color, Product, PendingModel


def detect_category(description: str, categories: List[Category]) -> Optional[Category]:
    if not description or not categories:
        return None
    
    description_lower = description.lower()
    
    rules = {
        "Телефон": ["iphone", "galaxy", "pixel", "phone", "mobile"],
        "Компьютер": ["macbook", "mac mini", "laptop", "notebook", "imac", "mac pro"],
        "Планшет": ["ipad", "galaxy tab", "tablet"],
        "Часы": ["watch", "galaxy watch", "apple watch"],
        "Зарядное": ["adapter", "charger", "power adapter", "power supply"],
        "Чехол": ["case", "folio", "cover", "silicon", "techwoven"],
        "Чехол-книжка": ["smart folio", "book cover"],
        "Наушники": ["airpods", "headphones", "earbuds", "earphones"],
        "Кабель": ["cable", "wire", "usb-c", "lightning"],
        "Экшн-камера": ["action cam", "osmo", "insta360", "gopro"],
        "Фитнес-браслет": ["fitbit", "fitness", "tracker", "band"],
        "Кошелек": ["wallet", "card holder"],
        "Ремешок": ["strap", "band", "bracelet"],
        "Клавиатура": ["keyboard", "magic keyboard"],
    }
    
    for category_name, keywords in rules.items():
        for keyword in keywords:
            if keyword in description_lower:
                for cat in categories:
                    if cat.name == category_name:
                        return cat
    
    # Дефолтная категория, если ничего не найдено
    for cat in categories:
        if cat.name == "Компьютер":
            return cat
    
    return None


def detect_color(description: str, colors: List[Color]) -> Optional[Color]:
    if not description or not colors:
        return None
    
    for color in colors:
        if color.eng.lower() in description.lower():
            return color
    
    return None


def detect_or_create_category(
    description: str,
    categories: List[Category],
    db: Session
) -> Optional[Category]:
    """Определить категорию или создать новую (временную)"""
    
    # Сначала пытаемся найти по правилам
    category = detect_category(description, categories)
    
    if category:
        return category
    
    # Если категория не найдена, создаем временную
    # Извлекаем название из описания
    name_eng = extract_category_name(description)
    
    # Проверяем, может уже есть такая категория (похожая)
    existing = db.query(Category).filter(Category.name == name_eng).first()
    if existing:
        return existing
    
    # Создаем новую категорию с пустым префиксом
    new_category = Category(
        name=name_eng,
        name_eng=name_eng,
        prefix_ru="",  # Пользователь заполнит позже
        prefix_eng="",  # Не используется
        collect_serials=True,
        serial_source="serial_number",
        clean_serial_prefix=True
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    print(f"✅ Создана новая категория: {name_eng}")
    return new_category


def detect_or_create_color(
    description: str,
    colors: List[Color],
    db: Session
) -> Optional[Color]:
    """Определить цвет или создать новый (временный)"""
    
    # Сначала пытаемся найти по правилам
    color = detect_color(description, colors)
    
    if color:
        return color
    
    # Если цвет не найден, ищем в описании популярные цвета
    color_patterns = [
        (r'\b(space black|black)\b', 'Black', 'Черный'),
        (r'\b(silver)\b', 'Silver', 'Серебристый'),
        (r'\b(midnight)\b', 'Midnight', 'Темная ночь'),
        (r'\b(starlight)\b', 'Starlight', 'Сияющая звезда'),
        (r'\b(blue)\b', 'Blue', 'Голубой'),
        (r'\b(pink)\b', 'Pink', 'Розовый'),
        (r'\b(yellow)\b', 'Yellow', 'Желтый'),
        (r'\b(white)\b', 'White', 'Белый'),
        (r'\b(red)\b', 'Red', 'Красный'),
        (r'\b(orange)\b', 'Orange', 'Оранжевый'),
        (r'\b(purple)\b', 'Purple', 'Фиолетовый'),
        (r'\b(green)\b', 'Green', 'Зеленый'),
        (r'\b(gray|grey)\b', 'Gray', 'Серый'),
        (r'\b(gold)\b', 'Gold', 'Золотой'),
        (r'\b(rose gold)\b', 'Rose Gold', 'Розовое золото'),
    ]
    
    description_lower = description.lower()
    for pattern, eng, rus in color_patterns:
        if re.search(pattern, description_lower):
            # Проверяем, есть ли такой цвет в БД
            existing = db.query(Color).filter(Color.eng == eng).first()
            if existing:
                return existing
            
            # Если нет, создаем новый
            new_color = Color(eng=eng, rus=rus)
            db.add(new_color)
            db.commit()
            db.refresh(new_color)
            print(f"✅ Создан новый цвет: {eng} ({rus})")
            return new_color
    
    # Если ничего не нашли, возвращаем None (цвет не определен)
    return None


def extract_category_name(description: str) -> str:
    """Извлекает название категории из описания"""
    # Берем первые 2-3 слова
    words = description.split()
    if len(words) >= 3:
        return " ".join(words[:3])
    elif len(words) >= 2:
        return " ".join(words[:2])
    return words[0] if words else "Новая категория"


def generate_russian_name(
    description: str,
    category: Optional[Category],
    color: Optional[Color]
) -> str:
    if not description:
        return ""
    
    name = description
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()
    
    brands = ["Apple", "Samsung", "Xiaomi", "Huawei", "Lenovo", "HP", "Dell", "Asus", "Acer", "Google", "DJI", "Insta360"]
    for brand in brands:
        if name.startswith(brand):
            name = name[len(brand):].strip()
            break
    
    if color and color.rus:
        if color.eng.lower() in name.lower():
            # Заменяем английское название на русское в кавычках
            pattern = re.compile(re.escape(color.eng), re.IGNORECASE)
            name = pattern.sub(f'"{color.rus}"', name)
        else:
            name = f'{name} "{color.rus}"'
    
    return name.strip()


def save_pending_models(
    items: List[Dict[str, Any]],
    categories: List[Category],
    colors: List[Color],
    db: Session,
    session_id: str
) -> List[Dict[str, Any]]:
    """Сохранить новые модели в список на подтверждение"""
    new_models = []
    
    existing_part_numbers = {
        p[0] for p in db.query(Product.part_number).all()
    }
    
    # Проверяем уже ожидающие подтверждения
    pending_part_numbers = {
        p.part_number for p in db.query(PendingModel).filter(
            PendingModel.status == "pending"
        ).all()
    }
    
    for item in items:
        part_number = item.get("part_number", "")
        
        # Пропускаем если уже есть или уже на подтверждении
        if not part_number or part_number in existing_part_numbers or part_number in pending_part_numbers:
            continue
        
        description = item.get("description", "")
        
        category = detect_category(description, categories)
        color = detect_color(description, colors)
        
        suggested_name = generate_russian_name(description, category, color)
        
        # Если категория не найдена, создаем временную
        if not category:
            category = detect_or_create_category(description, categories, db)
            # Обновляем список категорий
            categories = db.query(Category).all()
        
        # Если цвет не найден, пытаемся создать
        if not color:
            color = detect_or_create_color(description, colors, db)
            if color:
                colors = db.query(Color).all()
        
        pending = PendingModel(
            session_id=session_id,
            part_number=part_number,
            model_number=item.get("model_number", ""),
            description=description,
            coo=item.get("coo", ""),
            suggested_category_id=category.id if category else None,
            suggested_color_id=color.id if color else None,
            suggested_name_ru=suggested_name,
            status="pending"
        )
        db.add(pending)
        db.commit()
        
        new_models.append({
            "part_number": part_number,
            "suggested_name": suggested_name,
            "category_id": category.id if category else None,
            "color_id": color.id if color else None
        })
        
        print(f"📝 Добавлена на подтверждение: {part_number}")
    
    return new_models


def get_pending_models_by_session(db: Session, session_id: str) -> List[Dict[str, Any]]:
    pendings = db.query(PendingModel).filter(
        PendingModel.session_id == session_id,
        PendingModel.status == "pending"
    ).all()
    
    result = []
    for p in pendings:
        category_name = None
        if p.suggested_category_id:
            cat = db.query(Category).filter(Category.id == p.suggested_category_id).first()
            category_name = cat.name if cat else None
        
        color_name = None
        if p.suggested_color_id:
            col = db.query(Color).filter(Color.id == p.suggested_color_id).first()
            color_name = col.eng if col else None
        
        result.append({
            "id": p.id,
            "part_number": p.part_number,
            "model_number": p.model_number,
            "description": p.description,
            "coo": p.coo,
            "suggested_category_id": p.suggested_category_id,
            "suggested_category_name": category_name,
            "suggested_color_id": p.suggested_color_id,
            "suggested_color_name": color_name,
            "suggested_name_ru": p.suggested_name_ru,
            "custom_name_ru": p.custom_name_ru,
            "status": p.status
        })
    
    return result