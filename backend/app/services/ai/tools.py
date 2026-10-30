# # backend/app/services/ai/tools.py
"""
JSON-схемы tools для Groq Function Calling.
Модель читает эти описания и решает, какую функцию вызвать.

ВАЖНО: для всех необязательных параметров тип = ["<type>", "null"],
иначе Groq отбивает запрос с 400, когда модель передаёт null.
"""

TOOLS = [
    # ============================================================
    # READ-ONLY
    # ============================================================
    {
        "type": "function",
        "function": {
            "name": "count_products",
            "description": "Посчитать количество товаров в базе. Можно с фильтрами: по категории, наличию веса, подстроке в описании.",
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
            "description": "Найти товары по подстроке в part_number или description. Возвращает список с id, part_number, description, weight, category.",
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
            "name": "list_categories",
            "description": "Получить список всех активных категорий с их префиксами.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
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
            "description": "Обновить вес товара. Можно по конкретному part_number или массово по pattern (подстрока в description). ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ пользователя. Максимум 100 записей за раз.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number": {
                        "type": ["string", "null"],
                        "description": "Артикул конкретного товара. Используй, если нужно обновить один товар."
                    },
                    "pattern": {
                        "type": ["string", "null"],
                        "description": "Подстрока в description для массового обновления (например, 'sport band'). Минимум 3 символа. Нельзя использовать вместе с part_number. Максимум 100 записей за раз."
                    },
                    "new_weight": {
                        "type": "number",
                        "description": "Новый вес в кг (например, 0.6)."
                    }
                },
                "required": ["new_weight"]
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
                                "model_number": {"type": ["string", "null"], "description": "Номер модели (опционально)"},
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
    "create_category",
    "create_products",
}

READ_TOOLS = {
    "count_products",
    "search_products",
    "find_missing_part_numbers",
    "check_products_exist",
    "get_product_weight",
    "find_products_without_weight"
    "list_categories",
}

# Лимиты (используются в executor для валидации)
LIMITS = {
    "update_product_weight": 100,
    "update_product_category": 100,
    "create_products": 20,
    "check_products_exist": 200,
    "search_products": 50,
    "pattern_min_length": 3,
}