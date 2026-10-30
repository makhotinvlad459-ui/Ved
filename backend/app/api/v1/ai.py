# backend/app/api/v1/ai.py
"""
AI-ассистент: POST /api/v1/ai/command, /ai/confirm, /ai/cancel
Цикл tool calling (max 5 итераций).
Read-tools выполняются сразу.
Write-tools → preview → save_action в Redis → ответ confirmation.
Confirm → execute_write_tool → ответ result.
"""

import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    AICommandRequest, AICommandResponse,
    AIConfirmRequest, AIConfirmResponse,
)
from app.services.ai.client import groq_chat, GroqError
from app.services.ai.prompts import SYSTEM_PROMPT
from app.services.ai.tools import TOOLS, WRITE_TOOLS
from app.services.ai.executor import execute_tool, execute_write_tool, ToolError
from app.services.ai import confirm as ai_confirm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

MAX_ITERATIONS = 5


@router.post("/command", response_model=AICommandResponse)
async def ai_command(
    data: AICommandRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Принимает текстовый запрос, прогоняет через цикл tool calling.
    - Read-tools выполняются сразу.
    - Write-tool → preview + save_action → возвращает confirmation.
    """
    text = (data.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Пустой запрос")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Слишком длинный запрос (>2000)")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    tools_used: List[str] = []

    for iteration in range(MAX_ITERATIONS):
        try:
            resp = await groq_chat(messages=messages, tools=TOOLS)
        except GroqError as e:
            logger.error(f"Groq error on iteration {iteration}: {e}")
            return AICommandResponse(
                type="error",
                text=f"AI недоступен: {e}",
            )

        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content")

        # === Нет tool_calls — финальный ответ ===
        if not tool_calls:
            return AICommandResponse(
                type="answer",
                text=(content or "").strip() or "Готово.",
                tools_used=tools_used,
            )

        # === Есть tool_calls ===
        # Добавляем assistant-сообщение с tool_calls в историю
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                fn_args = {}

            tools_used.append(fn_name)

            # === WRITE-TOOL: preview → save_action → return confirmation ===
            if fn_name in WRITE_TOOLS:
                try:
                    preview_result = await execute_tool(db, fn_name, fn_args)
                except ToolError as e:
                    # Ошибку возвращаем модели — она озвучит
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps({"error": str(e)}, ensure_ascii=False),
                    })
                    continue

                if "error" in preview_result:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(preview_result, ensure_ascii=False),
                    })
                    continue

                action_id = await ai_confirm.save_action(
                    tool=fn_name,
                    args=preview_result["action"]["args"],
                    preview=preview_result["preview"],
                    message=preview_result.get("message", ""),
                )

                return AICommandResponse(
                    type="confirmation",
                    text=preview_result.get("message", ""),
                    action_id=action_id,
                    preview=preview_result["preview"],
                    tools_used=tools_used,
                )

            # === READ-TOOL: выполняем сразу ===
            try:
                result = await execute_tool(db, fn_name, fn_args)
            except ToolError as e:
                result = {"error": str(e)}

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

    # Не сошлись за MAX_ITERATIONS
    return AICommandResponse(
        type="error",
        text="Слишком много шагов. Уточни запрос.",
        tools_used=tools_used,
    )


@router.post("/confirm", response_model=AIConfirmResponse)
async def ai_confirm_endpoint(
    data: AIConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """Подтверждение или отмена отложенного write-действия."""
    action = await ai_confirm.get_action(data.action_id)
    if not action:
        return AIConfirmResponse(
            type="error",
            text="Действие не найдено или истекло (TTL 10 мин). Повтори запрос.",
        )

    # === Отмена ===
    if not data.approved:
        await ai_confirm.delete_action(data.action_id)
        return AIConfirmResponse(
            type="cancelled",
            text="Действие отменено.",
        )

    # === Подтверждение — выполняем ===
    try:
        result = await execute_write_tool(
            db,
            action["tool"],
            action["args"],
        )
    except ToolError as e:
        await ai_confirm.delete_action(data.action_id)
        return AIConfirmResponse(
            type="error",
            text=f"Ошибка выполнения: {e}",
        )
    except Exception as e:
        logger.exception(f"AI confirm failed: {e}")
        await ai_confirm.delete_action(data.action_id)
        return AIConfirmResponse(
            type="error",
            text=f"Внутренняя ошибка: {e}",
        )

    # Удаляем action после успешного выполнения
    await ai_confirm.delete_action(data.action_id)

    # Формируем человекочитаемый текст
    tool = action["tool"]
    if tool == "update_product_weight":
        n = result.get("updated_count", 0)
        w = result.get("new_weight")
        text = f"Обновлено {n} товаров. Новый вес: {w} кг."
    elif tool == "update_product_category":
        n = result.get("updated_count", 0)
        cat = result.get("category_name")
        text = f"Назначена категория '{cat}' для {n} товаров."
    elif tool == "create_category":
        text = f"Категория '{result.get('name')}' создана (id={result.get('category_id')})."
    elif tool == "create_products":
        n = result.get("created_count", 0)
        text = f"Создано {n} товаров."
    else:
        text = "Готово."

    return AIConfirmResponse(
        type="result",
        text=text,
        result=result,
    )


@router.post("/cancel", response_model=AIConfirmResponse)
async def ai_cancel(
    data: AIConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """Отмена без выполнения (аналог confirm с approved=false)."""
    await ai_confirm.delete_action(data.action_id)
    return AIConfirmResponse(
        type="cancelled",
        text="Действие отменено.",
    )