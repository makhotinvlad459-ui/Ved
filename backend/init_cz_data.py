# backend/init_cz_data.py
"""
Заполнение справочников ЧЗ: категории, цвета, модели iPhone/Samsung.
Запускать: docker exec excel_backend python init_cz_data.py
Повторный запуск безопасен — дубликаты не создаются.
"""
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import CzCardProduct, CzColorMapping, CzCategoryMapping


# ============================================================
# КАТЕГОРИИ
# ============================================================
CATEGORIES = [
    {
        "name": "Смартфоны",
        "k3": "30514",
        "tnved": "8517130000",
        "okpd2": "26.30.22.110",
        "vid_tovara": "СМАРТФОН",
        "keywords": "iphone,samsung,galaxy",
    },
    {
        "name": "Планшеты",
        "k3": "30466",
        "tnved": "8471300000",
        "okpd2": "26.20.11.110",
        "vid_tovara": "ПЛАНШЕТ",
        "keywords": "ipad",
    },
    {
        "name": "Ноутбуки",
        "k3": "30463",
        "tnved": "8471300000",
        "okpd2": "26.20.11.110",
        "vid_tovara": "НОУТБУК",
        "keywords": "macbook",
    },
]


# ============================================================
# ЦВЕТА
# ============================================================
COLORS = [
    ("Space Black", "ЧЕРНЫЙ"),
    ("Black", "ЧЕРНЫЙ"),
    ("Jet Black", "ЧЕРНЫЙ"),
    ("Silver", "СЕРЕБРЯНЫЙ"),
    ("Space Grey", "СЕРЫЙ"),
    ("Gravel Grey", "СЕРЫЙ"),
    ("Midnight", "ТЕМНО-СИНИЙ"),
    ("Starlight", "СЕРЕБРЯНЫЙ"),
    ("Deep Blue", "ТЕМНО-СИНИЙ"),
    ("Cosmic Orange", "ОРАНЖЕВЫЙ"),
    ("Rose Gold", "ЗОЛОТОЙ"),
    ("Denim", "СИНИЙ"),
    ("Rapid Red", "КРАСНЫЙ"),
    ("Fox Orange", "ОРАНЖЕВЫЙ"),
    ("Electric Lavender", "ФИОЛЕТОВЫЙ"),
    ("Berry", "МАЛИНОВЫЙ"),
    ("Yellow", "ЖЁЛТЫЙ"),
    ("Pink", "РОЗОВЫЙ"),
    ("Blue", "СИНИЙ"),
    ("White", "БЕЛЫЙ"),
    ("Charcoal Gray", "СЕРЫЙ"),
    ("Burgundy", "БОРДОВЫЙ"),
    ("Glacier", "ГОЛУБОЙ"),
    ("Blush", "РОЗОВЫЙ"),
    ("Cobalt Violet", "ФИОЛЕТОВЫЙ"),
    ("Sky Blue", "ГОЛУБОЙ"),
    ("Pink Gold", "РОЗОВЫЙ"),
    ("Titanium Jetblack", "ЧЕРНЫЙ"),
    ("Titanium Gray", "СЕРЫЙ"),
    ("Titanium Black", "ЧЕРНЫЙ"),
    ("Mint", "СВЕТЛО-ЗЕЛЕНЫЙ"),
    ("Navy", "ТЕМНО-СИНИЙ"),
    ("Icy Blue", "СВЕТЛО-СИНИЙ"),
    ("Silver Shadow", "СЕРЕБРЯНЫЙ"),
    ("Hyper Purple", "ФИОЛЕТОВЫЙ"),
    ("Quick Sand", "СВЕТЛО-БЕЖЕВЫЙ"),
    ("Power Pink", "РОЗОВЫЙ"),
]


# ============================================================
# МОДЕЛИ (ключ — НАЗВАНИЕ МОДЕЛИ, не part_number)
# ============================================================
PRODUCTS = [
    # iPhone 15
    {"model_name": "iPhone 15", "brand": "APPLE", "screen_size": 6.1, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"model_name": "iPhone 15 Plus", "brand": "APPLE", "screen_size": 6.7, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"model_name": "iPhone 15 Pro", "brand": "APPLE", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"model_name": "iPhone 15 Pro Max", "brand": "APPLE", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},

    # iPhone 16
    {"model_name": "iPhone 16", "brand": "APPLE", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"model_name": "iPhone 16 Plus", "brand": "APPLE", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"model_name": "iPhone 16 Pro", "brand": "APPLE", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"model_name": "iPhone 16 Pro Max", "brand": "APPLE", "screen_size": 6.9, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},

    # iPhone 17
    {"model_name": "iPhone 17", "brand": "APPLE", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    {"model_name": "iPhone 17 Air", "brand": "APPLE", "screen_size": 6.6, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    {"model_name": "iPhone 17 Pro", "brand": "APPLE", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},
    {"model_name": "iPhone 17 Pro Max", "brand": "APPLE", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},

    # iPhone 18
    {"model_name": "iPhone 18", "brand": "APPLE", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A20"},
    {"model_name": "iPhone 18 Plus", "brand": "APPLE", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A20"},
    {"model_name": "iPhone 18 Pro", "brand": "APPLE", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A20 Pro"},
    {"model_name": "iPhone 18 Pro Max", "brand": "APPLE", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A20 Pro"},

    # Samsung Galaxy S25
    {"model_name": "Galaxy S25", "brand": "Samsung", "screen_size": 6.2, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"model_name": "Galaxy S25+", "brand": "Samsung", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"model_name": "Galaxy S25 Ultra", "brand": "Samsung", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"model_name": "Galaxy S25 Edge", "brand": "Samsung", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"model_name": "Galaxy S25 FE", "brand": "Samsung", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Samsung", "cpu_model": "Exynos 2400"},

    # Samsung Galaxy S26
    {"model_name": "Galaxy S26", "brand": "Samsung", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
    {"model_name": "Galaxy S26+", "brand": "Samsung", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
    {"model_name": "Galaxy S26 Ultra", "brand": "Samsung", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
]


async def main():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("ЗАПОЛНЕНИЕ СПРАВОЧНИКОВ ЧЗ")
        print("=" * 60)

        # Категории
        print("\n📦 Категории:")
        for cat in CATEGORIES:
            stmt = select(CzCategoryMapping).where(CzCategoryMapping.name == cat["name"])
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                db.add(CzCategoryMapping(**cat))
                print(f"  ✅ {cat['name']}")
            else:
                print(f"  ⏭️ {cat['name']} (уже есть)")

        # Цвета
        print("\n🎨 Цвета:")
        for eng, cz in COLORS:
            stmt = select(CzColorMapping).where(CzColorMapping.eng == eng)
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                db.add(CzColorMapping(eng=eng, cz_value=cz))
                print(f"  ✅ {eng} → {cz}")
            else:
                print(f"  ⏭️ {eng} (уже есть)")

        # Модели
        print("\n📱 Модели:")
        for prod in PRODUCTS:
            stmt = select(CzCardProduct).where(CzCardProduct.model_name == prod["model_name"])
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                db.add(CzCardProduct(**prod))
                print(f"  ✅ {prod['model_name']}")
            else:
                print(f"  ⏭️ {prod['model_name']} (уже есть)")

        await db.commit()

        print("\n" + "=" * 60)
        print("✅ Готово!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())