"""
logger.py — Gửi log thành công và lỗi về Discord Webhook + in ra console.
"""

import traceback
import asyncio
import logging
from datetime import datetime

import aiohttp

import config

# Cấu hình logging cơ bản ra console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("facebook_bot")


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


async def _send_discord(payload: dict) -> None:
    """Gửi embed payload lên Discord Webhook (không raise nếu lỗi)."""
    if not config.DISCORD_WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status not in (200, 204):
                    _log.warning(
                        "Discord webhook trả về status %s", resp.status
                    )
    except Exception as exc:  # noqa: BLE001
        _log.warning("Không gửi được Discord webhook: %s", exc)


async def log_success(
    sender_name: str,
    sender_id: str,
    question: str,
    answer: str,
    group_id: str | None = None,
) -> None:
    """
    Log thành công: người gửi, câu hỏi, câu trả lời, group, thời gian.
    """
    group_info = f"`{group_id}`" if group_id else "DM (nhắn riêng)"
    short_q = question[:300] + ("…" if len(question) > 300 else "")
    short_a = answer[:500] + ("…" if len(answer) > 500 else "")

    _log.info(
        "✅ [%s] %s (%s) → %s | %s",
        group_info,
        sender_name,
        sender_id,
        short_q,
        short_a,
    )

    embed = {
        "embeds": [
            {
                "title": "✅ Bot đã trả lời",
                "color": 0x2ECC71,
                "fields": [
                    {
                        "name": "👤 Người gửi",
                        "value": f"{sender_name} (`{sender_id}`)",
                        "inline": True,
                    },
                    {
                        "name": "📍 Group",
                        "value": group_info,
                        "inline": True,
                    },
                    {
                        "name": "❓ Câu hỏi",
                        "value": f"```{short_q}```",
                        "inline": False,
                    },
                    {
                        "name": "💬 Câu trả lời",
                        "value": f"```{short_a}```",
                        "inline": False,
                    },
                ],
                "footer": {"text": f"🕒 {_now()}"},
            }
        ]
    }
    await _send_discord(embed)


async def log_error(
    context: str,
    exc: BaseException | None = None,
    extra: str | None = None,
) -> None:
    """
    Log lỗi: context mô tả, exception, traceback.
    """
    tb = ""
    if exc is not None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    _log.error("❌ %s | %s | %s", context, exc, extra or "")
    if tb:
        _log.error(tb)

    desc_parts = [f"**Context:** {context}"]
    if exc:
        desc_parts.append(f"**Lỗi:** `{type(exc).__name__}: {exc}`")
    if extra:
        desc_parts.append(f"**Thêm:** {extra}")
    if tb:
        tb_short = tb[-1500:]
        desc_parts.append(f"**Traceback:**\n```\n{tb_short}\n```")

    embed = {
        "embeds": [
            {
                "title": "❌ Bot gặp lỗi",
                "description": "\n".join(desc_parts),
                "color": 0xE74C3C,
                "footer": {"text": f"🕒 {_now()}"},
            }
        ]
    }
    await _send_discord(embed)


async def log_info(message: str) -> None:
    """Log thông tin chung (startup, reconnect, v.v.)."""
    _log.info("ℹ️  %s", message)
    embed = {
        "embeds": [
            {
                "title": "ℹ️ Thông báo Bot",
                "description": message,
                "color": 0x3498DB,
                "footer": {"text": f"🕒 {_now()}"},
            }
        ]
    }
    await _send_discord(embed)
