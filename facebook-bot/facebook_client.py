"""
facebook_client.py — Xử lý kết nối Facebook qua fbchat_muqit.
Thư viện này là ASYNC hoàn toàn và dùng COOKIES để xác thực (không hỗ trợ email/password).
"""

from __future__ import annotations

import asyncio

import fbchat_muqit as fb
from fbchat_muqit import Client, Message, ThreadType

import config
import logger
import ai_handler


class FacebookBot(Client):
    """
    Kế thừa fbchat_muqit.Client.
    Override on_message để xử lý tin nhắn đến.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bot_display_name: str = ""  # Tên thật của bot, load sau khi login

    async def _get_bot_display_name(self) -> str:
        """Lấy tên thật của bot (dùng để detect mention)."""
        if self._bot_display_name:
            return self._bot_display_name
        try:
            # self.name đã có sau khi __aenter__ chạy
            if self.name:
                self._bot_display_name = self.name
                return self._bot_display_name
        except Exception:
            pass
        return ""

    async def on_message(self, event_data: Message) -> None:
        """
        Được gọi mỗi khi có tin nhắn mới.
        Bot chỉ phản hồi nếu:
        - Không phải tin nhắn của chính mình.
        - Group: thread phải nằm trong GROUP_IDS (nếu config) VÀ có @mention.
        - DM: sender phải nằm trong ALLOWED_USER_IDS (nếu config).
        """
        # Bỏ qua tin nhắn của chính bot
        if str(event_data.sender_id) == str(self.uid):
            return

        raw_text: str = (event_data.text or "").strip()
        thread_id: str = str(event_data.thread_id)
        sender_id: str = str(event_data.sender_id)
        thread_type: ThreadType = event_data.thread_type

        # ── Xử lý tin nhắn nhóm (GROUP) ────────────────────────────────────
        if thread_type == ThreadType.GROUP:
            if not self._is_allowed_group(thread_id):
                return

            # In log để debug
            print(f"Nhận tin nhắn: {raw_text}")

            if not await self._is_mentioned(raw_text):
                return

            question = self._strip_mention(raw_text)
            context_key = f"group_{thread_id}"

        # ── Xử lý DM (nhắn riêng) ──────────────────────────────────────────
        elif thread_type == ThreadType.USER:
            print(f"Nhận tin nhắn DM: {raw_text}")
            if config.ALLOWED_USER_IDS and sender_id not in [
                str(uid) for uid in config.ALLOWED_USER_IDS
            ]:
                return
            question = raw_text
            context_key = f"dm_{sender_id}"

        else:
            return

        if not question:
            return

        # Gọi AI và gửi phản hồi
        await self._respond(
            sender_id=sender_id,
            question=question,
            thread_id=thread_id,
            context_key=context_key,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Gọi AI → gửi phản hồi
    # ──────────────────────────────────────────────────────────────────────────
    async def _respond(
        self,
        sender_id: str,
        question: str,
        thread_id: str,
        context_key: str,
    ) -> None:
        try:
            answer = await ai_handler.get_ai_response(
                thread_id=context_key,
                user_message=question,
            )

            # Gửi tin nhắn phản hồi
            await self.send_message(text=answer, thread_id=thread_id)

            # Log thành công
            await logger.log_success(
                sender_name=sender_id,
                sender_id=sender_id,
                question=question,
                answer=answer,
                group_id=thread_id if context_key.startswith("group_") else None,
            )

        except Exception as exc:  # noqa: BLE001
            await logger.log_error(
                context=f"Xử lý tin nhắn từ user {sender_id}",
                exc=exc,
                extra=f"Câu hỏi: {question[:200]}",
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────
    def _is_allowed_group(self, thread_id: str) -> bool:
        """Kiểm tra group có trong danh sách được phép không."""
        if not config.GROUP_IDS:
            return True  # Không config → cho phép tất cả group
        return thread_id in [str(g) for g in config.GROUP_IDS]

    async def _is_mentioned(self, text: str) -> bool:
        """
        Kiểm tra tin nhắn có nhắc đến bot không, dựa trên:
        - BOT_NAME trong config (ví dụ: '@MyAI')
        - Tên thật của bot trên Facebook (self.name)
        """
        text_lower = text.lower()

        # Check theo BOT_NAME config
        if config.BOT_NAME.lower() in text_lower:
            return True

        # Check theo tên thật của bot
        bot_display = await self._get_bot_display_name()
        if bot_display and bot_display.lower() in text_lower:
            return True

        return False

    def _strip_mention(self, text: str) -> str:
        """Loại bỏ BOT_NAME và tên bot khỏi chuỗi, trả về câu hỏi sạch."""
        result = text
        result = result.replace(config.BOT_NAME, "").replace(config.BOT_NAME.lower(), "")
        if self._bot_display_name:
            result = result.replace(self._bot_display_name, "").replace(
                self._bot_display_name.lower(), ""
            )
        return result.strip()

    async def on_listening(self) -> None:
        """Được gọi khi bot bắt đầu lắng nghe."""
        # Load tên thật của bot ngay khi bắt đầu listen
        await self._get_bot_display_name()
        await logger.log_info(
            f"✅ {config.BOT_NAME} đang lắng nghe tin nhắn!\n"
            f"   Bot UID: {self.uid} | Tên thật: {self.name}\n"
            f"   Groups: {config.GROUP_IDS or 'Tất cả'}\n"
            f"   Trigger: '{config.BOT_NAME}' hoặc '{self.name}'"
        )


async def create_and_listen() -> None:
    """
    Tạo bot, đăng nhập bằng cookies và bắt đầu lắng nghe.
    Thư viện fbchat_muqit chỉ hỗ trợ đăng nhập qua cookies.json.
    """
    import json
    from pathlib import Path

    # Kiểm tra cookies.json có dữ liệu không
    cookies_path = Path(config.COOKIES_FILE)
    if not cookies_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy '{config.COOKIES_FILE}'. "
            "Hãy export cookies Facebook và lưu vào file này. "
            "Xem README.md để biết cách làm."
        )

    try:
        cookies_data = json.loads(cookies_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"'{config.COOKIES_FILE}' không phải JSON hợp lệ: {exc}") from exc

    if not cookies_data:
        raise ValueError(
            f"'{config.COOKIES_FILE}' đang rỗng. "
            "Hãy export cookies Facebook thật và điền vào file này."
        )

    # Tạo bot và đăng nhập
    async with FacebookBot(cookies_file_path=config.COOKIES_FILE) as bot:
        await bot.listen()
