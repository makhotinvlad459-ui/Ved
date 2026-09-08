# backend/app/services/cz_generator.py
import openpyxl
import os
from typing import Dict, List, Any


def generate_cz_files(
    groups: Dict[str, Dict[str, Any]],
    gtin_products: Dict[str, Any],
    output_dir: str,
    session_id: str
) -> List[str]:
    """
    Создаёт .xlsx файлы для каждого GTIN
    Имя файла: GTIN_{gtin}-{count}.xlsx
    """
    created_files = []
    
    for gtin, data in groups.items():
        codes = data.get("codes", [])
        count = len(codes)
        
        filename = f"GTIN_{gtin}-{count}.xlsx"
        file_path = os.path.join(output_dir, f"{session_id}_{filename}")
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Коды ЧЗ"
        
        # Записываем коды в первый столбец (без заголовка)
        for i, code in enumerate(codes, start=1):
            ws.cell(i, 1).value = code
        
        wb.save(file_path)
        created_files.append(file_path)
        print(f"   📄 Создан файл: {filename} ({count} кодов)")
    
    return created_files