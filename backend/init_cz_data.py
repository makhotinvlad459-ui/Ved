# backend/init_cz_data.py
"""
Заполнение справочников ЧЗ дефолтными данными.
Запускать один раз: docker exec excel_backend python init_cz_data.py
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
# КАТЕГОРИИ ЧЗ
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
# ЦВЕТА (eng → значение ЧЗ)
# ============================================================
COLORS = [
    # Apple цвета
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
    # Samsung цвета
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
    # Beats цвета
    ("Hyper Purple", "ФИОЛЕТОВЫЙ"),
    ("Quick Sand", "СВЕТЛО-БЕЖЕВЫЙ"),
    ("Power Pink", "РОЗОВЫЙ"),
]


# ============================================================
# ТОВАРЫ (iPhone + Samsung)
# ============================================================
PRODUCTS = [
    # === iPhone 15 ===
    {"part_number": "MTP03", "brand": "APPLE", "model_name": "iPhone 15", "screen_size": 6.1, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTP13", "brand": "APPLE", "model_name": "iPhone 15", "screen_size": 6.1, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTP23", "brand": "APPLE", "model_name": "iPhone 15", "screen_size": 6.1, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTP33", "brand": "APPLE", "model_name": "iPhone 15", "screen_size": 6.1, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTP43", "brand": "APPLE", "model_name": "iPhone 15", "screen_size": 6.1, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTP63", "brand": "APPLE", "model_name": "iPhone 15", "screen_size": 6.1, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTP73", "brand": "APPLE", "model_name": "iPhone 15 Plus", "screen_size": 6.7, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTP83", "brand": "APPLE", "model_name": "iPhone 15 Plus", "screen_size": 6.7, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTQR3", "brand": "APPLE", "model_name": "iPhone 15 Plus", "screen_size": 6.7, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    {"part_number": "MTQT3", "brand": "APPLE", "model_name": "iPhone 15 Plus", "screen_size": 6.7, "ram_gb": 6, "cpu_vendor": "Apple", "cpu_model": "A16 Bionic"},
    # iPhone 15 Pro
    {"part_number": "MTUX3", "brand": "APPLE", "model_name": "iPhone 15 Pro", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTV03", "brand": "APPLE", "model_name": "iPhone 15 Pro", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTV13", "brand": "APPLE", "model_name": "iPhone 15 Pro", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTV23", "brand": "APPLE", "model_name": "iPhone 15 Pro", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTV33", "brand": "APPLE", "model_name": "iPhone 15 Pro", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTV43", "brand": "APPLE", "model_name": "iPhone 15 Pro", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    # iPhone 15 Pro Max
    {"part_number": "MTU63", "brand": "APPLE", "model_name": "iPhone 15 Pro Max", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTU73", "brand": "APPLE", "model_name": "iPhone 15 Pro Max", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTU83", "brand": "APPLE", "model_name": "iPhone 15 Pro Max", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTU93", "brand": "APPLE", "model_name": "iPhone 15 Pro Max", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},
    {"part_number": "MTUA3", "brand": "APPLE", "model_name": "iPhone 15 Pro Max", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A17 Pro"},

    # === iPhone 16 ===
    {"part_number": "MTP03", "brand": "APPLE", "model_name": "iPhone 16", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP13", "brand": "APPLE", "model_name": "iPhone 16", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP23", "brand": "APPLE", "model_name": "iPhone 16", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP33", "brand": "APPLE", "model_name": "iPhone 16", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP43", "brand": "APPLE", "model_name": "iPhone 16", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP63", "brand": "APPLE", "model_name": "iPhone 16", "screen_size": 6.1, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP73", "brand": "APPLE", "model_name": "iPhone 16 Plus", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP83", "brand": "APPLE", "model_name": "iPhone 16 Plus", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTP93", "brand": "APPLE", "model_name": "iPhone 16 Plus", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    {"part_number": "MTPA3", "brand": "APPLE", "model_name": "iPhone 16 Plus", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18"},
    # iPhone 16 Pro
    {"part_number": "MTQ03", "brand": "APPLE", "model_name": "iPhone 16 Pro", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ13", "brand": "APPLE", "model_name": "iPhone 16 Pro", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ23", "brand": "APPLE", "model_name": "iPhone 16 Pro", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ33", "brand": "APPLE", "model_name": "iPhone 16 Pro", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ43", "brand": "APPLE", "model_name": "iPhone 16 Pro", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    # iPhone 16 Pro Max
    {"part_number": "MTQ53", "brand": "APPLE", "model_name": "iPhone 16 Pro Max", "screen_size": 6.9, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ63", "brand": "APPLE", "model_name": "iPhone 16 Pro Max", "screen_size": 6.9, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ73", "brand": "APPLE", "model_name": "iPhone 16 Pro Max", "screen_size": 6.9, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ83", "brand": "APPLE", "model_name": "iPhone 16 Pro Max", "screen_size": 6.9, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},
    {"part_number": "MTQ93", "brand": "APPLE", "model_name": "iPhone 16 Pro Max", "screen_size": 6.9, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A18 Pro"},

    # === iPhone 17 ===
    {"part_number": "MJQ04", "brand": "APPLE", "model_name": "iPhone 17", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    {"part_number": "MJQ14", "brand": "APPLE", "model_name": "iPhone 17", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    {"part_number": "MJQ24", "brand": "APPLE", "model_name": "iPhone 17", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    {"part_number": "MJQ34", "brand": "APPLE", "model_name": "iPhone 17", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    {"part_number": "MJQ44", "brand": "APPLE", "model_name": "iPhone 17", "screen_size": 6.3, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    # iPhone 17 Air
    {"part_number": "MJQ54", "brand": "APPLE", "model_name": "iPhone 17 Air", "screen_size": 6.6, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    {"part_number": "MJQ64", "brand": "APPLE", "model_name": "iPhone 17 Air", "screen_size": 6.6, "ram_gb": 8, "cpu_vendor": "Apple", "cpu_model": "A19"},
    # iPhone 17 Pro
    {"part_number": "MJQ74", "brand": "APPLE", "model_name": "iPhone 17 Pro", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},
    {"part_number": "MJQ84", "brand": "APPLE", "model_name": "iPhone 17 Pro", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},
    {"part_number": "MJQ94", "brand": "APPLE", "model_name": "iPhone 17 Pro", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},
    # iPhone 17 Pro Max
    {"part_number": "MJQA4", "brand": "APPLE", "model_name": "iPhone 17 Pro Max", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},
    {"part_number": "MJQB4", "brand": "APPLE", "model_name": "iPhone 17 Pro Max", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},
    {"part_number": "MJQC4", "brand": "APPLE", "model_name": "iPhone 17 Pro Max", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Apple", "cpu_model": "A19 Pro"},

    # === Samsung Galaxy S25 ===
    {"part_number": "SM-S931B", "brand": "Samsung", "model_name": "Galaxy S25", "screen_size": 6.2, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"part_number": "SM-S931B/DS", "brand": "Samsung", "model_name": "Galaxy S25", "screen_size": 6.2, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    # Galaxy S25+
    {"part_number": "SM-S936B", "brand": "Samsung", "model_name": "Galaxy S25+", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"part_number": "SM-S936B/DS", "brand": "Samsung", "model_name": "Galaxy S25+", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    # Galaxy S25 Ultra
    {"part_number": "SM-S938B", "brand": "Samsung", "model_name": "Galaxy S25 Ultra", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"part_number": "SM-S938B/DS", "brand": "Samsung", "model_name": "Galaxy S25 Ultra", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    # Galaxy S25 Edge
    {"part_number": "SM-S937B", "brand": "Samsung", "model_name": "Galaxy S25 Edge", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    {"part_number": "SM-S937B/DS", "brand": "Samsung", "model_name": "Galaxy S25 Edge", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite"},
    # Galaxy S25 FE
    {"part_number": "SM-S731B", "brand": "Samsung", "model_name": "Galaxy S25 FE", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Samsung", "cpu_model": "Exynos 2400"},
    {"part_number": "SM-S731B/DS", "brand": "Samsung", "model_name": "Galaxy S25 FE", "screen_size": 6.7, "ram_gb": 8, "cpu_vendor": "Samsung", "cpu_model": "Exynos 2400"},

    # === Samsung Galaxy S26 ===
    {"part_number": "SM-S942B", "brand": "Samsung", "model_name": "Galaxy S26", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
    {"part_number": "SM-S942B/DS", "brand": "Samsung", "model_name": "Galaxy S26", "screen_size": 6.3, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
    # Galaxy S26+
    {"part_number": "SM-S947B", "brand": "Samsung", "model_name": "Galaxy S26+", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
    {"part_number": "SM-S947B/DS", "brand": "Samsung", "model_name": "Galaxy S26+", "screen_size": 6.7, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
    # Galaxy S26 Ultra
    {"part_number": "SM-S948B", "brand": "Samsung", "model_name": "Galaxy S26 Ultra", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
    {"part_number": "SM-S948B/DS", "brand": "Samsung", "model_name": "Galaxy S26 Ultra", "screen_size": 6.9, "ram_gb": 12, "cpu_vendor": "Qualcomm", "cpu_model": "Snapdragon 8 Elite Gen 5"},
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

        # Товары
        print("\n📱 Товары (iPhone + Samsung):")
        for prod in PRODUCTS:
            stmt = select(CzCardProduct).where(CzCardProduct.part_number == prod["part_number"])
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                db.add(CzCardProduct(**prod))
                print(f"  ✅ {prod['part_number']} — {prod['model_name']}")
            else:
                print(f"  ⏭️ {prod['part_number']} (уже есть)")

        await db.commit()

        print("\n" + "=" * 60)
        print("✅ Готово!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())