"""Register the configured Telegram webhook: python -m app.register_webhook."""

import asyncio

from .core.config import get_settings, validate_settings
from .telegram.bot import TelegramBot
from .telegram.webhook import register_webhook


async def main() -> None:
    settings = get_settings()
    validate_settings(settings)
    result = await register_webhook(
        TelegramBot(settings.telegram_bot_token),
        settings.telegram_webhook_url + settings.webhook_path,
        settings.telegram_webhook_secret,
    )
    print("Telegram webhook registered" if result else "Telegram rejected webhook registration")


if __name__ == "__main__":
    asyncio.run(main())