# backend/app/services/cz_generator.py
import openpyxl
import os
from typing import Dict, List, Any


def generate_cz_files(
    groups: Dict[str, List[str]],
    gtin_products: Dict[str, Any],
    output_dir: str,
    session_id: str
) -> List[str]:
    """
    Создаёт .xlsx файлы для каждого GTIN (только коды, без заголовков)
    """
    created_files = []
    
    for gtin, codes in groups.items():
        product = gtin_products.get(gtin)
        
        if product:
            parts = []
            if product.product_name:
                parts.append(product.product_name.replace(' ', '_'))
            if product.model_number:
                parts.append(product.model_number)
            if product.coo:
                parts.append(product.coo)
            
            if not parts:
                parts.append(gtin)
            
            filename = ".".join(parts) + ".xlsx"
        else:
            filename = f"GTIN_{gtin}.xlsx"
        
        file_path = os.path.join(output_dir, f"{session_id}_{filename}")
        
        # Создаём Excel файл
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Записываем ТОЛЬКО коды в первый столбец (без заголовков!)
        for i, code in enumerate(codes, start=1):
            ws.cell(i, 1).value = code.strip()
        
        wb.save(file_path)
        created_files.append(file_path)
        print(f"   📄 Создан файл: {filename} ({len(codes)} кодов)")
    
    return created_files