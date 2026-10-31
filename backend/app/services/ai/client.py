# backend/app/services/ai/client.py
"""
Обёртка над Groq API (OpenAI-совместимый /chat/completions).
- async httpx
- timeout 30s
- retry на 429 / 500 / 502 / 503 (max 2 повтора, backoff 3s, 6s)
- логирование usage (prompt/completion/total tokens)
"""

import asyncio
import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Модель: можно переопределить через env GROQ_MODEL
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TIMEOUT = 30.0
MAX_RETRIES = 2
RETRY_BACKOFF = [3.0, 6.0]  # секунды между повторами
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GroqError(Exception):
    """Ошибка вызова Groq."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise GroqError("GROQ_API_KEY не задан в окружении backend")
    return key


async def groq_chat(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 800,
    reasoning_effort: Optional[str] = "low",
) -> Dict[str, Any]:
    """
    Один вызов Groq /chat/completions.
    Возвращает полный dict ответа (choices, usage).
    Бросает GroqError при фатальных ошибках.
    """
    api_key = _get_api_key()

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
        body["reasoning_format"] = "hidden"  # попытка скрыть reasoning

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; VEDProcessor/1.0)",
    }

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(GROQ_URL, json=body, headers=headers)

            if resp.status_code in RETRYABLE_STATUS:
                snippet = resp.text[:300]
                logger.warning(
                    f"Groq {resp.status_code} (attempt {attempt+1}/{MAX_RETRIES+1}): {snippet}"
                )
                last_error = GroqError(
                    f"Groq вернул {resp.status_code}: {snippet}",
                    status_code=resp.status_code,
                )
                
                # --- Если 429 (лимит токенов) — не ждем и не ретраим, отдаем красивую ошибку ---
                if resp.status_code == 429:
                    raise GroqError("Закипели мозги! 🧠🔥 Подожди минуту.", status_code=429)
                # ------------------------------------------------------------------------------

                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
                    continue
                raise last_error

            if resp.status_code >= 400:
                # 400 / 401 / 403 / 404 — не retry
                snippet = resp.text[:500]
                raise GroqError(
                    f"Groq вернул {resp.status_code}: {snippet}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            usage = data.get("usage", {})
            logger.info(
                f"Groq OK: model={model}, "
                f"prompt={usage.get('prompt_tokens')}, "
                f"completion={usage.get('completion_tokens')}, "
                f"total={usage.get('total_tokens')}, "
                f"queue={usage.get('queue_time')}"
            )
            return data

        except httpx.TimeoutException as e:
            last_error = GroqError(f"Groq timeout ({TIMEOUT}s): {e}")
            logger.warning(f"Groq timeout (attempt {attempt+1}/{MAX_RETRIES+1})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            raise last_error

        except httpx.RequestError as e:
            last_error = GroqError(f"Groq network error: {e}")
            logger.warning(f"Groq network error (attempt {attempt+1}/{MAX_RETRIES+1}): {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            raise last_error

    raise last_error or GroqError("Groq: неизвестная ошибка")