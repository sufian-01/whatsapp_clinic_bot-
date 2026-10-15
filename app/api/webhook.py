"""Legacy webhook endpoint (deprecated: platform uses Meta WhatsApp Cloud API)."""

import logging
from fastapi import APIRouter, Header, HTTPException, Request

from ..core.config import Settings

logger = logging.getLogger(__name__)


def create_webhook_router(settings: Settings, graph=None, bot=None, sarvam=None) -> APIRouter:
    router = APIRouter()

    path = getattr(settings, "webhook_path", "/webhook/telegram")

    @router.post(path)
    async def legacy_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
        if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
        if bot and hasattr(bot, "raw"):
            try:
                from telegram import Update
                from ..telegram.handlers import handle_update

                update = Update.de_json(await request.json(), bot.raw)
                await handle_update(update, settings.clinic_name, graph, bot, sarvam)
                return {"ok": True}
            except Exception:
                logger.exception("Legacy webhook processing failed")
        return {"ok": True, "channel": "whatsapp_primary"}

    return router
