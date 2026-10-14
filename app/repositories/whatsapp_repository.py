"""PostgreSQL repository for WhatsApp conversations and messages."""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..channels.whatsapp.client import normalize_phone_number
from ..db.models.patient import Patient
from ..db.models.whatsapp import WhatsAppConversation, WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppRepository:
    """Thread-safe transactional repository for WhatsApp domain persistence."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get_or_create_conversation(
        self,
        tenant_id: str,
        phone_number: str,
        wa_id: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> WhatsAppConversation:
        """Find existing conversation or create a new one linked to matching patient."""
        norm_phone = normalize_phone_number(phone_number) or phone_number.strip()
        last_10 = norm_phone[-10:] if len(norm_phone) >= 10 else norm_phone

        with self.session_factory() as session:
            stmt = select(WhatsAppConversation).where(
                WhatsAppConversation.tenant_id == tenant_id,
                WhatsAppConversation.phone_number == norm_phone,
            )
            conv = session.scalars(stmt).first()

            if conv:
                changed = False
                if profile_name and conv.profile_name != profile_name:
                    conv.profile_name = profile_name
                    changed = True
                if wa_id and not conv.wa_id:
                    conv.wa_id = wa_id
                    changed = True
                if not conv.patient_id and last_10:
                    # Attempt linking to patient
                    pat_stmt = select(Patient).where(
                        Patient.tenant_id == tenant_id,
                        Patient.phone.like(f"%{last_10}%"),
                    )
                    pat = session.scalars(pat_stmt).first()
                    if pat:
                        conv.patient_id = pat.id
                        changed = True
                if changed:
                    session.commit()
                    session.refresh(conv)
                return conv

            # Create new conversation, linking to patient if exists
            pat_id = None
            if last_10:
                pat_stmt = select(Patient).where(
                    Patient.tenant_id == tenant_id,
                    Patient.phone.like(f"%{last_10}%"),
                )
                pat = session.scalars(pat_stmt).first()
                if pat:
                    pat_id = pat.id

            new_conv = WhatsAppConversation(
                tenant_id=tenant_id,
                phone_number=norm_phone,
                wa_id=wa_id,
                profile_name=profile_name,
                patient_id=pat_id,
                is_active=True,
                last_message_at=datetime.now(timezone.utc),
            )
            session.add(new_conv)
            session.commit()
            session.refresh(new_conv)
            return new_conv

    def record_inbound_message(
        self,
        tenant_id: str,
        conversation_id: Optional[str],
        whatsapp_message_id: str,
        phone_number: str,
        message_type: str,
        body: Optional[str],
        raw_payload: Optional[str] = None,
    ) -> Tuple[WhatsAppMessage, bool]:
        """Record inbound message in PostgreSQL with idempotent deduplication.

        Returns (message_record, is_duplicate).
        """
        norm_phone = normalize_phone_number(phone_number) or phone_number.strip()
        with self.session_factory() as session:
            # Check existing message ID for deduplication
            if whatsapp_message_id:
                stmt = select(WhatsAppMessage).where(
                    WhatsAppMessage.tenant_id == tenant_id,
                    WhatsAppMessage.whatsapp_message_id == whatsapp_message_id,
                )
                existing = session.scalars(stmt).first()
                if existing:
                    logger.info(
                        "Deduplicated existing inbound WhatsApp message in DB: tenant=%s, msg_id=%s",
                        tenant_id, whatsapp_message_id,
                    )
                    return existing, True

            now = datetime.now(timezone.utc)
            msg = WhatsAppMessage(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                whatsapp_message_id=whatsapp_message_id,
                phone_number=norm_phone,
                direction="inbound",
                message_type=message_type or "text",
                body=body,
                status="received",
                raw_payload=raw_payload,
            )
            session.add(msg)

            # Update conversation last_message_at
            if conversation_id:
                conv = session.get(WhatsAppConversation, conversation_id)
                if conv:
                    conv.last_message_at = now

            session.commit()
            session.refresh(msg)
            return msg, False

    def record_outbound_message(
        self,
        tenant_id: str,
        conversation_id: Optional[str],
        whatsapp_message_id: Optional[str],
        phone_number: str,
        message_type: str,
        body: Optional[str],
        status: str = "sent",
        raw_payload: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> WhatsAppMessage:
        """Record outbound message in PostgreSQL."""
        norm_phone = normalize_phone_number(phone_number) or phone_number.strip()
        with self.session_factory() as session:
            now = datetime.now(timezone.utc)
            msg = WhatsAppMessage(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                whatsapp_message_id=whatsapp_message_id,
                phone_number=norm_phone,
                direction="outbound",
                message_type=message_type or "text",
                body=body,
                status=status,
                raw_payload=raw_payload,
                error_details=error_details,
            )
            session.add(msg)

            if conversation_id:
                conv = session.get(WhatsAppConversation, conversation_id)
                if conv:
                    conv.last_message_at = now

            session.commit()
            session.refresh(msg)
            return msg

    def update_message_status(
        self,
        whatsapp_message_id: str,
        status: str,
        tenant_id: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> Optional[WhatsAppMessage]:
        """Update message delivery status (e.g. sent, delivered, read, failed)."""
        if not whatsapp_message_id:
            return None

        with self.session_factory() as session:
            stmt = select(WhatsAppMessage).where(
                WhatsAppMessage.whatsapp_message_id == whatsapp_message_id
            )
            if tenant_id:
                stmt = stmt.where(WhatsAppMessage.tenant_id == tenant_id)

            msg = session.scalars(stmt).first()
            if not msg:
                return None

            msg.status = status
            if error_details:
                msg.error_details = error_details
            session.commit()
            session.refresh(msg)
            return msg

    def get_conversation_messages(
        self,
        tenant_id: str,
        phone_number: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent message history for a conversation."""
        norm_phone = normalize_phone_number(phone_number) or phone_number.strip()
        with self.session_factory() as session:
            stmt = (
                select(WhatsAppMessage)
                .where(
                    WhatsAppMessage.tenant_id == tenant_id,
                    WhatsAppMessage.phone_number == norm_phone,
                )
                .order_by(WhatsAppMessage.created_at.asc())
                .limit(limit)
            )
            messages = session.scalars(stmt).all()
            return [
                {
                    "id": m.id,
                    "whatsapp_message_id": m.whatsapp_message_id,
                    "direction": m.direction,
                    "message_type": m.message_type,
                    "body": m.body,
                    "status": m.status,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ]

