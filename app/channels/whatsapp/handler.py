"""WhatsApp message processing and chatbot orchestration handler.

Connects the Meta WhatsApp Cloud API channel to the shared multi-tenant AI core:
- Validates receiving business phone number to resolve target tenant (strict fail-closed).
- Persists conversations and messages in PostgreSQL via WhatsAppRepository.
- Deduplicates incoming messages using memory TTL cache and PostgreSQL uniqueness.
- Manages isolated conversation state per tenant and patient phone.
- Dispatches messages to the unified LangGraph agent inside tenant_scope(tenant_id).
- Formats AI responses into WhatsApp text or interactive buttons.
- Handles delivery status callbacks and marks messages as read.
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
import tempfile
from threading import Lock
import time
from typing import Any, Dict, List, Optional, Set

from ...core.config import Settings
from ...core.feature_flags import (
    FEATURE_CANCELLATION,
    FEATURE_INTERACTIVE_LISTS,
    FEATURE_ONLINE_PAYMENTS,
    FEATURE_RAG_KNOWLEDGE,
    FEATURE_RESCHEDULING,
    FEATURE_VOICE_INBOUND,
    FEATURE_VOICE_OUTBOUND,
    get_disabled_feature_message,
    is_feature_enabled,
    resolve_effective_feature_flags,
)
from ...core.tenant import tenant_scope
from ...telegram.sessions import SessionStore
from .client import MetaWhatsAppClient, normalize_phone_number
from .models import WhatsAppMessage, WhatsAppValue


logger = logging.getLogger(__name__)


def _format_whatsapp_markdown(text: str) -> str:
    """Convert standard markdown into WhatsApp-compatible markdown (*bold*, no ### headers)."""
    if not text:
        return ""
    # Convert **bold** to *bold*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Convert header tags like ### Header to *Header*
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)
    return text.strip()


def _clean_text_for_speech(text: str) -> str:
    """Format bot text into natural spoken language for Sarvam TTS voice synthesis."""
    if not text:
        return ""
    # Remove markdown asterisks, hashes, backticks, underscores
    cleaned = re.sub(r"[\*_~`#]", "", text)
    # Remove URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove emojis
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", cleaned)
    # Remove multiple dashes/equals
    cleaned = re.sub(r"[-=]{3,}", "", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class WhatsAppHandler:
    """Thread-safe processor connecting WhatsApp webhooks to the LangGraph AI Assistant."""

    def __init__(
        self,
        settings: Settings,
        graph,
        client: Optional[MetaWhatsAppClient] = None,
        sessions: Optional[SessionStore] = None,
        audit_service: Optional[Any] = None,
        repository: Optional[Any] = None,
        sarvam: Optional[Any] = None,
        tenant_management_service: Optional[Any] = None,
    ):
        self.settings = settings
        self.graph = graph
        self.client = client or MetaWhatsAppClient(
            access_token=settings.whatsapp_access_token,
            api_version=settings.whatsapp_api_version,
            phone_number_id=settings.whatsapp_phone_number_id,
            default_country_code=settings.whatsapp_default_country_code,
        )
        self.sessions = sessions or SessionStore()
        self.audit = audit_service
        self.repository = repository
        self.sarvam = sarvam
        self.tenant_mgmt_service = tenant_management_service
        if self.sarvam is None:
            try:
                from ...services.sarvam_service import SarvamService
                self.sarvam = SarvamService.from_settings(settings)
            except Exception:
                self.sarvam = None
        self._seen_messages: Dict[str, float] = {}  # message_id -> timestamp
        self._lock = Lock()
        self._dedup_ttl_seconds = 3600  # 1 hour

    def is_duplicate(self, message_id: str) -> bool:
        """Check if message_id was already processed recently, pruning old entries."""
        if not message_id:
            return False
        now = time.time()
        with self._lock:
            # Prune entries older than TTL
            expired = [mid for mid, ts in self._seen_messages.items() if now - ts > self._dedup_ttl_seconds]
            for mid in expired:
                del self._seen_messages[mid]

            if message_id in self._seen_messages:
                return True
            self._seen_messages[message_id] = now
            return False

    def resolve_tenant_id(self, phone_number_id: str) -> Optional[str]:
        """Resolve receiving business phone number ID to tenant ID.

        Enforces strict fail-closed routing: returns None if phone_number_id is unmapped.
        Checks dynamic database-backed TenantManagementService first, falling back to static config.
        """
        clean_pid = str(phone_number_id).strip() if phone_number_id else ""
        if not clean_pid:
            return None

        # 1. Dynamic lookup from TenantManagementService (backed by DB & cache)
        if self.tenant_mgmt_service:
            dynamic_tid = self.tenant_mgmt_service.resolve_tenant_by_phone_number_id(clean_pid)
            if dynamic_tid:
                return dynamic_tid

        # 2. Static configuration fallback (.env WHATSAPP_TENANT_PHONE_MAP)
        mapping = self.settings.get_whatsapp_tenant_mapping()
        tenant_id = mapping.get(clean_pid)
        return tenant_id if tenant_id else None

    def _get_tenant_flags(self, tenant_id: Optional[str]) -> Dict[str, bool]:
        if tenant_id and self.tenant_mgmt_service:
            return self.tenant_mgmt_service.get_tenant_feature_flags(tenant_id)
        # When no tenant_mgmt_service is injected (e.g., unit tests), default to full capabilities
        return resolve_effective_feature_flags("ENTERPRISE", {})


    def _get_clinic_name(self, tenant_id: Optional[str]) -> str:
        if tenant_id and self.tenant_mgmt_service:
            t = self.tenant_mgmt_service.get_tenant(tenant_id)
            if t and t.get("name"):
                return t["name"]
        return self.settings.clinic_name

    def _get_support_phone(self, tenant_id: Optional[str]) -> str:
        if tenant_id and self.tenant_mgmt_service:
            t = self.tenant_mgmt_service.get_tenant(tenant_id)
            if t and t.get("phone"):
                return t["phone"]
        return self.settings.support_phone or "the clinic reception"


    async def handle_value(self, value: WhatsAppValue) -> None:
        """Process a WhatsApp webhook 'value' payload containing messages or statuses."""
        phone_number_id = (
            value.metadata.phone_number_id
            if value.metadata and value.metadata.phone_number_id
            else self.settings.whatsapp_phone_number_id
        )
        tenant_id = self.resolve_tenant_id(phone_number_id)

        # 1. Process delivery statuses (always safe to process; updates DB if message ID exists)
        if value.statuses:
            for status_obj in value.statuses:
                self._handle_status(status_obj, tenant_id)

        # 2. Process incoming messages
        if value.messages:
            if not tenant_id:
                logger.error(
                    "FAIL-CLOSED: Inbound WhatsApp message received on unmapped phone_number_id=%s. "
                    "Rejecting request without accessing any clinic tenant data.",
                    phone_number_id,
                )
                return

            contact_profiles: Dict[str, str] = {}
            if value.contacts:
                for c in value.contacts:
                    if c.profile and c.profile.name:
                        contact_profiles[c.wa_id] = c.profile.name

            for message in value.messages:
                profile_name = contact_profiles.get(message.from_)
                await self._handle_message(
                    message, tenant_id, phone_number_id, profile_name=profile_name
                )

    def _handle_status(self, status_obj, tenant_id: Optional[str]) -> None:
        """Log delivery receipts, errors, and update database message status."""
        safe_msg_id = status_obj.id[:16] if status_obj.id else "unknown"
        safe_recipient = hashlib.sha256(status_obj.recipient_id.encode()).hexdigest()[:8] if status_obj.recipient_id else "unknown"
        if status_obj.status == "failed":
            logger.warning(
                "WhatsApp message delivery failed: tenant=%s, msg_id=%s, recipient_hash=%s, errors=%s",
                tenant_id, safe_msg_id, safe_recipient, status_obj.errors,
            )
        else:
            logger.info(
                "WhatsApp message status update: tenant=%s, msg_id=%s, status=%s",
                tenant_id, safe_msg_id, status_obj.status,
            )

        # Update in PostgreSQL database if repository available
        if self.repository and status_obj.id:
            try:
                err_text = json.dumps(status_obj.errors) if status_obj.errors else None
                self.repository.update_message_status(
                    whatsapp_message_id=status_obj.id,
                    status=status_obj.status,
                    tenant_id=tenant_id,
                    error_details=err_text,
                )
            except Exception:
                logger.exception("Failed to update WhatsApp message status in repository: %s", safe_msg_id)

        if self.audit:
            try:
                self.audit.record(
                    user="whatsapp_webhook",
                    action="WHATSAPP_STATUS_CALLBACK",
                    entity_type="message",
                    entity_id=safe_msg_id,
                    details={
                        "tenant_id": tenant_id,
                        "status": status_obj.status,
                        "recipient_hash": safe_recipient,
                    },
                )
            except Exception:
                pass

    async def _handle_message(
        self,
        message: WhatsAppMessage,
        tenant_id: str,
        phone_number_id: str,
        profile_name: Optional[str] = None,
    ) -> None:
        """Process single inbound message with fail-closed tenant scoping and DB persistence."""
        msg_id = message.id or f"gen_{hashlib.sha256((message.from_ + (message.text.body if message.text else '')).encode()).hexdigest()[:16]}"
        if self.is_duplicate(msg_id):
            logger.info("Ignoring duplicate WhatsApp message (memory cache): %s", msg_id)
            return

        sender_phone = normalize_phone_number(message.from_, self.settings.whatsapp_default_country_code) or message.from_
        flags = self._get_tenant_flags(tenant_id)
        clinic_name = self._get_clinic_name(tenant_id)
        support_phone = self._get_support_phone(tenant_id)

        # 1. Check if incoming message is a voice note / audio
        is_voice_inbound = False
        user_input = ""
        is_unsupported = False

        if message.type in ("audio", "voice"):
            if not is_feature_enabled(flags, FEATURE_VOICE_INBOUND):
                logger.info("[WHATSAPP AUDIO] Feature 'voice_inbound' disabled for tenant=%s", tenant_id)
                disabled_msg = get_disabled_feature_message(FEATURE_VOICE_INBOUND, clinic_name, support_phone)
                self.client.send_text(sender_phone, disabled_msg, phone_number_id=phone_number_id)
                return

            audio_obj = message.audio or message.voice
            media_id = audio_obj.id if audio_obj else None
            if not media_id:
                logger.warning("[WHATSAPP AUDIO] Received audio message without media_id")
                return


            logger.info("=" * 60)
            logger.info(">>> [STEP 1: INBOUND VOICE MESSAGE]")
            logger.info("[WHATSAPP WEBHOOK] customer_number=%s", sender_phone)
            logger.info("[WHATSAPP WEBHOOK] message type: %s (media_id=%s)", message.type, media_id)
            logger.info("[WHATSAPP WEBHOOK] selected store/tenant: %s", tenant_id)
            logger.info("[WHATSAPP AUDIO] Downloading audio from Meta CDN...")

            audio_bytes = await asyncio.to_thread(self.client.download_media, media_id)
            if not audio_bytes:
                logger.error("[WHATSAPP AUDIO] Failed to download audio media_id=%s", media_id)
                err_text = "I received your voice note, but could not download it. Please try sending it again or typing your message."
                self.client.send_text(sender_phone, err_text, phone_number_id=phone_number_id)
                return

            if not self.sarvam or not getattr(self.sarvam, "available", False):
                logger.warning("[WHATSAPP AUDIO] Sarvam AI service not configured")
                err_text = "Voice features are currently unavailable. Please send your query as a text message."
                self.client.send_text(sender_phone, err_text, phone_number_id=phone_number_id)
                return

            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                    f.write(audio_bytes)
                    temp_path = Path(f.name)

                logger.info("[WHATSAPP AUDIO] Transcribing audio via Sarvam STT (%s)...", self.settings.sarvam_stt_model)
                transcript = await asyncio.to_thread(self.sarvam.transcribe, temp_path)
                logger.info("=" * 60)
                logger.info(">>> [SARVAM STT SUCCESS] Transcript: '%s'", transcript)
                logger.info("=" * 60)
                user_input = transcript
                is_voice_inbound = True
            except Exception as e:
                logger.warning("[WHATSAPP AUDIO] Sarvam STT transcription failed: %s", e)
                err_text = "I received your voice note, but couldn't understand it clearly. Could you please record it again or type your message?"
                self.client.send_text(sender_phone, err_text, phone_number_id=phone_number_id)
                return
            finally:
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
        else:
            user_input, is_unsupported = self._extract_message_text(message)
            logger.info("=" * 60)
            logger.info(">>> [STEP 1: INBOUND MESSAGE]")
            logger.info("[WHATSAPP WEBHOOK] customer_number=%s", sender_phone)
            logger.info("[WHATSAPP WEBHOOK] message=%s", user_input)
            logger.info("[WHATSAPP WEBHOOK] message type: %s", message.type)
            logger.info("[WHATSAPP WEBHOOK] selected store/tenant: %s", tenant_id)
            logger.info("=" * 60)

        # Persist conversation and inbound message in PostgreSQL
        conv_id = None
        if self.repository:
            try:
                conversation = self.repository.get_or_create_conversation(
                    tenant_id=tenant_id,
                    phone_number=sender_phone,
                    wa_id=message.from_,
                    profile_name=profile_name,
                )
                conv_id = conversation.id if conversation else None
                preview_body = user_input if user_input else f"[{message.type}]"
                raw_json = json.dumps(message.model_dump())
                _, is_db_dup = self.repository.record_inbound_message(
                    tenant_id=tenant_id,
                    conversation_id=conv_id,
                    whatsapp_message_id=msg_id,
                    phone_number=sender_phone,
                    message_type=message.type,
                    body=preview_body,
                    raw_payload=raw_json,
                )
                if is_db_dup:
                    logger.info("Ignoring duplicate WhatsApp message (database deduplication): %s", msg_id)
                    return
            except Exception:
                logger.exception("Failed to persist inbound WhatsApp message to DB for tenant=%s", tenant_id)

        if self.audit:
            try:
                safe_sender = hashlib.sha256(sender_phone.encode()).hexdigest()[:10]
                self.audit.record(
                    user="whatsapp_patient",
                    action="WHATSAPP_MESSAGE_RECEIVED",
                    entity_type="message",
                    entity_id=msg_id[:16] if msg_id else "unknown",
                    details={"tenant_id": tenant_id, "type": message.type, "sender_hash": safe_sender},
                )
            except Exception:
                pass

        # Mark message as read asynchronously
        try:
            self.client.mark_as_read(msg_id, phone_number_id=phone_number_id)
        except Exception:
            pass

        if is_unsupported:
            guidance = (
                f"Hello! 👋 I am the AI Medical Assistant for {self.settings.clinic_name}.\n\n"
                "I received your attachment. For privacy and clinical safety, files and attachments "
                "are reviewed directly with the doctor during your appointment.\n\n"
                "You can message me to book, check, reschedule, or cancel appointments, or ask about clinic timings!"
            )
            res = self.client.send_text(sender_phone, guidance, phone_number_id=phone_number_id)
            if self.repository:
                try:
                    out_wamid = (
                        res.get("data", {}).get("messages", [{}])[0].get("id")
                        if res and res.get("data") else None
                    )
                    self.repository.record_outbound_message(
                        tenant_id=tenant_id,
                        conversation_id=conv_id,
                        whatsapp_message_id=out_wamid,
                        phone_number=sender_phone,
                        message_type="text",
                        body=guidance,
                        status="sent" if res.get("success") else "failed",
                        raw_payload=json.dumps(res) if res else None,
                    )
                except Exception:
                    pass
            return

        if not user_input:
            return

        # Execute shared LangGraph flow inside tenant context
        with tenant_scope(tenant_id):
            session_key = f"wa:{tenant_id}:{sender_phone}"
            state = self.sessions.get(session_key)
            state["chat_id"] = session_key
            state["user_text"] = user_input
            state["channel"] = "whatsapp"
            state["phone"] = sender_phone
            state["tenant_id"] = tenant_id
            state["feature_flags"] = flags
            state["clinic_name"] = clinic_name
            state["support_phone"] = support_phone


            history = list(state.get("messages", []))
            history.append({"role": "user", "content": user_input})
            state["messages"] = history[-12:]

            try:
                # Invoke LangGraph
                logger.info("[WHATSAPP AGENT] processing started")
                result = await asyncio.to_thread(self.graph.invoke, state)

                response_text = result.get("response", "")
                if not response_text:
                    response_text = "I have received your request. How else can I assist you with your clinic visit?"

                logger.info("[WHATSAPP AGENT] agent response=%s", response_text)

                # Append to history
                resp_history = list(result.get("messages", state["messages"]))
                resp_history.append({"role": "assistant", "content": response_text})
                result["messages"] = resp_history[-12:]

                self.sessions.save(session_key, result)

                # Send response back to patient via WhatsApp and persist outbound record
                await self._send_whatsapp_reply(
                    sender_phone,
                    response_text,
                    result,
                    phone_number_id,
                    is_voice=is_voice_inbound,
                    tenant_id=tenant_id,
                    conversation_id=conv_id,
                )
            except Exception:
                logger.exception("Failed to process WhatsApp AI message for tenant=%s", tenant_id)
                support = self.settings.support_phone or "the clinic reception"
                err_reply = (
                    "I apologize, but I am temporarily unable to complete your request. "
                    f"Please try again shortly or contact our clinic directly at {support}."
                )
                res = self.client.send_text(sender_phone, err_reply, phone_number_id=phone_number_id)
                if self.repository:
                    try:
                        out_wamid = (
                            res.get("data", {}).get("messages", [{}])[0].get("id")
                            if res and res.get("data") else None
                        )
                        self.repository.record_outbound_message(
                            tenant_id=tenant_id,
                            conversation_id=conv_id,
                            whatsapp_message_id=out_wamid,
                            phone_number=sender_phone,
                            message_type="text",
                            body=err_reply,
                            status="sent" if res.get("success") else "failed",
                            raw_payload=json.dumps(res) if res else None,
                        )
                    except Exception:
                        pass

    def _extract_message_text(self, message: WhatsAppMessage) -> tuple[str, bool]:
        """Extract user prompt from various WhatsApp message types."""
        m_type = message.type
        if m_type == "text" and message.text:
            return message.text.body.strip(), False

        if m_type == "interactive" and message.interactive:
            inter = message.interactive
            if inter.button_reply:
                return inter.button_reply.id or inter.button_reply.title, False
            if inter.list_reply:
                return inter.list_reply.id or inter.list_reply.title, False

        if m_type == "button":
            return getattr(message, "text", {}).get("body", "button_reply"), False

        if m_type in ("image", "document", "video", "sticker"):
            return "", True

        if m_type == "location" and message.location:
            loc = message.location
            return f"Patient shared location: lat={loc.latitude}, long={loc.longitude}", False

        return "", True

    async def _send_whatsapp_reply(
        self,
        recipient: str,
        response_text: str,
        state: Dict[str, Any],
        phone_number_id: str,
        is_voice: bool = False,
        tenant_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Render AI output into appropriate WhatsApp format (Interactive List, Buttons, Voice Note, or Card)."""
        flags = self._get_tenant_flags(tenant_id)
        clinic_name = self._get_clinic_name(tenant_id)
        effective_phone_id = phone_number_id if phone_number_id else self.settings.whatsapp_phone_number_id
        logger.info("=" * 60)
        logger.info(">>> [STEP 4: OUTBOUND DISPATCH]")
        logger.info("[WHATSAPP SEND] sending response")
        logger.info("[WHATSAPP SEND] phone_number_id=%s", effective_phone_id)
        logger.info("[WHATSAPP SEND] recipient=%s", recipient)
        logger.info("[WHATSAPP SEND] is_voice=%s", is_voice)

        # 1. If patient sent a voice message, synthesize and send a voice reply first (if voice_outbound enabled)
        if is_voice and is_feature_enabled(flags, FEATURE_VOICE_OUTBOUND) and self.sarvam and getattr(self.sarvam, "available", False):
            try:
                tts_text = _clean_text_for_speech(response_text)
                if tts_text:
                    from ...graph.nodes import _is_hindi_or_hinglish
                    lang = "hi" if _is_hindi_or_hinglish(tts_text) else "en"
                    logger.info(">>> [OUTBOUND VOICE NOTE] Synthesizing audio via Sarvam TTS (lang=%s, speaker=%s)...", lang, self.settings.sarvam_tts_speaker)
                    audio_bytes = await asyncio.to_thread(self.sarvam.synthesize, tts_text[:600], lang)
                    if audio_bytes:
                        logger.info("[OUTBOUND VOICE NOTE] Uploading %d bytes of Opus audio to Meta Cloud API...", len(audio_bytes))
                        media_id = await asyncio.to_thread(
                            self.client.upload_media,
                            audio_bytes,
                            "audio/ogg",
                            "voice_reply.ogg",
                            effective_phone_id,
                        )
                        if media_id:
                            voice_res = self.client.send_audio(recipient, media_id, phone_number_id=effective_phone_id)
                            logger.info(">>> [STEP 4b: VOICE NOTE DISPATCH SUCCESS] Voice note sent to WhatsApp! Meta ID: %s", media_id)
                            if self.repository and tenant_id:
                                try:
                                    v_wamid = voice_res.get("data", {}).get("messages", [{}])[0].get("id") if voice_res and voice_res.get("data") else None
                                    self.repository.record_outbound_message(
                                        tenant_id=tenant_id,
                                        conversation_id=conversation_id,
                                        whatsapp_message_id=v_wamid,
                                        phone_number=recipient,
                                        message_type="audio",
                                        body="[Voice note reply]",
                                        status="sent" if voice_res.get("success") else "failed",
                                        raw_payload=json.dumps(voice_res) if voice_res else None,
                                    )
                                except Exception:
                                    pass
            except Exception as e:
                logger.warning("Voice reply generation or sending failed: %s", e)

        # 2. Determine rich interactive messaging based on graph state UI
        interactive_enabled = is_feature_enabled(flags, FEATURE_INTERACTIVE_LISTS)
        ui = state.get("ui", "") if interactive_enabled else ""
        step = state.get("appointment_step", "") if interactive_enabled else ""
        msg_type = "text"
        res: Dict[str, Any] = {}


        # CASE A: Doctor selection interactive list
        if ui == "doctor_select" and state.get("doctor_choices"):
            choices = state.get("doctor_choices", [])
            rows = []
            for doc in choices[:10]:
                doc_id = (doc.get("Doctor ID") or "").strip()
                doc_name = (doc.get("Doctor Name") or "Doctor").strip()
                spec = (doc.get("Specialization") or "General").strip()
                fee = str(doc.get("Consultation Fee") or "").strip()
                cleaned_fee = fee.replace("Rs.", "").replace("Rs", "").replace("INR", "").replace("₹", "").strip()
                fee_disp = f"₹{cleaned_fee}" if cleaned_fee else ""
                desc = f"{spec} • {fee_disp}" if fee_disp else spec
                rows.append({
                    "id": doc_id or doc_name,
                    "title": doc_name[:24],
                    "description": desc[:72],
                })

            body_text = _format_whatsapp_markdown(response_text)
            logger.info(">>> [OUTBOUND INTERACTIVE] Sending Doctor Selection List (%d doctors)", len(rows))
            res = self.client.send_interactive_list(
                to=recipient,
                body=body_text[:1024],
                button_text="Select Doctor",
                sections=[{"title": "Available Doctors", "rows": rows}],
                header=self.settings.clinic_name[:60],
                footer="Tap 'Select Doctor' below",
                phone_number_id=effective_phone_id,
            )
            msg_type = "interactive"

        # CASE B: Slot selection (interactive buttons for <= 3, interactive list for > 3)
        elif ui == "slots" and state.get("available_slots"):
            slots = state.get("available_slots", [])
            if 1 <= len(slots) <= 3:
                buttons = [
                    {"id": f"slot:{s.get('Slot ID', '')}", "title": s.get("Start Time", "")[:20]}
                    for s in slots
                ]
                logger.info(">>> [OUTBOUND INTERACTIVE] Sending %d Slot Buttons", len(buttons))
                res = self.client.send_interactive_buttons(
                    to=recipient,
                    body=_format_whatsapp_markdown(response_text)[:1024],
                    buttons=buttons,
                    header=self.settings.clinic_name[:60],
                    phone_number_id=effective_phone_id,
                )
            else:
                rows = [
                    {
                        "id": f"slot:{s.get('Slot ID', '')}",
                        "title": f"{s.get('Start Time', '')} - {s.get('End Time', '')}"[:24],
                        "description": f"Date: {s.get('Date', '')}"[:72],
                    }
                    for s in slots[:10]
                ]
                logger.info(">>> [OUTBOUND INTERACTIVE] Sending Slot List (%d slots)", len(rows))
                res = self.client.send_interactive_list(
                    to=recipient,
                    body=_format_whatsapp_markdown(response_text)[:1024],
                    button_text="Select Time Slot",
                    sections=[{"title": "Available Slots", "rows": rows}],
                    header=self.settings.clinic_name[:60],
                    footer="Tap 'Select Time Slot' below",
                    phone_number_id=effective_phone_id,
                )
            msg_type = "interactive"

        # CASE C: Confirmation step
        elif (
            ui == "confirm"
            or step == "confirmation"
            or (
                "confirm" in response_text.lower()
                and any(w in response_text.lower() for w in ("book", "appointment", "schedule"))
                and "confirmed" not in response_text.lower()
            )
        ):
            buttons = [
                {"id": "confirm", "title": "Confirm Booking"},
                {"id": "cancel", "title": "Change / Cancel"},
            ]
            logger.info(">>> [OUTBOUND INTERACTIVE] Sending Booking Confirmation Buttons")
            res = self.client.send_interactive_buttons(
                to=recipient,
                body=_format_whatsapp_markdown(response_text)[:1024],
                buttons=buttons,
                header="Confirm Appointment"[:60],
                phone_number_id=effective_phone_id,
            )
            msg_type = "interactive"

        # CASE D: Payment step
        elif ui == "payment" or step == "payment":
            if is_feature_enabled(flags, FEATURE_ONLINE_PAYMENTS):
                buttons = [
                    {"id": "payment_offline", "title": "Pay at Clinic"},
                    {"id": "payment_online", "title": "Pay Online"},
                ]
            else:
                buttons = [
                    {"id": "payment_offline", "title": "Pay at Clinic"},
                ]
            logger.info(">>> [OUTBOUND INTERACTIVE] Sending Payment Options Buttons")

            res = self.client.send_interactive_buttons(
                to=recipient,
                body=_format_whatsapp_markdown(response_text)[:1024],
                buttons=buttons,
                header="Payment Options"[:60],
                phone_number_id=effective_phone_id,
            )
            msg_type = "interactive"

        # CASE E: Cancellation confirmation
        elif ui == "cancel_confirm":
            buttons = [
                {"id": "confirm_cancel", "title": "Yes, Cancel"},
                {"id": "keep_appointment", "title": "Keep Appointment"},
            ]
            logger.info(">>> [OUTBOUND INTERACTIVE] Sending Cancel Confirmation Buttons")
            res = self.client.send_interactive_buttons(
                to=recipient,
                body=_format_whatsapp_markdown(response_text)[:1024],
                buttons=buttons,
                header="Cancel Confirmation"[:60],
                phone_number_id=effective_phone_id,
            )
            msg_type = "interactive"

        # CASE F: Reschedule confirmation
        elif ui == "reschedule_confirm":
            buttons = [
                {"id": "confirm_reschedule", "title": "Confirm Reschedule"},
                {"id": "cancel_reschedule", "title": "Keep Current"},
            ]
            logger.info(">>> [OUTBOUND INTERACTIVE] Sending Reschedule Confirmation Buttons")
            res = self.client.send_interactive_buttons(
                to=recipient,
                body=_format_whatsapp_markdown(response_text)[:1024],
                buttons=buttons,
                header="Reschedule Confirmation"[:60],
                phone_number_id=effective_phone_id,
            )
            msg_type = "interactive"

        # CASE G: Select appointment from multiple upcoming appointments
        elif ui == "select_appointment" and state.get("upcoming_appointments"):
            appts = state.get("upcoming_appointments", [])
            rows = []
            for a in appts[:10]:
                tok = (a.get("token_no") or a.get("appointment_id") or "").strip()
                doc = (a.get("doctor") or "Doctor").strip()
                d = str(a.get("date") or "").strip()
                t = str(a.get("time") or "").strip()
                rows.append({
                    "id": tok,
                    "title": f"Dr. {doc}"[:24],
                    "description": f"{d} at {t} (Token: {tok})"[:72],
                })
            logger.info(">>> [OUTBOUND INTERACTIVE] Sending Appointment Selection List (%d appts)", len(rows))
            res = self.client.send_interactive_list(
                to=recipient,
                body=_format_whatsapp_markdown(response_text)[:1024],
                button_text="Select Appointment",
                sections=[{"title": "Your Appointments", "rows": rows}],
                header="Upcoming Appointments"[:60],
                phone_number_id=effective_phone_id,
            )
            msg_type = "interactive"

        # CASE H: Default Clean Formatted Text Message
        else:
            clean_text = _format_whatsapp_markdown(response_text)
            res = self.client.send_text(
                to=recipient,
                text=clean_text,
                phone_number_id=effective_phone_id,
            )
            msg_type = "text"

        logger.info("[WHATSAPP SEND] API response status=%s", res.get("status_code"))
        logger.info("[WHATSAPP SEND] API response body=%s", res.get("raw_response") or json.dumps(res.get("data") or {}))

        if res.get("success"):
            out_wamid = (
                res.get("data", {}).get("messages", [{}])[0].get("id")
                if res and res.get("data") else "unknown"
            )
            logger.info("=" * 60)
            logger.info(">>> [STEP 5: DISPATCH SUCCESS] HTTP %s OK | Meta Message ID: %s", res.get("status_code"), out_wamid)
            logger.info(">>> [DELIVERY STATUS] Response message delivered to patient's WhatsApp!")
            logger.info("=" * 60)
        else:
            status_code = res.get("status_code")
            raw_err = res.get("error") or res.get("raw_response") or "Unknown error"
            logger.error("!" * 60)
            logger.error(">>> [STEP 5: DISPATCH FAILED] Meta Cloud API Error (HTTP %s)", status_code)
            logger.error(">>> Error Detail: %s", raw_err)
            if status_code == 401 or "Session has expired" in str(raw_err):
                logger.error(">>> [ROOT CAUSE] Meta Access Token has EXPIRED!")
                logger.error(">>> [HOW TO FIX] 1. Go to developers.facebook.com -> Your App -> WhatsApp -> API Setup")
                logger.error(">>>              2. Copy the fresh 'Temporary access token' (or generate system user token)")
                logger.error(">>>              3. Update WHATSAPP_ACCESS_TOKEN in .env and restart server.")
            elif status_code == 400:
                logger.error(">>> [ROOT CAUSE] Invalid parameter, unverified test recipient, or outside 24h window.")
            logger.error("!" * 60)

        if self.repository and tenant_id:
            try:
                out_wamid = (
                    res.get("data", {}).get("messages", [{}])[0].get("id")
                    if res and res.get("data") else None
                )
                self.repository.record_outbound_message(
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    whatsapp_message_id=out_wamid,
                    phone_number=recipient,
                    message_type=msg_type,
                    body=response_text,
                    status="sent" if res.get("success") else "failed",
                    raw_payload=json.dumps(res) if res else None,
                    error_details=res.get("error") if not res.get("success") else None,
                )
            except Exception:
                logger.exception("Failed to record outbound WhatsApp message in repository.")

        return res
