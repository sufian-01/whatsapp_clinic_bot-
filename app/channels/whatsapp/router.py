"""FastAPI endpoints for Meta WhatsApp Cloud API Webhook."""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse

from ...core.config import Settings
from .handler import WhatsAppHandler
from .models import WhatsAppWebhookPayload
from .security import verify_meta_signature, verify_webhook_challenge

logger = logging.getLogger(__name__)


def create_whatsapp_router(settings: Settings, handler: WhatsAppHandler) -> APIRouter:
    """Create and configure the Meta WhatsApp Cloud API webhook router."""
    router = APIRouter(tags=["whatsapp"])

    @router.get(settings.whatsapp_webhook_path)
    async def whatsapp_webhook_verification(
        hub_mode: Optional[str] = Query(None, alias="hub.mode"),
        hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
        hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    ) -> Response:
        """Handle Meta Webhook verification handshake."""
        expected_token = settings.whatsapp_verify_token
        challenge = verify_webhook_challenge(hub_mode, hub_verify_token, hub_challenge, expected_token)
        if challenge is not None:
            logger.info("Meta WhatsApp webhook verification challenge verified successfully.")
            return PlainTextResponse(content=challenge, status_code=status.HTTP_200_OK)

        logger.warning(
            "Meta WhatsApp webhook verification failed: mode=%s, token_match=%s",
            hub_mode,
            bool(hub_verify_token and hub_verify_token == expected_token),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification token mismatch or invalid mode.",
        )

    @router.post(settings.whatsapp_webhook_path)
    async def whatsapp_webhook_inbound(
        request: Request,
        background_tasks: BackgroundTasks,
        x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    ) -> dict:
        """Process inbound WhatsApp messages and status events with signature verification."""
        logger.info("[WHATSAPP WEBHOOK] payload received")
        raw_body = await request.body()

        # 1. Signature Verification (HMAC-SHA256)
        if settings.whatsapp_app_secret and x_hub_signature_256:
            if not verify_meta_signature(raw_body, x_hub_signature_256, settings.whatsapp_app_secret):
                logger.warning("[WHATSAPP WEBHOOK] Signature verification failed.")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid X-Hub-Signature-256 webhook signature.",
                )
        elif settings.whatsapp_app_secret and not x_hub_signature_256:
            if settings.app_env.casefold() == "production":
                logger.warning("[WHATSAPP WEBHOOK] Missing required signature in production.")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Missing X-Hub-Signature-256 signature header.",
                )

        # 2. Schema Parse
        try:
            payload_dict = await request.json()
            payload = WhatsAppWebhookPayload.model_validate(payload_dict)
        except Exception as e:
            logger.warning("[WHATSAPP WEBHOOK] Malformed WhatsApp webhook payload: %s", e)
            # Meta expects 200 OK even for unparseable webhooks to prevent retrying bad payloads
            return {"status": "ignored", "reason": "malformed_payload"}

        # 3. Dispatch to background processor for prompt acknowledgement
        for entry in payload.entry:
            for change in entry.changes:
                if (change.field == "messages" or not change.field) and change.value:
                    background_tasks.add_task(handler.handle_value, change.value)

        # Immediate return (<50ms) to satisfy Meta requirements
        return {"status": "ok"}

    return router
