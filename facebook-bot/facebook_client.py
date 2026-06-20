"""
facebook_client.py — Kết nối Facebook qua fbchat_muqit (async, cookies-only).
Hỗ trợ trigger bằng BOT_NAME config, tên thật và biệt danh (nickname) trong group.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import fbchat_muqit as fb
from fbchat_muqit import Client, Message, ThreadType

import config
import logger
import ai_handler


# ─── Helpers hiển thị console ──────────────────────────────────────────────────

def _ts() -> str:
    """Timestamp ngắn gọn HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def _log(source: str, body: str) -> None:
    """In log chuẩn: [HH:MM:SS] [SOURCE] body"""
    print(f"[{_ts()}] [{source}] {body}")


# ─── Bot class ─────────────────────────────────────────────────────────────────

class FacebookBot(Client):
    """
    Kế thừa fbchat_muqit.Client.
    - Trigger theo BOT_NAME, tên thật và nickname trong từng group.
    - Nickname được cache per-thread để giảm API call.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Cache nickname của bot trong từng group: {thread_id: nickname | None}
        self._nickname_cache: dict[str, str | None] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Lấy nickname của bot trong group (có cache)
    # ──────────────────────────────────────────────────────────────────────────
    async def _get_bot_nickname(self, thread_id: str) -> str | None:
        """
        Lấy biệt danh (nickname) hiện tại của bot trong group thread_id.
        Kết quả được cache — chỉ gọi API lần đầu hoặc khi cache bị xoá.
        """
        if thread_id in self._nickname_cache:
            return self._nickname_cache[thread_id]

        try:
            threads = await self.fetch_thread_info([thread_id])
            if threads:
                thread = threads[0]
                nicknames: dict | None = thread.participants_nickname
                nick = (nicknames or {}).get(str(self.uid))
                self._nickname_cache[thread_id] = nick
                return nick
        except Exception as exc:
            _log("WARN", f"Không lấy được nickname group {thread_id}: {exc}")

        self._nickname_cache[thread_id] = None
        return None

    def invalidate_nickname_cache(self, thread_id: str) -> None:
        """Xoá cache nickname của group (dùng khi nickname bị đổi)."""
        self._nickname_cache.pop(thread_id, None)

    # ──────────────────────────────────────────────────────────────────────────
    # Kiểm tra trigger mention
    # ──────────────────────────────────────────────────────────────────────────
    async def _is_mentioned(self, text: str, thread_id: str) -> bool:
        """
        Bot được nhắc đến nếu text chứa BẤT KỲ một trong:
        1. config.BOT_NAME          (ví dụ: '@MyAI')
        2. self.name                (tên thật Facebook của bot)
        3. Nickname của bot trong group thread_id (nếu có)
        """
        t = text.lower()

        if config.BOT_NAME.lower() in t:
            return True

        if self.name and self.name.lower() in t:
            return True

        nickname = await self._get_bot_nickname(thread_id)
        if nickname and nickname.lower() in t:
            return True

        return False

    def _strip_triggers(self, text: str, nickname: str | None) -> str:
        """Loại bỏ tất cả trigger keywords khỏi câu hỏi, trả về text sạch."""
        result = text
        for token in filter(None, [config.BOT_NAME, self.name, nickname]):
            result = result.replace(token, "").replace(token.lower(), "")
        return result.strip()

    # ──────────────────────────────────────────────────────────────────────────
    # Callback nhận tin nhắn
    # ──────────────────────────────────────────────────────────────────────────
    async def on_message(self, event_data: Message) -> None:
        """Xử lý mọi tin nhắn đến. Bỏ qua tin của chính bot."""
        if str(event_data.sender_id) == str(self.uid):
            return

        raw_text: str = (event_data.text or "").strip()
        thread_id: str = str(event_data.thread_id)
        sender_id: str = str(event_data.sender_id)
        thread_type: ThreadType = event_data.thread_type

        # ── Group ──────────────────────────────────────────────────────────
        if thread_type == ThreadType.GROUP:
            if not self._is_allowed_group(thread_id):
                return

            _log("MSG", f"group={thread_id} | user={sender_id} | \"{raw_text}\"")

            mentioned = await self._is_mentioned(raw_text, thread_id)
            if not mentioned:
                return

            nickname = await self._get_bot_nickname(thread_id)
            question = self._strip_triggers(raw_text, nickname)
            context_key = f"group_{thread_id}"
            source_label = f"GROUP {thread_id}"

        # ── DM ─────────────────────────────────────────────────────────────
        elif thread_type == ThreadType.USER:
            if config.ALLOWED_USER_IDS and sender_id not in [
                str(u) for u in config.ALLOWED_USER_IDS
            ]:
                return

            _log("DM", f"user={sender_id} | \"{raw_text}\"")
            question = raw_text
            context_key = f"dm_{sender_id}"
            source_label = f"DM {sender_id}"
            thread_id = thread_id  # giữ nguyên để send_message đúng thread

        else:
            return

        if not question:
            _log("SKIP", f"Câu hỏi rỗng sau khi strip trigger — bỏ qua.")
            return

        await self._respond(
            sender_id=sender_id,
            question=question,
            thread_id=thread_id,
            context_key=context_key,
            source_label=source_label,
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
        source_label: str,
    ) -> None:
        _log("AI→", f"[{source_label}] Đang xử lý: \"{question[:80]}{'…' if len(question)>80 else ''}\"")

        try:
            answer = await ai_handler.get_ai_response(
                thread_id=context_key,
                user_message=question,
            )

            await self.send_message(text=answer, thread_id=thread_id)

            short_a = answer[:100] + ("…" if len(answer) > 100 else "")
            _log("✅", f"[{source_label}] user={sender_id} -> \"{short_a}\"")

            await logger.log_success(
                sender_name=sender_id,
                sender_id=sender_id,
                question=question,
                answer=answer,
                group_id=thread_id if context_key.startswith("group_") else None,
            )

        except Exception as exc:  # noqa: BLE001
            _log("❌", f"[{source_label}] Lỗi: {exc}")
            await logger.log_error(
                context=f"Xử lý tin nhắn từ user {sender_id} [{source_label}]",
                exc=exc,
                extra=f"Q: {question[:200]}",
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────
    def _is_allowed_group(self, thread_id: str) -> bool:
        if not config.GROUP_IDS:
            return True
        return thread_id in [str(g) for g in config.GROUP_IDS]

    # ──────────────────────────────────────────────────────────────────────────
    # Sự kiện vòng đời
    # ──────────────────────────────────────────────────────────────────────────
    async def on_listening(self) -> None:
        _log("BOT", f"UID={self.uid} | Tên={self.name}")
        _log("BOT", f"Groups={config.GROUP_IDS or 'TẤT CẢ'} | Model={config.MODEL_NAME}")
        _log("BOT", f"Trigger: '{config.BOT_NAME}' | tên thật | nickname group")
        _log("BOT", "─" * 50)
        _log("BOT", "✅ Đang lắng nghe tin nhắn…")

        await logger.log_info(
            f"✅ {config.BOT_NAME} đang chạy!\n"
            f"   UID: {self.uid} | Tên: {self.name}\n"
            f"   Groups: {config.GROUP_IDS or 'Tất cả'}\n"
            f"   Model: {config.MODEL_NAME}"
        )

    async def on_nickname_change(self, event_data) -> None:
        """Xoá cache nickname khi có người đổi nickname trong group."""
        try:
            thread_id = str(event_data.thread_id)
            self.invalidate_nickname_cache(thread_id)
            _log("INFO", f"Nickname thay đổi trong group {thread_id} — đã xoá cache.")
        except Exception:
            pass


# ─── Khởi tạo và chạy ─────────────────────────────────────────────────────────

async def create_and_listen() -> None:
    """Tạo bot, xác thực bằng cookies.json và bắt đầu lắng nghe."""
    import json
    from pathlib import Path

    cookies_path = Path(config.COOKIES_FILE)
    if not cookies_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy '{config.COOKIES_FILE}'. "
            "Hãy export cookies Facebook và lưu vào file này."
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

    _log("BOT", f"Đang kết nối Facebook với cookies: {config.COOKIES_FILE}")
    async with FacebookBot(cookies_file_path=config.COOKIES_FILE) as bot:
        await bot.listen()
