# backend/app/services/ai/client.py
"""
Обёртка над Groq API с fallback на OpenRouter.
"""

import asyncio
import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# --- Конфигурация Groq ---
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# --- Конфигурация OpenRouter (fallback) ---
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Для OpenRouter можно использовать те же модели, либо другие (например, google/gemini-2.5-flash)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b") 

TIMEOUT = 30.0
MAX_RETRIES = 1  # Уменьшили, чтобы быстрее переключаться
RETRY_BACKOFF = [3.0]
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GroqError(Exception):
    """Ошибка вызова AI-провайдера."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _get_groq_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise GroqError("GROQ_API_KEY не задан в окружении backend")
    return key


def _get_openrouter_key() -> Optional[str]:
    return os.getenv("OPENROUTER_API_KEY")


async def _call_openai_compatible(
    url: str,
    api_key: str,
    body: Dict[str, Any],
    provider_name: str,
) -> Dict[str, Any]:
    """Универсальный вызов OpenAI-совместимого API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://89.38.131.221", # Для OpenRouter (опционально)
        "X-Title": "VED Processor",
    }

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(url, json=body, headers=headers)

            if resp.status_code in RETRYABLE_STATUS:
                snippet = resp.text[:300]
                logger.warning(f"{provider_name} {resp.status_code}: {snippet}")
                last_error = GroqError(
                    f"{provider_name} вернул {resp.status_code}: {snippet}",
                    status_code=resp.status_code,
                )
                if resp.status_code == 429:
                    raise last_error  # Не ретраим 429, сразу наверх
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
                    continue
                raise last_error

            if resp.status_code >= 400:
                snippet = resp.text[:500]
                raise GroqError(
                    f"{provider_name} вернул {resp.status_code}: {snippet}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            usage = data.get("usage", {})
            logger.info(
                f"{provider_name} OK: prompt={usage.get('prompt_tokens')}, "
                f"completion={usage.get('completion_tokens')}, "
                f"total={usage.get('total_tokens')}"
            )
            return data

        except httpx.TimeoutException as e:
            last_error = GroqError(f"{provider_name} timeout ({TIMEOUT}s): {e}")
            logger.warning(f"{provider_name} timeout (attempt {attempt+1})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            raise last_error

        except httpx.RequestError as e:
            last_error = GroqError(f"{provider_name} network error: {e}")
            logger.warning(f"{provider_name} network error: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            raise last_error

    raise last_error or GroqError(f"{provider_name}: неизвестная ошибка")


async def groq_chat(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    model: str = GROQ_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 300,
    reasoning_effort: Optional[str] = "low",
) -> Dict[str, Any]:
    """
    Пытается вызвать Groq. При ошибке 429 (или другой) переключается на OpenRouter.
    """
    body: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
        body["reasoning_format"] = "hidden"

    # --- 1. Пробуем Groq ---
    try:
        groq_key = _get_groq_key()
        return await _call_openai_compatible(GROQ_URL, groq_key, body, "Groq")
    except GroqError as e:
        logger.warning(f"Groq недоступен ({e}), переключаемся на OpenRouter...")
        # Продолжаем выполнение, чтобы попробовать OpenRouter

    # --- 2. Пробуем OpenRouter (fallback) ---
    openrouter_key = _get_openrouter_key()
    if not openrouter_key:
        raise GroqError(
            "Groq недоступен, а OPENROUTER_API_KEY не задан. "
            "Добавь ключ в .env для fallback."
        )

    # Для OpenRouter используем свою модель
    body["model"] = OPENROUTER_MODEL
    # Убираем reasoning_effort, если OpenRouter его не поддерживает (обычно не поддерживает)
    body.pop("reasoning_effort", None)
    body.pop("reasoning_format", None)

    logger.info(f"Fallback на OpenRouter (model={OPENROUTER_MODEL})")
    return await _call_openai_compatible(OPENROUTER_URL, openrouter_key, body, "OpenRouter")