import os
import time
import shutil

TEMP_DIR = '/app/temp'

def clean_old_files():
    now = time.time()
    for filename in os.listdir(TEMP_DIR):
        filepath = os.path.join(TEMP_DIR, filename)
        if os.path.isfile(filepath):
            # Удаляем файлы старше 1 часа
            if now - os.path.getmtime(filepath) > 3600:
                os.remove(filepath)
                print(f'🗑️ Удален старый файл: {filename}')

if __name__ == '__main__':
    clean_old_files()
