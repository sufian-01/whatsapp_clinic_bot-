"""Small Telegram API adapter used by the webhook."""

from telegram import Bot


class TelegramBot:
    def __init__(self, token: str) -> None:
        self._bot = Bot(token)

    @property
    def raw(self) -> Bot:
        return self._bot

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def register_webhook(self, url: str, secret_token: str = "") -> bool:
        return await self._bot.set_webhook(url=url, secret_token=secret_token or None)