# backend/app/services/cz_card_generator.py
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

YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

CATEGORY_TO_TEMPLATE = {
    "Смартфоны": "IMPORT_K3_Смартфоны.xlsx",
    "Планшеты": "IMPORT_K3_Планшеты.xlsx",
    "Ноутбуки": "IMPORT_K3_Ноутбуки.xlsx",
}

CATEGORY_TO_PREFIX = {
    "Смартфоны": "Смартфон",
    "Планшеты": "Планшет",
    "Ноутбуки": "Ноутбук",
}


# ============================================================
# ИЗВЛЕЧЕНИЕ НАЗВАНИЯ МОДЕЛИ ИЗ ОПИСАНИЯ
# ============================================================

def extract_model_name(description: str) -> Optional[str]:
    """
    Извлекает название модели для поиска в CzCardProduct.

    Примеры:
      'Apple iPhone 18 Pro Max 256Gb Black (MJX54VC/A)' → 'iPhone 18 Pro Max'
      'Apple iPhone 18 Pro 256GB Silver (MJQ44LL/A)' → 'iPhone 18 Pro'
      'Samsung Galaxy S26 Ultra 12/256Gb White (SM-S948BZWIMEA)' → 'Galaxy S26 Ultra'
      'Apple iPad Air 11 Starlight 128Gb' → 'iPad Air 11'
      'Apple MacBook Pro 16" Space Black' → 'MacBook Pro 16'
    """
    if not description:
        return None

    d = description

    # iPhone (порядок: Pro Max → Pro → Plus → Air → Mini → e → без суффикса)
    m = re.search(
        r'iPhone\s+\d+(?:\s+(?:Pro\s+Max|Pro|Plus|Air|Mini|e|Duo))?',
        d, re.IGNORECASE
    )
    if m:
        return m.group(0).strip()

    # Samsung Galaxy (S26 Ultra, S26+, S26, A55 и т.д.)
    m = re.search(
        r'Galaxy\s+[A-Z]\d+(?:\s+(?:Ultra|Plus))?(?:\+)?',
        d
    )
    if m:
        return m.group(0).strip()

    # MacBook (Pro/Air/Neo + размер)
    m = re.search(
        r'MacBook\s+(?:Pro|Air|Neo)(?:\s+\d+(?:\.\d+)?["\u201d\u2033]?)?',
        d
    )
    if m:
        return m.group(0).strip()

    # iPad (Pro/Air/Mini + размер)
    m = re.search(
        r'iPad\s+(?:Pro|Air|Mini)?(?:\s+\d+(?:\.\d+)?["\u201d\u2033]?)?',
        d
    )
    if m:
        return m.group(0).strip()

    return None


def extract_color(description: str, color_mappings: List[CzColorMapping]) -> tuple:
    if not description or not color_mappings:
        return None, None

    d = description.lower()
    matches = []
    for cm in color_mappings:
        if cm.eng and cm.eng.lower() in d:
            matches.append((cm.eng, cm.cz_value, len(cm.eng)))

    if not matches:
        return None, None

    matches.sort(key=lambda x: x[2], reverse=True)
    return matches[0][0], matches[0][1]


def build_full_name(category: str, description: str) -> str:
    prefix = CATEGORY_TO_PREFIX.get(category, "")
    desc = (description or "").strip()
    if prefix:
        return f"{prefix} {desc}"
    return desc


def _is_duo(description: str) -> bool:
    """Определяет, является ли устройство складным (iPhone Duo)."""
    if not description:
        return False
    return "duo" in description.lower()


def _pick_vid_tovara(category: str, description: str, default: str) -> str:
    """
    Подбирает «Вид товара» из справочника ЧЗ.
    Для iPhone Duo — «СМАРТФОН СКЛАДНОЙ», для остальных — default из БД.
    """
    if category == "Смартфоны" and _is_duo(description):
        return "СМАРТФОН СКЛАДНОЙ"
    return default


def generate_category_file(
    category: str,
    items: List[Dict[str, Any]],
    category_mapping: CzCategoryMapping,
    color_mappings: List[CzColorMapping],
    product_cache: Dict[str, CzCardProduct],
    output_path: str,
) -> str:
    template_name = CATEGORY_TO_TEMPLATE.get(category)
    if not template_name:
        raise Exception(f"Нет шаблона для категории {category}")

    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        raise Exception(f"Шаблон не найден: {template_path}")

    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    start_row = 5
    current_row = start_row

    for item in items:
        part_number = item.get("part_number")
        description = item.get("description", "")
        gtin = item.get("gtin", "")

        # === Ищем модель по названию ===
        model_name = extract_model_name(description)
        cz_product: Optional[CzCardProduct] = None
        if model_name:
            cz_product = product_cache.get(model_name.lower())

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

        color_eng, color_cz = extract_color(description, color_mappings)

        vid_tovara_default = category_mapping.vid_tovara
        vid_tovara = _pick_vid_tovara(category, description, vid_tovara_default)

        k3 = category_mapping.k3
        tnved = category_mapping.tnved
        okpd2 = category_mapping.okpd2

        brand = item.get("brand") or ""
        full_name = build_full_name(category, description)

        rom_type = "Гбайт"
        rom_value = rom_gb
        if rom_gb and rom_gb >= 1024:
            rom_type = "Тбайт"
            rom_value = rom_gb // 1024

        # === GTIN как текст (сохраняем ведущий ноль) ===
        gtin_cell = ws.cell(current_row, 1)
        gtin_cell.value = str(gtin) if gtin else ""
        gtin_cell.number_format = '@'

        # === Tnved как текст ===
        tnved_cell = ws.cell(current_row, 2)
        tnved_cell.value = str(tnved) if tnved else ""
        tnved_cell.number_format = '@'

        ws.cell(current_row, 3).value = k3
        ws.cell(current_row, 4).value = full_name
        ws.cell(current_row, 5).value = brand
        ws.cell(current_row, 6).value = okpd2
        ws.cell(current_row, 7).value = "Артикул"
        ws.cell(current_row, 8).value = part_number
        ws.cell(current_row, 9).value = "НЕТ"
        ws.cell(current_row, 10).value = vid_tovara
        ws.cell(current_row, 11).value = color_cz
        ws.cell(current_row, 12).value = "ОТСУТСТВУЕТ"
        ws.cell(current_row, 13).value = "ОТСУТСТВУЕТ"
        ws.cell(current_row, 14).value = screen_size
        ws.cell(current_row, 15).value = "Гбайт"
        ws.cell(current_row, 16).value = ram_gb
        ws.cell(current_row, 17).value = rom_type
        ws.cell(current_row, 18).value = rom_value
        ws.cell(current_row, 19).value = cpu_vendor
        ws.cell(current_row, 20).value = cpu_model
        ws.cell(current_row, 21).value = tnved

        # === Tnved (дубль в U) как текст ===
        u_cell = ws.cell(current_row, 21)
        u_cell.value = str(tnved) if tnved else ""
        u_cell.number_format = '@'

        ws.cell(current_row, 22).value = "НЕТ"

        for col_idx, val in [
            (1, gtin),
            (4, full_name),
            (5, brand),
            (8, part_number),
            (11, color_cz),
            (14, screen_size),
            (16, ram_gb),
            (18, rom_value),
            (19, cpu_vendor),
            (20, cpu_model),
        ]:
            if val is None or (isinstance(val, str) and not val.strip()):
                ws.cell(current_row, col_idx).fill = YELLOW_FILL

        ws.cell(current_row, 4).alignment = Alignment(wrap_text=True, vertical='top')
        current_row += 1

    # === УДАЛЯЕМ ПУСТЫЕ СТРОКИ (ЧЗ требует, чтобы все строки были заполнены) ===
    rows_to_delete = []
    for r in range(start_row, ws.max_row + 1):
        a_val = ws.cell(r, 1).value
        if a_val is None or (isinstance(a_val, str) and a_val.strip() == ""):
            rows_to_delete.append(r)

    # Удаляем с конца, чтобы не сбить индексы
    for r in reversed(rows_to_delete):
        ws.delete_rows(r)

    print(f"   🗑️ Удалено пустых строк: {len(rows_to_delete)}")

    wb.save(output_path)
    return output_path


def generate_cz_cards_zip(
    session_id: str,
    parsed_items: List[Dict[str, Any]],
    selected_part_numbers: List[str],
    db: Session,
) -> tuple:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    selected_set = set(p.upper() for p in selected_part_numbers)

    # Дедупликация по part_number
    seen = set()
    unique_items = []
    for it in parsed_items:
        pn = it.get("part_number", "").upper()
        if pn not in selected_set:
            continue
        if pn in seen:
            continue
        seen.add(pn)
        unique_items.append(it)

    if not unique_items:
        raise Exception("Не выбрано ни одной позиции")

    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for it in unique_items:
        cat = it.get("category")
        if not cat:
            continue
        by_category.setdefault(cat, []).append(it)

    if not by_category:
        raise Exception("Нет позиций с определённой категорией")

    color_mappings = db.query(CzColorMapping).filter(
        CzColorMapping.is_active == True
    ).all()

    category_mappings = {
        cm.name: cm for cm in db.query(CzCategoryMapping).filter(
            CzCategoryMapping.is_active == True
        ).all()
    }

    # === Кэш моделей: ключ — model_name в нижнем регистре ===
    cz_products = db.query(CzCardProduct).filter(
        CzCardProduct.is_active == True
    ).all()
    product_cache = {p.model_name.lower(): p for p in cz_products}

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

    zip_path = os.path.join(OUTPUT_DIR, f"cz_cards_{session_id[:8]}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in generated_paths:
            zf.write(file_path, arcname=os.path.basename(file_path))

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