"""Telegram webhook registration service."""

from .bot import TelegramBot


async def register_webhook(bot: TelegramBot, webhook_url: str, secret_token: str = "") -> bool:
    if not webhook_url:
        raise ValueError("TELEGRAM_WEBHOOK_URL is required to register a webhook")
    return await bot.register_webhook(webhook_url, secret_token)