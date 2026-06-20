"""
config.py — Load và quản lý tất cả biến cấu hình từ file .env
Lưu ý: fbchat_muqit chỉ hỗ trợ xác thực qua cookies.json (không dùng email/password).
"""

import os
import json
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()


def _parse_list(value: str, default: list = None) -> list:
    """Parse chuỗi JSON hoặc chuỗi phân cách bằng dấu phẩy thành list."""
    if not value:
        return default or []
    value = value.strip()
    if value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return [item.strip() for item in value.split(",") if item.strip()]


# ─── Facebook (cookies-only auth) ──────────────────────────────────────────────
COOKIES_FILE: str = os.getenv("COOKIES_FILE", "cookies.json")

# ─── OpenRouter ────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME: str = os.getenv("MODEL_NAME", "google/gemini-flash-1.5")
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    (
        "Bạn là một AI thông minh và thân thiện. "
        "Hãy trả lời bằng tiếng Việt, ngắn gọn và hữu ích."
    ),
)
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1000"))
MAX_CONTEXT_MESSAGES: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "10"))

# ─── Bot ───────────────────────────────────────────────────────────────────────
BOT_NAME: str = os.getenv("BOT_NAME", "@MyAI")

# Danh sách Group ID được phép (chuỗi hoặc JSON array)
GROUP_IDS: list[str] = _parse_list(os.getenv("GROUP_IDS", "[]"))

# Danh sách User ID được phép nhắn riêng (optional)
ALLOWED_USER_IDS: list[str] = _parse_list(os.getenv("ALLOWED_USER_IDS", "[]"))

# ─── Discord ───────────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

# ─── Reconnect ─────────────────────────────────────────────────────────────────
RECONNECT_DELAY: int = int(os.getenv("RECONNECT_DELAY", "10"))   # giây
MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "0"))  # 0 = vô hạn


def validate():
    """Kiểm tra các biến bắt buộc đã được set chưa."""
    errors = []
    if not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY chưa được set")
    if errors:
        raise EnvironmentError(
            "Thiếu biến cấu hình bắt buộc:\n" + "\n".join(f"  - {e}" for e in errors)
        )
