import openpyxl
import os
from typing import Dict, List, Any


def generate_cz_files(
    groups: Dict[str, List[str]],
    gtin_products: Dict[str, Any],
    output_dir: str,
    session_id: str
) -> List[str]:
    created_files = []
    
    for gtin, codes in groups.items():
        count = len(codes)
        
        filename = \"GTIN_\" + str(gtin) + \"-\" + str(count) + \".xlsx\"
        file_path = os.path.join(output_dir, session_id + \"_\" + filename)
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = \"Коды ЧЗ\"
        
        for i, code in enumerate(codes, start=1):
            ws.cell(i, 1).value = code
        
        wb.save(file_path)
        created_files.append(file_path)
        print(f\"   📄 Создан файл: {filename} ({count} кодов)\")
    
    return created_files