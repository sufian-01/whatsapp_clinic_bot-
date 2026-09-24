"""Telegram webhook endpoint."""

from fastapi import APIRouter, Header, HTTPException, Request
from telegram import Update

from ..core.config import Settings
from ..telegram.handlers import handle_update


def create_webhook_router(settings: Settings, graph, bot) -> APIRouter:
    router = APIRouter()

    @router.post(settings.webhook_path)
    async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
        if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
        try:
            update = Update.de_json(await request.json(), bot.raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Telegram update") from None
        try:
            await handle_update(update, settings.clinic_name, graph, bot)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Telegram update handling failed")
        return {"ok": True}

    return router