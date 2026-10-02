"""Small Telegram API adapter used by the webhook."""

from io import BytesIO
from pathlib import Path

from telegram import Bot


class TelegramBot:
    def __init__(self, token: str) -> None:
        self._bot = Bot(token)

    @property
    def raw(self) -> Bot:
        return self._bot

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def send_voice(self, chat_id: int, audio: bytes, reply_markup=None) -> None:
        """Send an OGG/Opus reply without writing patient data to disk."""
        voice = BytesIO(audio)
        voice.name = "clinic-reply.ogg"
        await self._bot.send_voice(chat_id=chat_id, voice=voice, reply_markup=reply_markup)

    async def download_voice_file(self, file_id: str, destination: Path) -> None:
        """Download a Telegram voice message to an already-private temp path."""
        telegram_file = await self._bot.get_file(file_id)
        await telegram_file.download_to_drive(custom_path=destination)

    async def register_webhook(self, url: str, secret_token: str = "") -> bool:
        return await self._bot.set_webhook(url=url, secret_token=secret_token or None)
