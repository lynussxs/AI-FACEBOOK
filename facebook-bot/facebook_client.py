"""
facebook_client.py — Xử lý login Facebook, load/save cookies,
lắng nghe tin nhắn và gửi phản hồi.
Sử dụng thư viện fbchat-muqit (fork fbchat tốt nhất hiện nay).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

# fbchat-muqit cung cấp API đồng bộ; ta wrap bằng asyncio.to_thread
try:
    import fbchat
    from fbchat import Client, Message, ThreadType
except ImportError as exc:
    raise ImportError(
        "Cài fbchat-muqit: pip install fbchat-muqit"
    ) from exc

import config
import logger
import ai_handler


class FacebookBot(Client):
    """
    Kế thừa fbchat.Client để override các callback lắng nghe sự kiện.
    """

    def __init__(self):
        super().__init__()
        self._bot_uid: str | None = None  # UID của bot sau khi login

    # ──────────────────────────────────────────────────────────────────────────
    # Callback: nhận tin nhắn mới
    # ──────────────────────────────────────────────────────────────────────────
    def onMessage(
        self,
        author_id: str = None,
        message_object: Message = None,
        thread_id: str = None,
        thread_type: ThreadType = None,
        **kwargs,
    ):
        """
        Được gọi mỗi khi có tin nhắn mới.
        Bot chỉ xử lý nếu:
        - Không phải tin nhắn của chính mình.
        - Là group được config (thread_type == GROUP).
        - Tin nhắn có @mention BOT_NAME, HOẶC là DM từ user được phép.
        """
        # Bỏ qua tin nhắn của chính bot
        if author_id == self.uid:
            return

        text: str = (message_object.text or "").strip()

        # Xử lý tin nhắn nhóm
        if thread_type == ThreadType.GROUP:
            if not self._is_allowed_group(thread_id):
                return
            if not self._is_mentioned(text):
                return
            # Loại bỏ phần @mention khỏi câu hỏi
            question = self._strip_mention(text)
        # Xử lý DM (nhắn riêng)
        elif thread_type == ThreadType.USER:
            if config.ALLOWED_USER_IDS and author_id not in config.ALLOWED_USER_IDS:
                return
            question = text
            thread_id = f"dm_{author_id}"
        else:
            return

        if not question:
            return

        # Lấy tên người gửi
        sender_name = self._get_user_name(author_id)

        # Chạy async từ sync context (fbchat callback là sync)
        asyncio.run(
            self._handle_message(
                author_id=author_id,
                sender_name=sender_name,
                question=question,
                thread_id=thread_id,
                original_thread_id=thread_id if thread_type == ThreadType.GROUP else None,
                thread_type=thread_type,
            )
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Xử lý tin nhắn: gọi AI rồi gửi phản hồi
    # ──────────────────────────────────────────────────────────────────────────
    async def _handle_message(
        self,
        author_id: str,
        sender_name: str,
        question: str,
        thread_id: str,
        original_thread_id: str | None,
        thread_type: ThreadType,
    ):
        try:
            # Gọi OpenRouter lấy câu trả lời
            answer = await ai_handler.get_ai_response(
                thread_id=thread_id,
                user_message=question,
            )

            # Gửi câu trả lời về Facebook (sync, chạy trong thread pool)
            await asyncio.to_thread(
                self.send,
                Message(text=answer),
                thread_id=original_thread_id or author_id,
                thread_type=thread_type if original_thread_id else ThreadType.USER,
            )

            # Log thành công
            await logger.log_success(
                sender_name=sender_name,
                sender_id=author_id,
                question=question,
                answer=answer,
                group_id=original_thread_id,
            )

        except Exception as exc:  # noqa: BLE001
            await logger.log_error(
                context=f"Xử lý tin nhắn từ {sender_name} ({author_id})",
                exc=exc,
                extra=f"Câu hỏi: {question[:200]}",
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────
    def _is_allowed_group(self, thread_id: str) -> bool:
        """Kiểm tra group có trong danh sách được phép không."""
        if not config.GROUP_IDS:
            return True  # Nếu không config → cho phép tất cả
        return str(thread_id) in [str(g) for g in config.GROUP_IDS]

    def _is_mentioned(self, text: str) -> bool:
        """Kiểm tra tin nhắn có @mention tên bot không."""
        return config.BOT_NAME.lower() in text.lower()

    def _strip_mention(self, text: str) -> str:
        """Loại bỏ @mention khỏi chuỗi và trim."""
        return text.lower().replace(config.BOT_NAME.lower(), "").strip()

    def _get_user_name(self, user_id: str) -> str:
        """Lấy tên người dùng từ Facebook (fallback về ID nếu lỗi)."""
        try:
            user_info = self.fetchUserInfo(user_id)
            if user_info and user_id in user_info:
                return user_info[user_id].name
        except Exception:  # noqa: BLE001
            pass
        return f"User({user_id})"

    def onError(self, exception, **kwargs):
        """Callback khi có lỗi từ fbchat."""
        asyncio.run(
            logger.log_error(
                context="fbchat internal error",
                exc=exception,
            )
        )


# ─── Login / Cookie management ─────────────────────────────────────────────────

def _load_cookies() -> dict | None:
    """Đọc cookies từ file nếu tồn tại và không rỗng."""
    path = Path(config.COOKIES_FILE)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _save_cookies(client: FacebookBot) -> None:
    """Lưu session cookies hiện tại vào file."""
    try:
        cookies = client.getSession()
        Path(config.COOKIES_FILE).write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        asyncio.run(logger.log_error("Lưu cookies thất bại", exc))


def create_and_login() -> FacebookBot:
    """
    Tạo FacebookBot instance và đăng nhập.
    - Nếu có cookies.json hợp lệ → đăng nhập bằng cookies.
    - Nếu không → đăng nhập email/password rồi save cookies.
    """
    bot = FacebookBot()

    cookies = _load_cookies()
    if cookies:
        try:
            bot.setSession(cookies)
            asyncio.run(logger.log_info("✅ Đăng nhập bằng cookies thành công."))
            return bot
        except fbchat.FBchatException as exc:
            asyncio.run(
                logger.log_error(
                    "Cookies hết hạn hoặc không hợp lệ, thử email/password…",
                    exc,
                )
            )

    # Đăng nhập bằng email + password
    bot.login(config.FACEBOOK_EMAIL, config.FACEBOOK_PASSWORD)
    asyncio.run(logger.log_info("✅ Đăng nhập bằng email/password thành công."))

    # Lưu cookies để lần sau dùng lại
    _save_cookies(bot)
    asyncio.run(logger.log_info("💾 Cookies đã được lưu vào " + config.COOKIES_FILE))

    return bot
