# backend/app/init_db.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import AsyncSessionLocal, engine
from .models import Category, Color, Product, Base
import asyncio


async def init_db():
    """Полная инициализация базы данных: создание таблиц + начальные данные"""
    
    # 1. Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы созданы!")
    
    async with AsyncSessionLocal() as session:
        print("=" * 60)
        print("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
        print("=" * 60)
        
        # === Категории ===
        print("\n📦 Категории:")
        categories_data = [
            # Существующие категории
            {
                "name": "Компьютер",
                "name_eng": "Computer",
                "prefix_ru": "Портативный персональный компьютер торговой марки",
                "prefix_eng": "Portable personal computer brand",
                "collect_serials": True,
                "serial_source": "serial_number",
                "clean_serial_prefix": True
            },
            {
                "name": "Телефон",
                "name_eng": "Phone",
                "prefix_ru": "Телефонный мобильный аппарат торговой марки",
                "prefix_eng": "Mobile phone brand",
                "collect_serials": True,
                "serial_source": "imei_1",
                "clean_serial_prefix": False
            },
            {
                "name": "Планшет",
                "name_eng": "Tablet",
                "prefix_ru": "Планшетный компьютер торговой марки",
                "prefix_eng": "Tablet computer brand",
                "collect_serials": True,
                "serial_source": "serial_number",
                "clean_serial_prefix": True
            },
            {
                "name": "Часы",
                "name_eng": "Watch",
                "prefix_ru": "Персональные электронные смарт-часы торговой марки",
                "prefix_eng": "Personal electronic smart watch brand",
                "collect_serials": True,
                "serial_source": "serial_number",
                "clean_serial_prefix": True
            },
            {
                "name": "Зарядное",
                "name_eng": "Charger",
                "prefix_ru": "Устройство зарядное сетевое для мобильных устройств торговой марки",
                "prefix_eng": "Network charging device for mobile devices brand",
                "collect_serials": True,
                "serial_source": "serial_number",
                "clean_serial_prefix": True
            },
            # НОВЫЕ КАТЕГОРИИ
            {
                "name": "Чехол",
                "name_eng": "Case",
                "prefix_ru": "Чехол торговой марки",
                "prefix_eng": "Case brand",
                "collect_serials": False,
                "serial_source": None,
                "clean_serial_prefix": False
            },
            {
                "name": "Чехол-книжка",
                "name_eng": "Folio Case",
                "prefix_ru": "Чехол-книжка торговой марки",
                "prefix_eng": "Folio case brand",
                "collect_serials": False,
                "serial_source": None,
                "clean_serial_prefix": False
            },
            {
                "name": "Клавиатура",
                "name_eng": "Keyboard",
                "prefix_ru": "Беспроводная клавиатура торговой марки",
                "prefix_eng": "Wireless keyboard brand",
                "collect_serials": False,
                "serial_source": None,
                "clean_serial_prefix": False
            },
            {
                "name": "Наушники",
                "name_eng": "Headphones",
                "prefix_ru": "Персональные наушники торговой марки",
                "prefix_eng": "Personal headphones brand",
                "collect_serials": True,
                "serial_source": "serial_number",
                "clean_serial_prefix": True
            },
            {
                "name": "Кабель",
                "name_eng": "Cable",
                "prefix_ru": "Кабель торговой марки",
                "prefix_eng": "Cable brand",
                "collect_serials": False,
                "serial_source": None,
                "clean_serial_prefix": False
            },
            {
                "name": "Экшн-камера",
                "name_eng": "Action Camera",
                "prefix_ru": "Цифровая видеокамера (экшн-камера) торговой марки",
                "prefix_eng": "Digital video camera (action camera) brand",
                "collect_serials": True,
                "serial_source": "serial_number",
                "clean_serial_prefix": True
            },
            {
                "name": "Фитнес-браслет",
                "name_eng": "Fitness Tracker",
                "prefix_ru": "Фитнес-браслет торговой марки",
                "prefix_eng": "Fitness tracker brand",
                "collect_serials": False,
                "serial_source": None,
                "clean_serial_prefix": False
            },
            {
                "name": "Кошелек",
                "name_eng": "Wallet",
                "prefix_ru": "Кошелек торговой марки",
                "prefix_eng": "Wallet brand",
                "collect_serials": False,
                "serial_source": None,
                "clean_serial_prefix": False
            },
            {
                "name": "Ремешок",
                "name_eng": "Strap",
                "prefix_ru": "Кроссбоди-ремешок торговой марки",
                "prefix_eng": "Crossbody strap brand",
                "collect_serials": False,
                "serial_source": None,
                "clean_serial_prefix": False
            },
        ]
        
        for cat_data in categories_data:
            stmt = select(Category).where(Category.name == cat_data["name"])
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                category = Category(**cat_data)
                session.add(category)
                print(f"  ✅ {cat_data['name']}")
        
        # === Цвета ===
        print("\n🎨 Цвета:")
        colors_data = [
            {"eng": "Space Black", "rus": "Черный"},
            {"eng": "Silver", "rus": "Серебристый"},
            {"eng": "Space Grey", "rus": "Серый космос"},
            {"eng": "Midnight", "rus": "Темная ночь"},
            {"eng": "Starlight", "rus": "Сияющая звезда"},
            {"eng": "Deep Blue", "rus": "Темно-синий"},
            {"eng": "Cosmic Orange", "rus": "Космический оранжевый"},
            {"eng": "Yellow", "rus": "Желтый"},
            {"eng": "Pink", "rus": "Розовый"},
            {"eng": "Blue", "rus": "Голубой"},
            {"eng": "Rose Gold", "rus": "Розовое золото"},
            {"eng": "White", "rus": "Белый"},
            {"eng": "Charcoal Gray", "rus": "Серый (угольный)"},
            {"eng": "Denim", "rus": "Джинсовый"},
            {"eng": "Black", "rus": "Черный (аксессуар)"},
            {"eng": "Rapid Red", "rus": "Красный"},
            {"eng": "Fox Orange", "rus": "Оранжевый"},
            {"eng": "Electric Lavender", "rus": "Лавандовый"},
            {"eng": "Berry", "rus": "Ягодный"},
        ]
        
        for color_data in colors_data:
            stmt = select(Color).where(Color.eng == color_data["eng"])
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                color = Color(**color_data)
                session.add(color)
                print(f"  ✅ {color_data['eng']} ({color_data['rus']})")
        
        await session.commit()
        print("\n" + "=" * 60)
        print("✅ База данных инициализирована!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(init_db())