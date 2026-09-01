import sys
sys.path.append('/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Product, Category, Color
from app.database import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Получаем все категории
cat_computer = db.query(Category).filter(Category.name == "Компьютер").first()
cat_phone = db.query(Category).filter(Category.name == "Телефон").first()
cat_tablet = db.query(Category).filter(Category.name == "Планшет").first()
cat_watch = db.query(Category).filter(Category.name == "Часы").first()
cat_charger = db.query(Category).filter(Category.name == "Зарядное").first()

# Получаем цвета
color_black = db.query(Color).filter(Color.eng == "Space Black").first()
color_silver = db.query(Color).filter(Color.eng == "Silver").first()
color_midnight = db.query(Color).filter(Color.eng == "Midnight").first()
color_deep_blue = db.query(Color).filter(Color.eng == "Deep Blue").first()
color_cosmic_orange = db.query(Color).filter(Color.eng == "Cosmic Orange").first()
color_rose_gold = db.query(Color).filter(Color.eng == "Rose Gold").first()
color_space_grey = db.query(Color).filter(Color.eng == "Space Grey").first()
color_starlight = db.query(Color).filter(Color.eng == "Starlight").first()

models_data = [
    # MacBook Pro 16
    ("A3428", "MGEA4LL/A", "Apple MacBook Pro 16 Space Black 24Gb 1Tb", "Vietnam", cat_computer, color_black),
    ("A3428", "MGE64LL/A", "Apple MacBook Pro 16 Silver 48Gb 1Tb", "Vietnam", cat_computer, color_silver),
    ("A3428", "MGE44LL/A", "Apple MacBook Pro 16 Silver 24Gb 1Tb", "Vietnam", cat_computer, color_silver),
    # MacBook Pro 14
    ("A3426", "Z1ML001V2", "Apple MacBook Pro 14 Space Black 48Gb 1Tb", "China", cat_computer, color_black),
    ("A3434", "MDE34LL/A", "Apple MacBook Pro 14 Space Black 24Gb 1Tb", "Vietnam", cat_computer, color_black),
    ("A3426", "Z1MH0007W", "Apple MacBook Pro 14 Silver 48Gb 1Tb", "China", cat_computer, color_silver),
    # MacBook Air 15
    ("A3448", "Z1LQ00008", "Apple MacBook Air 15 Silver 24Gb 512Gb", "Vietnam", cat_computer, color_silver),
    ("A3448", "MDV94ZA/A", "Apple MacBook Air 15 Silver 16Gb 512Gb", "China", cat_computer, color_silver),
    ("A3448", "Z1LW00008", "Apple MacBook Air 15 Midnight 24Gb 512Gb", "Vietnam", cat_computer, color_midnight),
    ("A3448", "MDVH4ZA/A", "Apple MacBook Air 15 Midnight 16Gb 512Gb", "China", cat_computer, color_midnight),
    # Mac Mini
    ("A3238", "MU9D3LL/A", "Apple Mac Mini Silver 16Gb 256Gb", "Vietnam", cat_computer, color_silver),
    # iPhone
    ("A3526", "MFYU4ZA/A", "Apple iPhone 17 Pro Max 512Gb Deep Blue", "China", cat_phone, color_deep_blue),
    ("A3526", "MFYT4ZA/A", "Apple iPhone 17 Pro Max 512Gb Cosmic Orange", "China", cat_phone, color_cosmic_orange),
    # iPad Pro
    ("A3357", "MDWK4LL/A", "Apple iPad Pro 11 Space Black 256Gb", "Vietnam", cat_tablet, color_black),
    # iPad Air
    ("A3459", "MH334LL/A", "Apple iPad Air 11 Starlight 128Gb", "Vietnam", cat_tablet, color_starlight),
    ("A3460", "MH7D4ZP/A", "Apple iPad Air 11 Space Grey 256Gb", "Vietnam", cat_tablet, color_space_grey),
    ("A3460", "MH784ZP/A", "Apple iPad Air 11 Space Grey 128Gb", "China", cat_tablet, color_space_grey),
    # iPad
    ("A3354", "MD4D4LL/A", "Apple iPad 11 Yellow 128Gb", "Vietnam", cat_tablet, None),
    ("A3354", "MD4E4LL/A", "Apple iPad 11 Pink 128Gb", "Vietnam", cat_tablet, None),
    ("A3354", "MD4A4CL/A", "Apple iPad 11 Blue 128Gb", "China", cat_tablet, None),
    ("A3354", "MD4A4CL/A", "Apple iPad 11 Blue 128Gb", "Vietnam", cat_tablet, None),
    # Watch
    ("A3331", "MEU04LW/A", "Apple Watch Series 11 Rose Gold", "Vietnam", cat_watch, color_rose_gold),
    # Charger
    ("A2166", "MW2L3ZA/A", "Apple 96W USB-C Power Adapter", "China", cat_charger, None),
]

added = 0
for model_num, part, desc, coo, cat, color in models_data:
    existing = db.query(Product).filter(Product.part_number == part).first()
    if existing:
        print(f"⏭️ {part} уже есть")
        continue
    product = Product(
        model_number=model_num,
        part_number=part,
        description=desc,
        coo=coo,
        category_id=cat.id if cat else None,
        color_id=color.id if color else None,
        is_active=True
    )
    db.add(product)
    added += 1
    print(f"✅ {part}")

db.commit()
print(f"\n✅ Добавлено {added} моделей!")
db.close()