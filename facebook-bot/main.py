"""
main.py — File chạy chính của Facebook AI Bot.
Khởi động bot với auto-reconnect khi mất kết nối.
"""

import asyncio
import sys

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
    # Validate config khi khởi động
    try:
        config.validate()
    except EnvironmentError as exc:
        print(f"❌ Lỗi cấu hình:\n{exc}")
        sys.exit(1)

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n⛔ Bot dừng.")
        sys.exit(0)


if __name__ == "__main__":
    main()
