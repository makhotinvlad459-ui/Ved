# backend/app/services/cz_card_generator.py
"""
Генератор файлов IMPORT_K3_*.xlsx для сервиса «Карточки ЧЗ».
Заполняет шаблоны по выбранным позициям инвойса.
"""
import os
import re
import zipfile
import openpyxl
from openpyxl.styles import PatternFill, Alignment
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from app.models import CzCardProduct, CzColorMapping, CzCategoryMapping


TEMPLATES_DIR = "/app/app/templates"
OUTPUT_DIR = "/app/output"

# Жёлтая заливка для незаполненных обязательных ячеек
YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

# Маппинг категории → имя файла шаблона
CATEGORY_TO_TEMPLATE = {
    "Смартфоны": "IMPORT_K3_Смартфоны.xlsx",
    "Планшеты": "IMPORT_K3_Планшеты.xlsx",
    "Ноутбуки": "IMPORT_K3_Ноутбуки.xlsx",
}

# Префикс названия для полного наименования
CATEGORY_TO_PREFIX = {
    "Смартфоны": "Смартфон",
    "Планшеты": "Планшет",
    "Ноутбуки": "Ноутбук",
}


# ============================================================
# ЦВЕТ
# ============================================================

def extract_color(description: str, color_mappings: List[CzColorMapping]) -> tuple:
    """
    Ищет самое длинное совпадение eng-цвета в описании.
    Возвращает (eng, cz_value) или (None, None).
    """
    if not description or not color_mappings:
        return None, None

    d = description.lower()
    matches = []
    for cm in color_mappings:
        if cm.eng and cm.eng.lower() in d:
            matches.append((cm.eng, cm.cz_value, len(cm.eng)))

    if not matches:
        return None, None

    # Самое длинное совпадение
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches[0][0], matches[0][1]


# ============================================================
# ПОЛНОЕ НАИМЕНОВАНИЕ
# ============================================================

def build_full_name(category: str, description: str) -> str:
    """
    Полное наименование = префикс + описание.
    Пример: 'Смартфон Apple iPhone 18 Pro Max 1Tb Black (MJXX4ZA/A)'
    """
    prefix = CATEGORY_TO_PREFIX.get(category, "")
    desc = (description or "").strip()
    if prefix:
        return f"{prefix} {desc}"
    return desc


# ============================================================
# ГЕНЕРАЦИЯ ОДНОГО ФАЙЛА
# ============================================================

def generate_category_file(
    category: str,
    items: List[Dict[str, Any]],
    category_mapping: CzCategoryMapping,
    color_mappings: List[CzColorMapping],
    product_cache: Dict[str, CzCardProduct],
    output_path: str,
) -> str:
    """
    Заполняет шаблон для одной категории.
    items — позиции инвойса (после обогащения из CzCardProduct).
    """
    template_name = CATEGORY_TO_TEMPLATE.get(category)
    if not template_name:
        raise Exception(f"Нет шаблона для категории {category}")

    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        raise Exception(f"Шаблон не найден: {template_path}")

    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    # Данные начинаются с 5-й строки (1-4 — заголовки/типы/подсказки)
    start_row = 5
    current_row = start_row

    for item in items:
        part_number = item.get("part_number")
        description = item.get("description", "")
        gtin = item.get("gtin", "")

        # === Атрибуты: приоритет CzCardProduct, потом описание ===
        cz_product: Optional[CzCardProduct] = product_cache.get(part_number)

        # Экран
        screen_size = None
        if cz_product and cz_product.screen_size:
            screen_size = cz_product.screen_size
        else:
            screen_size = item.get("screen_size")

        # RAM
        ram_gb = None
        if cz_product and cz_product.ram_gb:
            ram_gb = cz_product.ram_gb
        else:
            ram_gb = item.get("ram_gb")

        # ROM — всегда из описания
        rom_gb = item.get("rom_gb")

        # CPU
        cpu_vendor = None
        cpu_model = None
        if cz_product and cz_product.cpu_model:
            cpu_vendor = cz_product.cpu_vendor
            cpu_model = cz_product.cpu_model
        else:
            cpu_vendor = item.get("cpu_vendor")
            cpu_model = item.get("cpu_model")

        # Цвет
        color_eng, color_cz = extract_color(description, color_mappings)

        # Вид товара — из category_mapping
        vid_tovara = category_mapping.vid_tovara
        k3 = category_mapping.k3
        tnved = category_mapping.tnved
        okpd2 = category_mapping.okpd2

        # Товарный знак
        brand = item.get("brand") or ""

        # Полное наименование
        full_name = build_full_name(category, description)

        # Тип ROM (Гбайт / Тбайт)
        rom_type = "Гбайт"
        rom_value = rom_gb
        if rom_gb and rom_gb >= 1024:
            rom_type = "Тбайт"
            rom_value = rom_gb // 1024

        # === Заполняем колонки ===
        # A: gtin
        ws.cell(current_row, 1).value = gtin
        # B: tnved
        ws.cell(current_row, 2).value = tnved
        # C: k3
        ws.cell(current_row, 3).value = k3
        # D: полное наименование
        ws.cell(current_row, 4).value = full_name
        # E: товарный знак
        ws.cell(current_row, 5).value = brand
        # F: ОКПД2
        ws.cell(current_row, 6).value = okpd2
        # G: тип (Артикул)
        ws.cell(current_row, 7).value = "Артикул"
        # H: артикул
        ws.cell(current_row, 8).value = part_number
        # I: full_replace — НЕТ
        ws.cell(current_row, 9).value = "НЕТ"
        # J: вид товара
        ws.cell(current_row, 10).value = vid_tovara
        # K: цвет
        ws.cell(current_row, 11).value = color_cz
        # L: ФНН — ОТСУТСТВУЕТ
        ws.cell(current_row, 12).value = "ОТСУТСТВУЕТ"
        # M: реестр — ОТСУТСТВУЕТ
        ws.cell(current_row, 13).value = "ОТСУТСТВУЕТ"
        # N: экран
        ws.cell(current_row, 14).value = screen_size
        # O: тип RAM
        ws.cell(current_row, 15).value = "Гбайт"
        # P: RAM
        ws.cell(current_row, 16).value = ram_gb
        # Q: тип ROM
        ws.cell(current_row, 17).value = rom_type
        # R: ROM
        ws.cell(current_row, 18).value = rom_value
        # S: производитель CPU
        ws.cell(current_row, 19).value = cpu_vendor
        # T: модель CPU
        ws.cell(current_row, 20).value = cpu_model
        # U: код ТНВЭД (дубль)
        ws.cell(current_row, 21).value = tnved
        # V: автоприкрепление ДС/СС — НЕТ
        ws.cell(current_row, 22).value = "НЕТ"
        # W-Z, AA-AB: пусто (пользователь заполнит в ЧЗ)
        # AC-AD: пусто

        # === Жёлтая заливка незаполненных обязательных ячеек ===
        for col_idx, val in [
            (1, gtin),         # gtin
            (4, full_name),    # полное наименование
            (5, brand),        # бренд
            (8, part_number),  # артикул
            (11, color_cz),    # цвет
            (14, screen_size), # экран
            (16, ram_gb),      # RAM
            (18, rom_value),   # ROM
            (19, cpu_vendor),  # CPU vendor
            (20, cpu_model),   # CPU model
        ]:
            if val is None or (isinstance(val, str) and not val.strip()):
                ws.cell(current_row, col_idx).fill = YELLOW_FILL

        # Выравнивание по левому краю для описания
        ws.cell(current_row, 4).alignment = Alignment(wrap_text=True, vertical='top')

        current_row += 1

    wb.save(output_path)
    return output_path


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def generate_cz_cards_zip(
    session_id: str,
    parsed_items: List[Dict[str, Any]],
    selected_part_numbers: List[str],
    db: Session,
) -> tuple:
    """
    Принимает распарсенные позиции + выбранные part_number.
    Генерирует ZIP с файлами по категориям.
    Возвращает (zip_path, {filename: count}).
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Фильтруем только выбранные
    selected_set = set(p.upper() for p in selected_part_numbers)
    selected_items = [
        it for it in parsed_items
        if it.get("part_number", "").upper() in selected_set
    ]

    if not selected_items:
        raise Exception("Не выбрано ни одной позиции")

    # Группируем по категориям
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for it in selected_items:
        cat = it.get("category")
        if not cat:
            continue
        by_category.setdefault(cat, []).append(it)

    if not by_category:
        raise Exception("Нет позиций с определённой категорией")

    # Загружаем справочники из БД
    color_mappings = db.query(CzColorMapping).filter(
        CzColorMapping.is_active == True
    ).all()

    category_mappings = {
        cm.name: cm for cm in db.query(CzCategoryMapping).filter(
            CzCategoryMapping.is_active == True
        ).all()
    }

    # Кэш CzCardProduct по part_number
    part_numbers = [it.get("part_number") for it in selected_items]
    cz_products = db.query(CzCardProduct).filter(
        CzCardProduct.part_number.in_(part_numbers)
    ).all()
    product_cache = {p.part_number.upper(): p for p in cz_products}

    # Рабочая папка
    work_dir = os.path.join(OUTPUT_DIR, f"{session_id}_cz_cards_parts")
    os.makedirs(work_dir, exist_ok=True)

    files_info: Dict[str, int] = {}
    generated_paths: List[str] = []

    for category, items in by_category.items():
        cm = category_mappings.get(category)
        if not cm:
            print(f"⚠️ Нет CzCategoryMapping для {category}, пропуск")
            continue

        file_name = CATEGORY_TO_TEMPLATE.get(category)
        if not file_name:
            continue

        # Имя файла с коротким session_id
        short_sid = session_id[:8]
        name_parts = file_name.rsplit(".xlsx", 1)
        output_name = f"{name_parts[0]}_{short_sid}.xlsx"
        output_path = os.path.join(work_dir, output_name)

        generate_category_file(
            category=category,
            items=items,
            category_mapping=cm,
            color_mappings=color_mappings,
            product_cache=product_cache,
            output_path=output_path,
        )

        generated_paths.append(output_path)
        files_info[output_name] = len(items)

    if not generated_paths:
        raise Exception("Не создано ни одного файла")

    # ZIP
    zip_path = os.path.join(OUTPUT_DIR, f"cz_cards_{session_id[:8]}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in generated_paths:
            zf.write(file_path, arcname=os.path.basename(file_path))

    # Чистим временные файлы
    for fp in generated_paths:
        try:
            os.remove(fp)
        except Exception:
            pass
    try:
        os.rmdir(work_dir)
    except Exception:
        pass

    return zip_path, files_info