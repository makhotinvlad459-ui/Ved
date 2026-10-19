# backend/app/services/model_detector.py
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models import Category, Color, Product, PendingModel


# ============================================================
# ОПРЕДЕЛЕНИЕ КАТЕГОРИИ
# ============================================================

def detect_category(description: str, categories: List[Category]) -> Optional[Category]:
    """
    Определяет категорию по описанию товара.

    ВАЖНО: правила привязаны к РЕАЛЬНЫМ именам категорий в БД:
      - «Ноутбуки APPLE», «Телефоны APPLE», «Планшеты APLLE», «Часы APPLE»,
        «Наушники APPLE», «Наушники Beats», «Телефоны Samsung»,
        «Ноутбуки Lenovo», «Пылесосы Dyson», и т.д.

    Если ничего не нашли — возвращает None (автосоздание отключено).
    """
    if not description or not categories:
        return None

    d = description.lower()

    # Словарь: имя категории в БД → список ключевых слов.
    # Порядок важен: более специфичные правила ВЫШЕ общих.
    rules: List[tuple] = [
        # === Apple: ноутбуки ===
        ("Ноутбуки APPLE", ["macbook"]),

        # === Apple: телефоны ===
        ("Телефоны APPLE", ["iphone"]),

        # === Apple: планшеты (ловим оба варианта — с опечаткой и без) ===
        ("Планшеты APLLE", ["ipad"]),
        ("Планшеты APPLE", ["ipad"]),

        # === Apple: часы ===
        ("Часы APPLE", [
            "apple watch", "watch series", "watch se",
            "watch ultra", "watch  series",
        ]),

        # === Apple: наушники ===
        ("Наушники APPLE", ["airpods"]),

        # === Apple: приставки / мониторы / мини / десктопы ===
        ("Приставки APPLE TV", ["apple tv"]),
        ("Мониторы APPLE", ["studio display", "pro display xdr"]),
        ("Макмини", ["mac mini"]),
        ("Персональные компьютеры APPLE", ["imac", "mac studio", "mac pro"]),

        # === Apple: аксессуары ===
        ("Клавиатуры APPLE", ["magic keyboard"]),
        ("Стилусы APPLE", ["apple pencil"]),
        ("Адаптеры APPLE", [
            "power adapter", "magsafe", "usb-c power",
            "usb-c power adapter", "85w", "96w", "70w", "140w",
        ]),
        ("Зарядное APPLE", ["charger", "power supply"]),
        ("Чехлы для телефонов APPLE", [
            "silicone case", "clear case", "case with magsafe",
            "case for iphone", "techwoven case",
        ]),
        ("Чехол-книжка APPLE", ["smart folio", "folio"]),
        ("Ремешки для часов APPLE", [
            "band for apple watch", "milanese loop", "link bracelet",
            "sport band", "sport loop", "solo loop", "braided solo loop",
        ]),
        ("Ремешки Crossbody APPLE", ["crossbody strap"]),
        ("Ремешки для руки", ["crossbody"]),
        ("Брелки APPLE", ["airtag", "key ring"]),
        ("Кошельки APPLE", ["magsafe wallet", "wallet with magsafe"]),
        ("Кошелек", ["wallet", "card holder"]),
        ("Полировочная ткань APPLE", ["polishing cloth"]),

        # === Samsung ===
        ("Телефоны Samsung", [
            "samsung galaxy", "galaxy s", "galaxy a", "galaxy z",
            "sm-s", "sm-g", "sm-a", "sm-f", "sm-n",
        ]),

        # === Beats ===
        ("Наушники Beats", [
            "beats powerbeats", "powerbeats", "beats studio",
            "beats fit", "beats solo", "beats ",
        ]),
        ("Чехол(торговой марки Beats)", ["beats case"]),

        # === Lenovo ===
        ("Ноутбуки Lenovo", [
            "lenovo", "thinkpad", "thinkbook", "legion",
            "ideapad", "yoga", "loq",
        ]),

        # === Dyson ===
        ("Пылесосы Dyson", [
            "dyson vacuum", "v8 ", "v10 ", "v11 ", "v12 ", "v15 ",
            "dyson v", "dyson digital slim",
        ]),
        ("Фены Dyson", ["dyson supersonic", "supersonic"]),
        ("Мультистайлеры Dyson", ["dyson airwrap", "airwrap"]),
        ("Выпрямители для волос Dyson", ["dyson corrale", "corrale"]),

        # === Прочее (общие правила — НИЖЕ специфичных) ===
        ("Мониторы", ["monitor", "display"]),
        ("Клавиатура", ["keyboard"]),
        ("Кабель", ["cable", "usb-c to", "lightning to", "thunderbolt"]),
        ("Экшн-камера", ["action cam", "osmo", "insta360", "gopro"]),
        ("Фитнес-браслеты Google", ["fitbit", "fitness tracker"]),
        ("Очки", ["glasses", "sunglasses"]),
    ]

    # Индекс: имя категории → объект Category
    cat_by_name = {c.name: c for c in categories}

    for cat_name, keywords in rules:
        cat = cat_by_name.get(cat_name)
        if not cat:
            continue  # такой категории нет в БД — пропускаем
        for kw in keywords:
            if kw in d:
                return cat

    # Ничего не нашли — None (пользователь выберет вручную)
    return None


# ============================================================
# ОПРЕДЕЛЕНИЕ ЦВЕТА
# ============================================================

def detect_color(description: str, colors: List[Color]) -> Optional[Color]:
    if not description or not colors:
        return None
    d = description.lower()
    matches = [c for c in colors if c.eng and c.eng.lower() in d]
    if not matches:
        return None
    return max(matches, key=lambda c: len(c.eng or ""))


# ============================================================
# АВТОСОЗДАНИЕ ЦВЕТА (оставлено — цветов мало, мусор минимален)
# ============================================================

def detect_or_create_color(
    description: str,
    colors: List[Color],
    db: Session
) -> Optional[Color]:
    color = detect_color(description, colors)
    if color:
        return color

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
        (r'\b(indigo)\b', 'Indigo', 'Индиго'),
        (r'\b(navy)\b', 'Navy', 'Тёмно-синий'),
        (r'\b(olive)\b', 'Olive', 'Оливковый'),
        (r'\b(taupe)\b', 'Taupe', 'Серо-коричневый'),
    ]

    description_lower = description.lower()
    for pattern, eng, rus in color_patterns:
        if re.search(pattern, description_lower):
            existing = db.query(Color).filter(Color.eng == eng).first()
            if existing:
                return existing

            new_color = Color(eng=eng, rus=rus)
            db.add(new_color)
            db.commit()
            db.refresh(new_color)
            print(f"✅ Создан новый цвет: {eng} ({rus})")
            return new_color

    return None


# ============================================================
# ГЕНЕРАЦИЯ РУССКОГО НАЗВАНИЯ
# ============================================================

def generate_russian_name(
    description: str,
    category: Optional[Category],
    color: Optional[Color]
) -> str:
    if not description:
        return ""

    name = description
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()

    brands = [
        "Apple", "Samsung", "Xiaomi", "Huawei", "Lenovo",
        "HP", "Dell", "Asus", "Acer", "Google", "DJI", "Insta360",
        "Beats", "Dyson",
    ]
    for brand in brands:
        if name.startswith(brand):
            name = name[len(brand):].strip()
            break

    if color and color.rus:
        if color.eng.lower() in name.lower():
            pattern = re.compile(re.escape(color.eng), re.IGNORECASE)
            name = pattern.sub(f'"{color.rus}"', name)
        else:
            name = f'{name} "{color.rus}"'

    return name.strip()


# ============================================================
# СОХРАНЕНИЕ PENDING-МОДЕЛЕЙ
# ============================================================

def save_pending_models(
    items: List[Dict[str, Any]],
    categories: List[Category],
    colors: List[Color],
    db: Session,
    session_id: str
) -> List[Dict[str, Any]]:
    """
    Сохранить новые модели в список на подтверждение.
    Также создаёт PendingModel для существующих Product БЕЗ категории.

    Автоматическое создание КАТЕГОРИЙ отключено.
    Автоматическое создание ЦВЕТОВ оставлено (безопасно — цветов мало).
    """
    new_models = []

    existing_part_numbers = {
        p[0] for p in db.query(Product.part_number).all()
    }

    pending_part_numbers = {
        p.part_number for p in db.query(PendingModel).filter(
            PendingModel.session_id == session_id,
            PendingModel.status == "pending"
        ).all()
    }

    for item in items:
        part_number = item.get("part_number", "")

        if not part_number:
            continue

        # === Случай 1: товар уже в PendingModel ===
        if part_number in pending_part_numbers:
            continue

        # === Случай 2: товар в БД, но без категории ===
        if part_number in existing_part_numbers:
            product = db.query(Product).filter(
                Product.part_number == part_number
            ).first()

            if product and not product.category_id:
                pending = PendingModel(
                    session_id=session_id,
                    part_number=part_number,
                    model_number=product.model_number,
                    description=product.description or item.get("description", ""),
                    coo=product.coo or item.get("coo", ""),
                    suggested_category_id=None,
                    suggested_color_id=product.color_id,
                    suggested_name_ru=product.custom_name_ru,
                    status="pending",
                )
                db.add(pending)
                db.commit()
                pending_part_numbers.add(part_number)

                new_models.append({
                    "part_number": part_number,
                    "type": "missing_category",
                    "suggested_name": product.custom_name_ru,
                    "category_id": None,
                    "color_id": product.color_id,
                })
                print(f"📝 Товар без категории на подтверждение: {part_number}")

            continue

        # === Случай 3: новый товар (нет в БД) ===
        description = item.get("description", "")

        category = detect_category(description, categories)
        color = detect_color(description, colors)

        suggested_name = generate_russian_name(description, category, color)

        # Автоматическое создание категорий ОТКЛЮЧЕНО.
        # Если detect_category не нашёл — suggested_category_id = None,
        # пользователь выберет/создаст вручную в PendingModelsScreen.

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
        pending_part_numbers.add(part_number)

        new_models.append({
            "part_number": part_number,
            "type": "new_model",
            "suggested_name": suggested_name,
            "category_id": category.id if category else None,
            "color_id": color.id if color else None
        })

        print(f"📝 Добавлена на подтверждение: {part_number} (category={category.name if category else 'None'})")

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

        existing_product = db.query(Product).filter(
            Product.part_number == p.part_number
        ).first()

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
            "status": p.status,
            "type": "missing_category" if existing_product else "new_model",
        })

    return result