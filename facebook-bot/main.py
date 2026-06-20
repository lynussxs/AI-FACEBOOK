"""
main.py — File chạy chính của Facebook AI Bot.
Khởi động bot với auto-reconnect khi mất kết nối.
"""

import asyncio
import os
import sys
from pathlib import Path


def _bootstrap_cookies() -> None:
    """
    Tự động tạo cookies.json từ biến môi trường FB_COOKIES_DATA.
    Chỉ chạy khi file chưa tồn tại hoặc rỗng — dùng khi deploy trên Railway.
    """
    cookies_file = Path(os.environ.get("COOKIES_FILE", "cookies.json"))
    cookies_data = os.environ.get("FB_COOKIES_DATA", "").strip()

    if not cookies_data:
        return  # Không có biến môi trường → bỏ qua

    # Chỉ ghi nếu file chưa tồn tại hoặc đang rỗng {}
    if not cookies_file.exists() or cookies_file.read_text(encoding="utf-8").strip() in ("", "{}"):
        cookies_file.write_text(cookies_data, encoding="utf-8")
        print(f"[BOOT] ✅ Đã tạo {cookies_file} từ biến môi trường FB_COOKIES_DATA")
    else:
        print(f"[BOOT] ℹ️  {cookies_file} đã tồn tại — bỏ qua FB_COOKIES_DATA")


import config
import logger
import facebook_client


async def run_bot() -> None:
    """
    Vòng lặp chính: kết nối → lắng nghe → tự reconnect khi disconnect.
    """
    await logger.log_info(
        f"🚀 Khởi động {config.BOT_NAME} | Model: {config.MODEL_NAME}"
    )

    attempt = 0
    while True:
        attempt += 1
        max_attempts = config.MAX_RECONNECT_ATTEMPTS
        if max_attempts > 0 and attempt > max_attempts:
            await logger.log_error(
                f"Đã thử reconnect {max_attempts} lần, dừng bot."
            )
            sys.exit(1)

        try:
            await logger.log_info(
                f"🔌 Đang kết nối Facebook… (lần thử #{attempt})"
            )

            # Kết nối và lắng nghe (blocking đến khi disconnect)
            await facebook_client.create_and_listen()

        except (FileNotFoundError, ValueError) as exc:
            # Lỗi cấu hình — không cần reconnect, dừng ngay
            await logger.log_error(
                context="Lỗi cấu hình cookies",
                exc=exc,
            )
            sys.exit(1)

        except KeyboardInterrupt:
            await logger.log_info("⛔ Bot dừng theo yêu cầu người dùng.")
            sys.exit(0)

        except Exception as exc:  # noqa: BLE001
            await logger.log_error(
                context=f"Bot bị disconnect (lần #{attempt})",
                exc=exc,
                extra=f"Sẽ thử lại sau {config.RECONNECT_DELAY}s…",
            )

        # Chờ trước khi reconnect
        await logger.log_info(
            f"⏳ Chờ {config.RECONNECT_DELAY}s trước khi reconnect…"
        )
        await asyncio.sleep(config.RECONNECT_DELAY)


def main():
    """Entry point."""
    # Bước 1: Tạo cookies.json từ env var nếu cần (Railway deploy)
    _bootstrap_cookies()

    # Bước 2: Validate config
    try:
        config.validate()
    except EnvironmentError as exc:
        print(f"❌ Lỗi cấu hình:\n{exc}")
        sys.exit(1)

    # Bước 3: Chạy bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n⛔ Bot dừng.")
        sys.exit(0)


if __name__ == "__main__":
    main()
