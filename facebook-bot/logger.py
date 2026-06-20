"""
logger.py — Gửi log thành công và lỗi về Discord Webhook + in ra console.
"""

import traceback
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


def _safe_str(value: str | None, default: str = "(trống)", max_len: int = 1000) -> str:
    """Đảm bảo chuỗi không rỗng và không vượt quá max_len ký tự."""
    text = (value or "").strip()
    if not text:
        return default
    return text[:max_len] + ("…" if len(text) > max_len else "")


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
                    body = await resp.text()
                    _log.warning(
                        "Discord webhook trả về status %s: %s", resp.status, body[:300]
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

    # Đảm bảo giá trị không rỗng (Discord báo 400 nếu field value trống)
    safe_name = _safe_str(sender_name, default=f"User({sender_id})", max_len=100)
    safe_q = _safe_str(question, default="(không có nội dung)", max_len=500)
    safe_a = _safe_str(answer, default="(không có câu trả lời)", max_len=800)

    _log.info(
        "✅ [%s] %s → %s | %s",
        group_info,
        safe_name,
        safe_q,
        safe_a,
    )

    embed = {
        "embeds": [
            {
                "title": "✅ Bot đã trả lời",
                "color": 0x2ECC71,  # số nguyên hex — xanh lá
                "fields": [
                    {
                        "name": "👤 Người gửi",
                        "value": f"{safe_name} (`{sender_id}`)",
                        "inline": True,
                    },
                    {
                        "name": "📍 Group",
                        "value": group_info,
                        "inline": True,
                    },
                    {
                        "name": "❓ Câu hỏi",
                        "value": f"```{safe_q}```",
                        "inline": False,
                    },
                    {
                        "name": "💬 Câu trả lời",
                        "value": f"```{safe_a}```",
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

    # Xây dựng description, đảm bảo không có trường nào rỗng
    safe_context = _safe_str(context, default="Lỗi không xác định", max_len=200)
    desc_parts = [f"**Context:** {safe_context}"]

    if exc:
        exc_str = _safe_str(f"{type(exc).__name__}: {exc}", max_len=300)
        desc_parts.append(f"**Lỗi:** `{exc_str}`")

    if extra:
        safe_extra = _safe_str(extra, max_len=300)
        desc_parts.append(f"**Thêm:** {safe_extra}")

    if tb:
        tb_short = _safe_str(tb[-1200:], max_len=1200)
        desc_parts.append(f"**Traceback:**\n```\n{tb_short}\n```")

    description = "\n".join(desc_parts)
    # Discord giới hạn description 4096 ký tự
    if len(description) > 4000:
        description = description[:4000] + "\n…(cắt bớt)"

    embed = {
        "embeds": [
            {
                "title": "❌ Bot gặp lỗi",
                "description": description,
                "color": 0xE74C3C,  # số nguyên hex — đỏ
                "footer": {"text": f"🕒 {_now()}"},
            }
        ]
    }
    await _send_discord(embed)


async def log_info(message: str) -> None:
    """Log thông tin chung (startup, reconnect, v.v.)."""
    _log.info("ℹ️  %s", message)

    safe_msg = _safe_str(message, default="(thông báo trống)", max_len=2000)
    embed = {
        "embeds": [
            {
                "title": "ℹ️ Thông báo Bot",
                "description": safe_msg,
                "color": 0x3498DB,  # số nguyên hex — xanh dương
                "footer": {"text": f"🕒 {_now()}"},
            }
        ]
    }
    await _send_discord(embed)
