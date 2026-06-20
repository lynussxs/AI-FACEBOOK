"""
ai_handler.py — Gọi OpenRouter API để tạo câu trả lời AI.
Hỗ trợ lưu context hội thoại theo từng thread (group hoặc DM).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Deque

import aiohttp

import config
import logger

# ─── Endpoint ──────────────────────────────────────────────────────────────────
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ─── Lưu lịch sử hội thoại: thread_id → deque of {"role": ..., "content": ...}
_history: dict[str, Deque[dict]] = defaultdict(
    lambda: deque(maxlen=config.MAX_CONTEXT_MESSAGES * 2)
)


def _build_messages(thread_id: str, user_message: str) -> list[dict]:
    """
    Xây dựng danh sách messages gửi đến API:
    system prompt + lịch sử + tin nhắn mới nhất.
    """
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
    messages.extend(list(_history[thread_id]))
    messages.append({"role": "user", "content": user_message})
    return messages


def add_to_history(thread_id: str, role: str, content: str) -> None:
    """Thêm tin nhắn vào lịch sử context của thread."""
    _history[thread_id].append({"role": role, "content": content})


def clear_history(thread_id: str) -> None:
    """Xoá lịch sử context của một thread."""
    if thread_id in _history:
        del _history[thread_id]


async def get_ai_response(thread_id: str, user_message: str) -> str:
    """
    Gọi OpenRouter API và trả về câu trả lời.
    Tự động lưu tin nhắn của user và AI vào history.

    Raises:
        RuntimeError: nếu API trả lỗi hoặc network lỗi.
    """
    messages = _build_messages(thread_id, user_message)

    payload = {
        "model": config.MODEL_NAME,
        "messages": messages,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
    }

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/facebook-ai-bot",
        "X-Title": config.BOT_NAME,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            OPENROUTER_URL,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            data = await resp.json()

            # Kiểm tra lỗi từ API
            if resp.status != 200:
                error_msg = data.get("error", {}).get("message", str(data))
                raise RuntimeError(
                    f"OpenRouter API lỗi {resp.status}: {error_msg}"
                )

            # Trích xuất câu trả lời
            try:
                answer = data["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError) as exc:
                raise RuntimeError(
                    f"Cấu trúc response không hợp lệ: {data}"
                ) from exc

    # Lưu vào lịch sử sau khi thành công
    add_to_history(thread_id, "user", user_message)
    add_to_history(thread_id, "assistant", answer)

    return answer
