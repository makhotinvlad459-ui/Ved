# backend/app/services/ai/tools.py

TOOLS = [
    # ============================================================
    # READ-ONLY (Безопасные запросы)
    # ============================================================
    {
        "type": "function",
        "function": {
            "name": "count_products",
            "description": "Посчитать количество товаров в базе. Можно с фильтрами: по категории, наличию веса, наличию модели, подстроке в описании.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_name": {
                        "type": ["string", "null"],
                        "description": "Название категории (например, 'Ноутбуки Lenovo'). Если не указано — все категории."
                    },
                    "has_weight": {
                        "type": ["boolean", "null"],
                        "description": "true — только с весом, false — только без веса. Если не указано — все."
                    },
                    "has_model_number": {
                        "type": ["boolean", "null"],
                        "description": "true — только с моделью, false — только без модели (пустая строка)."
                    },
                    "pattern": {
                        "type": ["string", "null"],
                        "description": "Подстрока для поиска в description (например, 'sport band')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Найти товары по подстроке в part_number или description. Возвращает список с id, part_number, description, weight, category, model_number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Подстрока для поиска (например, 'sport band' или 'MT0K3')."
                    },
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Максимум результатов (по умолчанию 20, максимум 50)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_missing_part_numbers",
            "description": "Проверить, каких артикулов нет в базе. Возвращает два списка: found (есть) и missing (нет).",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_numbers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список артикулов для проверки (например, ['ABC123', 'XYZ789'])."
                    }
                },
                "required": ["part_numbers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_products_exist",
            "description": "Проверить, какие товары из списка уже есть в базе, а каких нет. Принимает массив объектов {part_number, description}. Возвращает: found (есть, с данными из БД) и missing (нет, с исходными данными). Используй, когда пользователь копирует позиции из инвойса и хочет узнать, что уже заведено.",
            "parameters": {
                "type": "object",
                "properties": {
                    "products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "part_number": {"type": "string", "description": "Артикул"},
                                "description": {"type": ["string", "null"], "description": "Описание (для контекста, может быть пустым)"}
                            },
                            "required": ["part_number"]
                        },
                        "description": "Массив товаров для проверки. Максимум 200 за раз."
                    }
                },
                "required": ["products"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_weight",
            "description": "Узнать вес товара по артикулу. Если вес не задан — вернёт null.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number": {
                        "type": "string",
                        "description": "Артикул товара (например, 'MT0K3ZM/A')."
                    }
                },
                "required": ["part_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_products_without_weight",
            "description": "Найти список товаров, у которых отсутствует вес (weight = null или 0). Возвращает список с part_number, description и категорией.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Максимум результатов (по умолчанию 20, максимум 50)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_products_by_category",
            "description": "Найти список товаров в конкретной категории. Возвращает part_number, description, weight, model_number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_name": {
                        "type": "string",
                        "description": "Название категории (например, 'Ноутбуки Lenovo')."
                    },
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Максимум результатов (по умолчанию 20, максимум 50)."
                    }
                },
                "required": ["category_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_products_without_model_number",
            "description": "Найти товары, у которых не указан номер модели (model_number пустой или NULL).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Максимум результатов (по умолчанию 20, максимум 50)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "Получить список всех активных категорий с их префиксами.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    # --- ВЫПОЛНЕНИЕ SQL ---
    {
        "type": "function",
        "function": {
            "name": "execute_read_sql",
            "description": "Выполнить SELECT-запрос к базе данных. Используй для сложной фильтрации, сортировки, агрегации (COUNT, SUM, AVG, GROUP BY), JOIN-ов. ЗАПРЕЩЕНО использовать UPDATE, DELETE, INSERT. Схема: products(id, part_number, description, weight, model_number, category_id, coo), categories(id, name, prefix_ru), colors(id, eng, rus).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT запрос. Пример: SELECT part_number, description FROM products WHERE description ILIKE '%iphone%' ORDER BY weight DESC LIMIT 50;"
                    }
                },
                "required": ["query"]
            }
        }
    },

    # ============================================================
    # WRITE (требуют подтверждения)
    # ============================================================
    {
        "type": "function",
        "function": {
            "name": "update_product_weight",
            "description": "Обновить вес товара. Можно по конкретному part_number, списку part_numbers или массово по pattern. ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ. Максимум 100 записей за раз.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number": {
                        "type": ["string", "null"],
                        "description": "Один артикул товара. Если обновляешь список, используй part_numbers."
                    },
                    "part_numbers": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Список артикулов для массового обновления по списку."
                    },
                    "pattern": {
                        "type": ["string", "null"],
                        "description": "Подстрока в description для массового обновления (например, 'sport band'). Минимум 3 символа. Нельзя использовать вместе с part_number/part_numbers. Максимум 100 записей за раз."
                    },
                    "new_weight": {
                        "type": ["number", "null"],
                        "description": "Новый вес в кг (например, 0.6). Если пользователь не указал точную цифру в текущем сообщении, передай null."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_product_category",
            "description": "Назначить категорию существующим товарам. Можно по списку part_numbers или по pattern. ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ. Максимум 100 записей за раз.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_numbers": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Список артикулов. Используй, если категория назначается конкретным товарам."
                    },
                    "pattern": {
                        "type": ["string", "null"],
                        "description": "Подстрока в description для массового назначения. Минимум 3 символа. Нельзя вместе с part_numbers."
                    },
                    "category_name": {
                        "type": "string",
                        "description": "Название категории (например, 'Ремешки для часов APPLE')."
                    }
                },
                "required": ["category_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_product_model_number",
            "description": "Назначить один и тот же номер модели (model_number) списку товаров по артикулам. ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ. Максимум 100 записей.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_numbers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список артикулов (например, ['ABC123', 'XYZ789'])."
                    },
                    "model_number": {
                        "type": "string",
                        "description": "Номер модели, который нужно установить (например, 'A2890')."
                    }
                },
                "required": ["part_numbers", "model_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_category",
            "description": "Создать новую категорию товаров. ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название категории (например, 'Роботы-пылесосы')."
                    },
                    "prefix_ru": {
                        "type": "string",
                        "description": "Русский префикс для названий товаров (например, 'Робот-пылесос торговой марки')."
                    },
                    "name_eng": {
                        "type": ["string", "null"],
                        "description": "Английское название (опционально)."
                    }
                },
                "required": ["name", "prefix_ru"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_category",
            "description": "Переименовать существующую категорию. Позволяет изменить название категории (поле name), не затрагивая сами товары. ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_name": {
                        "type": "string",
                        "description": "Текущее название категории (например, 'Очки')."
                    },
                    "new_name": {
                        "type": "string",
                        "description": "Новое название категории (например, 'Очки Ray-Ban')."
                    }
                },
                "required": ["old_name", "new_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_products",
            "description": "Создать один или несколько товаров. ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ. Каждый товар должен иметь part_number и description. Если категория не указана — товар создастся без категории (потом можно назначить через update_product_category).",
            "parameters": {
                "type": "object",
                "properties": {
                    "products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "part_number": {"type": "string", "description": "Артикул (обязательно)"},
                                "description": {"type": "string", "description": "Описание товара (обязательно)"},
                                "model_number": {"type": ["string", "null"], "description": "Номер модели (опционально). Если не указан, передавай пустую строку."},
                                "category_name": {"type": ["string", "null"], "description": "Название категории (опционально)"},
                                "weight": {"type": ["number", "null"], "description": "Вес в кг (опционально)"},
                                "coo": {"type": ["string", "null"], "description": "Страна происхождения (опционально)"}
                            },
                            "required": ["part_number", "description"]
                        },
                        "description": "Массив товаров для создания. Максимум 20 за раз."
                    }
                },
                "required": ["products"]
            }
        }
    },
]

# ============================================================
# КАТЕГОРИИ TOOLS
# ============================================================

WRITE_TOOLS = {
    "update_product_weight",
    "update_product_category",
    "update_product_model_number",
    "create_category",
    "create_products",
    "rename_category",
}

READ_TOOLS = {
    "count_products",
    "search_products",
    "find_missing_part_numbers",
    "check_products_exist",
    "get_product_weight",
    "find_products_without_weight",
    "find_products_by_category",
    "find_products_without_model_number",
    "list_categories",
    "execute_read_sql",
}

# Лимиты (используются в executor для валидации)
LIMITS = {
    "update_product_weight": 100,
    "update_product_category": 100,
    "update_product_model_number": 100,
    "create_products": 20,
    "check_products_exist": 200,
    "search_products": 50,
    "pattern_min_length": 3,
}