"""
facebook_client.py — Xử lý kết nối Facebook qua fbchat_muqit.
Thư viện này là ASYNC hoàn toàn và dùng COOKIES để xác thực (không hỗ trợ email/password).
"""

from __future__ import annotations

import asyncio

import fbchat_muqit as fb
from fbchat_muqit import Client, Message, ThreadType, EventType

import config
import logger
import ai_handler


class FacebookBot(Client):
    """
    Kế thừa fbchat_muqit.Client.
    Override on_message để xử lý tin nhắn đến.
    """

    async def on_message(self, event_data: Message) -> None:
        """
        Được gọi mỗi khi có tin nhắn mới.
        Bot chỉ phản hồi nếu:
        - Không phải tin nhắn của chính mình.
        - Group: thread phải nằm trong GROUP_IDS (nếu config) VÀ có @mention BOT_NAME.
        - DM: sender phải nằm trong ALLOWED_USER_IDS (nếu config).
        """
        # Bỏ qua tin nhắn của chính bot
        if str(event_data.sender_id) == str(self.uid):
            return

        text: str = (event_data.text or "").strip()
        thread_id: str = str(event_data.thread_id)
        sender_id: str = str(event_data.sender_id)
        thread_type: ThreadType = event_data.thread_type

        # ── Xử lý tin nhắn nhóm (GROUP) ────────────────────────────────────
        if thread_type == ThreadType.GROUP:
            if not self._is_allowed_group(thread_id):
                return
            if not self._is_mentioned(text):
                return
            question = self._strip_mention(text)
            context_key = f"group_{thread_id}"

        # ── Xử lý DM (nhắn riêng) ──────────────────────────────────────────
        elif thread_type == ThreadType.USER:
            if config.ALLOWED_USER_IDS and sender_id not in [
                str(uid) for uid in config.ALLOWED_USER_IDS
            ]:
                return
            question = text
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

    def _is_mentioned(self, text: str) -> bool:
        """Kiểm tra tin nhắn có @mention tên bot không."""
        return config.BOT_NAME.lower() in text.lower()

    def _strip_mention(self, text: str) -> str:
        """Loại bỏ @mention khỏi chuỗi và trim."""
        return text.lower().replace(config.BOT_NAME.lower(), "").strip()

    async def on_listening(self) -> None:
        """Được gọi khi bot bắt đầu lắng nghe."""
        await logger.log_info(
            f"✅ {config.BOT_NAME} đang lắng nghe tin nhắn!\n"
            f"   Bot UID: {self.uid} | Tên: {self.name}\n"
            f"   Groups: {config.GROUP_IDS or 'Tất cả'}\n"
            f"   Trigger: {config.BOT_NAME}"
        )


async def create_and_listen() -> None:
    """
    Tạo bot, đăng nhập bằng cookies và bắt đầu lắng nghe.
    Thư viện fbchat_muqit chỉ hỗ trợ đăng nhập qua cookies.json.

    Raises:
        FileNotFoundError: nếu cookies.json không tồn tại hoặc rỗng.
        Exception: các lỗi kết nối / xác thực khác.
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
