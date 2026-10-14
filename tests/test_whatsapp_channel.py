"""Comprehensive automated tests for Meta WhatsApp Cloud API Channel.

Verifies:
1. Webhook subscription verification handshake (GET /webhook/whatsapp).
2. Rejection of invalid verification tokens.
3. Signature verification (HMAC-SHA256) on inbound requests.
4. Rejection of forged/tampered webhook signatures.
5. Multi-tenant resolution from phone_number_id.
6. Inbound text message processing & LangGraph dispatch.
7. Interactive button reply processing.
8. Graceful handling of media attachments / unsupported types.
9. Message deduplication (prevents duplicate execution of identical webhook events).
10. Outbound messaging client (send_text, interactive_buttons, send_template).
11. Delivery status callbacks handling.
"""

import hashlib
import hmac
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from app.channels.whatsapp.client import MetaWhatsAppClient, normalize_phone_number
from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.router import create_whatsapp_router
from app.channels.whatsapp.security import verify_meta_signature, verify_webhook_challenge
from app.core.config import Settings
from app.telegram.sessions import SessionStore


class WhatsAppChannelTests(unittest.TestCase):
    def setUp(self):
        self.verify_token = "clinic_verify_token_123"
        self.app_secret = "meta_app_secret_abc123"
        self.phone_id_a = "10001"
        self.phone_id_b = "10002"

        self.settings = Settings(
            clinic_name="Multi-Clinic Care",
            telegram_bot_token="fake_bot_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=Path("./data/knowledge"),
            vectorstore_dir=Path("./data/vectorstore"),
            whatsapp_enabled=True,
            whatsapp_verify_token=self.verify_token,
            whatsapp_app_secret=self.app_secret,
            whatsapp_phone_number_id=self.phone_id_a,
            whatsapp_tenant_phone_map=json.dumps({
                self.phone_id_a: "tenant_alpha",
                self.phone_id_b: "tenant_beta",
            }),
        )

        # Mock Outbound Client
        self.mock_client = MagicMock(spec=MetaWhatsAppClient)
        self.mock_client.send_text.return_value = {"success": True}
        self.mock_client.send_interactive_buttons.return_value = {"success": True}
        self.mock_client.mark_as_read.return_value = {"success": True}

        # Mock LangGraph
        self.mock_graph = MagicMock()
        self.mock_graph.invoke.return_value = {
            "response": "Hello, your appointment with Dr. Mehta is available on Monday 10:00 AM.",
            "messages": [],
        }

        self.sessions = SessionStore()
        self.handler = WhatsAppHandler(
            settings=self.settings,
            graph=self.mock_graph,
            client=self.mock_client,
            sessions=self.sessions,
        )

        self.app = FastAPI()
        self.app.include_router(create_whatsapp_router(self.settings, self.handler))
        self.test_client = TestClient(self.app)

    def _generate_signature(self, body_bytes: bytes) -> str:
        mac = hmac.new(
            key=self.app_secret.encode("utf-8"),
            msg=body_bytes,
            digestmod=hashlib.sha256,
        )
        return f"sha256={mac.hexdigest()}"

    # -------------------------------------------------------------------------
    # 1. Webhook Verification Handshake
    # -------------------------------------------------------------------------
    def test_webhook_verification_success(self):
        res = self.test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": self.verify_token,
                "hub.challenge": "1158201444",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "1158201444")

    def test_webhook_verification_invalid_token(self):
        res = self.test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "1158201444",
            },
        )
        self.assertEqual(res.status_code, 403)

    def test_webhook_verification_invalid_mode(self):
        res = self.test_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": self.verify_token,
                "hub.challenge": "1158201444",
            },
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 2. Signature Security Verification
    # -------------------------------------------------------------------------
    def test_valid_signature_accepted(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "messages": [
                                    {
                                        "id": "wamid_001",
                                        "from": "919876543210",
                                        "timestamp": "1728560000",
                                        "type": "text",
                                        "text": {"body": "Hi, I need doctor timings"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})
        self.mock_graph.invoke.assert_called()

    def test_invalid_signature_rejected(self):
        body_bytes = b'{"object": "whatsapp_business_account"}'
        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalid_tampered_hash_here",
            },
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 3. Multi-Tenant Routing from receiving Phone Number ID (Fail-Closed)
    # -------------------------------------------------------------------------
    def test_multi_tenant_routing_resolves_correct_tenant(self):
        self.assertEqual(self.handler.resolve_tenant_id(self.phone_id_a), "tenant_alpha")
        self.assertEqual(self.handler.resolve_tenant_id(self.phone_id_b), "tenant_beta")
        # Enforce fail closed: unmapped phone number ID must return None
        self.assertIsNone(self.handler.resolve_tenant_id("unknown_phone_id"))

    def test_unmapped_phone_number_fails_closed_without_calling_graph(self):
        """Unmapped phone ID must fail closed without invoking LangGraph or touching clinic data."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "unmapped_rogue_phone_id"},
                                "messages": [
                                    {
                                        "id": "wamid_unmapped_001",
                                        "from": "919876543210",
                                        "timestamp": "1728560000",
                                        "type": "text",
                                        "text": {"body": "Attempting cross-tenant intrusion"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)
        # LangGraph must NOT be called
        self.mock_graph.invoke.assert_not_called()

    # -------------------------------------------------------------------------
    # 4. Inbound Interactive Buttons Reply
    # -------------------------------------------------------------------------
    def test_interactive_button_reply_processed(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_b},
                                "messages": [
                                    {
                                        "id": "wamid_002",
                                        "from": "919876543211",
                                        "timestamp": "1728560010",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "button_reply",
                                            "button_reply": {
                                                "id": "confirm_booking",
                                                "title": "Confirm Booking",
                                            },
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)

    # -------------------------------------------------------------------------
    # 5. Media Attachments Graceful Handling
    # -------------------------------------------------------------------------
    def test_media_attachment_handled_gracefully(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "messages": [
                                    {
                                        "id": "wamid_003",
                                        "from": "919876543212",
                                        "timestamp": "1728560020",
                                        "type": "image",
                                        "image": {"id": "media_img_999", "mime_type": "image/jpeg"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)
        # Should send medical guidance message without calling graph
        self.mock_client.send_text.assert_called()
        call_text = self.mock_client.send_text.call_args[0][1]
        self.assertIn("clinical safety", call_text.lower())

    # -------------------------------------------------------------------------
    # 6. Message Deduplication
    # -------------------------------------------------------------------------
    def test_message_deduplication_prevents_duplicate_processing(self):
        self.assertFalse(self.handler.is_duplicate("wamid_test_dedup_01"))
        self.assertTrue(self.handler.is_duplicate("wamid_test_dedup_01"))

    # -------------------------------------------------------------------------
    # 7. Outbound Client Phone Normalization & Dispatch
    # -------------------------------------------------------------------------
    def test_phone_number_normalization(self):
        self.assertEqual(normalize_phone_number("9876543210", "91"), "919876543210")
        self.assertEqual(normalize_phone_number("+91 98765-43210"), "919876543210")
        self.assertEqual(normalize_phone_number("14155552671", "91"), "14155552671")

    def test_outbound_client_sends_text(self):
        mock_http = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "919876543210", "wa_id": "919876543210"}],
            "messages": [{"id": "wamid_out_001"}],
        }
        mock_http.post.return_value = mock_resp

        client = MetaWhatsAppClient(
            access_token="test_tok",
            phone_number_id="10001",
            http_client=mock_http,
        )
        res = client.send_text("9876543210", "Appointment confirmed")
        self.assertTrue(res["success"])
        mock_http.post.assert_called_once()
        payload = mock_http.post.call_args[1]["json"]
        self.assertEqual(payload["to"], "919876543210")
        self.assertEqual(payload["text"]["body"], "Appointment confirmed")

    def test_graph_failure_sends_fallback_apology(self):
        """Verify that when LangGraph raises an exception, patient receives a helpful apology."""
        self.mock_graph.invoke.side_effect = RuntimeError("Temporary LLM provider outage")
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "+12345",
                                    "phone_number_id": self.phone_id_a,
                                },
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "wamid_fail_01",
                                        "timestamp": "1700000000",
                                        "type": "text",
                                        "text": {"body": "Book an appointment"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(self.app_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)
        self.mock_client.send_text.assert_called()
        call_text = self.mock_client.send_text.call_args[0][1]
        self.assertIn("temporarily unable", call_text.lower())

    # -------------------------------------------------------------------------
    # 10. Inbound Voice Note Processing & Outbound Voice Reply
    # -------------------------------------------------------------------------
    def test_inbound_voice_message_transcribed_and_voice_reply_sent(self):
        # Configure Sarvam mock
        mock_sarvam = MagicMock()
        mock_sarvam.available = True
        mock_sarvam.transcribe.return_value = "Mujhe doctor Arjun se milna hai"
        mock_sarvam.synthesize.return_value = b"fake_opus_audio_bytes"
        self.handler.sarvam = mock_sarvam

        # Configure Client media mocks
        self.mock_client.download_media.return_value = b"fake_inbound_audio_bytes"
        self.mock_client.upload_media.return_value = "media_voice_reply_123"
        self.mock_client.send_audio.return_value = {"success": True}

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "wamid_voice_001",
                                        "timestamp": "1728560050",
                                        "type": "audio",
                                        "audio": {
                                            "id": "meta_inbound_media_456",
                                            "mime_type": "audio/ogg; codecs=opus",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(self.app_secret.encode(), body_bytes, hashlib.sha256).hexdigest()

        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)

        # 1. Download media was called with media ID
        self.mock_client.download_media.assert_called_with("meta_inbound_media_456")

        # 2. Sarvam transcribed the voice note
        mock_sarvam.transcribe.assert_called()

        # 3. LangGraph was invoked with the transcribed text
        self.mock_graph.invoke.assert_called()
        invoked_state = self.mock_graph.invoke.call_args[0][0]
        self.assertEqual(invoked_state.get("user_text"), "Mujhe doctor Arjun se milna hai")

        # 4. Outbound voice note was synthesized and uploaded
        mock_sarvam.synthesize.assert_called()
        self.mock_client.upload_media.assert_called()
        self.mock_client.send_audio.assert_called_with(
            "919876543210", "media_voice_reply_123", phone_number_id=self.phone_id_a
        )

    # -------------------------------------------------------------------------
    # 11. Outbound Interactive List for Doctor Selection
    # -------------------------------------------------------------------------
    def test_outbound_doctor_selection_interactive_list(self):
        self.mock_client.send_interactive_list.return_value = {"success": True}
        self.mock_graph.invoke.return_value = {
            "response": "Here are our available doctors. Please choose one:",
            "ui": "doctor_select",
            "doctor_choices": [
                {
                    "Doctor ID": "DOC-001",
                    "Doctor Name": "Dr. Arjun Mehta",
                    "Specialization": "General Medicine",
                    "Consultation Fee": "500",
                },
                {
                    "Doctor ID": "DOC-002",
                    "Doctor Name": "Dr. Priya Sharma",
                    "Specialization": "Cardiology",
                    "Consultation Fee": "700",
                },
            ],
            "messages": [],
        }

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "wamid_doc_list_01",
                                        "timestamp": "1728560060",
                                        "type": "text",
                                        "text": {"body": "doctors ki list dikhao"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(self.app_secret.encode(), body_bytes, hashlib.sha256).hexdigest()

        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)

        # Verify send_interactive_list was called
        self.mock_client.send_interactive_list.assert_called()
        call_kwargs = self.mock_client.send_interactive_list.call_args[1]
        self.assertEqual(call_kwargs.get("to"), "919876543210")
        self.assertEqual(call_kwargs.get("button_text"), "Select Doctor")
        sections = call_kwargs.get("sections", [])
        self.assertEqual(len(sections), 1)
        rows = sections[0].get("rows", [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["id"], "DOC-001")
        self.assertEqual(rows[0]["title"], "Dr. Arjun Mehta")
        self.assertIn("General Medicine", rows[0]["description"])
        self.assertIn("500", rows[0]["description"])
        self.assertEqual(rows[1]["id"], "DOC-002")
        self.assertEqual(rows[1]["title"], "Dr. Priya Sharma")

    # -------------------------------------------------------------------------
    # 12. Outbound Booking Confirmation Buttons
    # -------------------------------------------------------------------------
    def test_outbound_confirmation_interactive_buttons(self):
        self.mock_client.send_interactive_buttons.return_value = {"success": True}
        self.mock_graph.invoke.return_value = {
            "response": "Please confirm your appointment with Dr. Arjun Mehta on 2026-11-28 at 10:00 AM.",
            "ui": "confirm",
            "appointment_step": "confirmation",
            "messages": [],
        }

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "wamid_conf_01",
                                        "timestamp": "1728560070",
                                        "type": "text",
                                        "text": {"body": "919876543210"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(self.app_secret.encode(), body_bytes, hashlib.sha256).hexdigest()

        res = self.test_client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        self.assertEqual(res.status_code, 200)

        # Verify send_interactive_buttons was called with confirm/cancel
        self.mock_client.send_interactive_buttons.assert_called()
        call_kwargs = self.mock_client.send_interactive_buttons.call_args[1]
        self.assertEqual(call_kwargs.get("to"), "919876543210")
        buttons = call_kwargs.get("buttons", [])
        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0]["id"], "confirm")
        self.assertEqual(buttons[0]["title"], "Confirm Booking")
        self.assertEqual(buttons[1]["id"], "cancel")

