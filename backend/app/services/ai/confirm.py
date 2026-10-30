# backend/app/services/ai/confirm.py
"""
Хранилище отложенных write-действий (preview → confirm).
Redis: ключ `ai_action:{action_id}` → JSON {tool, args, preview, message, created_at}
TTL 10 минут.
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
TTL_SECONDS = 600  # 10 минут
KEY_PREFIX = "ai_action:"

_redis_client: Optional[aioredis.Redis] = None


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


def _key(action_id: str) -> str:
    return f"{KEY_PREFIX}{action_id}"


async def save_action(
    tool: str,
    args: Dict[str, Any],
    preview: Dict[str, Any],
    message: str,
) -> str:
    """
    Сохраняет отложенное действие. Возвращает action_id.
    """
    action_id = str(uuid.uuid4())
    payload = {
        "action_id": action_id,
        "tool": tool,
        "args": args,
        "preview": preview,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    r = _get_redis()
    await r.set(_key(action_id), json.dumps(payload, ensure_ascii=False), ex=TTL_SECONDS)
    logger.info(f"AI action saved: {action_id} ({tool}), ttl={TTL_SECONDS}s")
    return action_id


async def get_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Возвращает dict действия или None (истёк / не найден)."""
    r = _get_redis()
    raw = await r.get(_key(action_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"AI action {action_id}: invalid JSON in Redis")
        return None


async def delete_action(action_id: str) -> bool:
    """Удаляет действие. True — если было, False — если уже не было."""
    r = _get_redis()
    deleted = await r.delete(_key(action_id))
    return deleted > 0


async def ping() -> bool:
    """Проверка доступности Redis (для health)."""
    try:
        r = _get_redis()
        return bool(await r.ping())
    except Exception as e:
        logger.error(f"Redis ping failed: {e}")
        return False