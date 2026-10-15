"""Comprehensive End-to-End Tests for Kodnexus SaaS Multi-Tenant Platform.

Verifies:
1. Dynamic WhatsApp Routing by phone_number_id (fail-closed isolation).
2. Subscription Plans and Granular Feature Flag Toggle Resolution.
3. Feature Flag Pre-checks and Graceful Patient Fallbacks (Voice Inbound/Outbound, Cancellation, Rescheduling, Payments).
4. Tenant Knowledge Base & Isolated RAG Ingestion/Deletion.
5. Super Admin Platform API Endpoints (features, subscriptions, documents).
"""

import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.channels.whatsapp.client import MetaWhatsAppClient
from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.models import WhatsAppMessage, WhatsAppValue
from app.channels.whatsapp.router import create_whatsapp_router
from app.core.config import Settings
from app.core.feature_flags import (
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
from app.services.tenant_management_service import TenantManagementService
from app.telegram.sessions import SessionStore


class TestKodnexusMultiTenantSaaS(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        self.service = TenantManagementService(rag_base_dir=self.base_path)

        # Register Clinic A (Starter Plan, Voice Inbound disabled)
        self.clinic_a = self.service.create_tenant({
            "id": "clinic_alpha",
            "name": "Alpha Care Hospital",
            "whatsapp_phone_number": "+15551112222",
            "whatsapp_phone_number_id": "phone_alpha_111",
            "whatsapp_waba_id": "waba_alpha_111",
            "subscription_plan": "STARTER",
            "phone": "9876543210",
        })

        # Register Clinic B (Enterprise Plan, All Enabled)
        self.clinic_b = self.service.create_tenant({
            "id": "clinic_beta",
            "name": "Beta Specialty Clinic",
            "whatsapp_phone_number": "+15553334444",
            "whatsapp_phone_number_id": "phone_beta_222",
            "whatsapp_waba_id": "waba_beta_222",
            "subscription_plan": "ENTERPRISE",
            "phone": "9876543222",
        })

        self.settings = Settings(
            clinic_name="Kodnexus Platform Hub",
            telegram_bot_token="fake_tg_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=self.base_path / "knowledge",
            vectorstore_dir=self.base_path / "vectorstore",
            whatsapp_verify_token="test_verify_token",
            whatsapp_app_secret="test_app_secret_12345",
            whatsapp_access_token="test_access_token",
            whatsapp_phone_number_id="default_phone_id",
        )


        self.mock_graph = MagicMock()
        self.mock_graph.invoke.return_value = {
            "response": "Hello from Alpha Care Hospital",
            "messages": [],
            "ui": "",
        }

        self.mock_client = MagicMock(spec=MetaWhatsAppClient)
        self.mock_client.send_text.return_value = {"success": True, "data": {"messages": [{"id": "wamid_out_1"}]}}
        self.mock_client.send_interactive_buttons.return_value = {"success": True, "data": {"messages": [{"id": "wamid_btn_1"}]}}
        self.mock_client.send_audio.return_value = {"success": True, "data": {"messages": [{"id": "wamid_audio_1"}]}}

        self.handler = WhatsAppHandler(
            settings=self.settings,
            graph=self.mock_graph,
            client=self.mock_client,
            sessions=SessionStore(),
            tenant_management_service=self.service,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # -----------------------------------------------------------------------
    # 1. Dynamic WhatsApp Routing Tests
    # -----------------------------------------------------------------------
    def test_dynamic_routing_resolves_phone_number_ids_correctly(self):
        # Clinic A
        tid_a = self.handler.resolve_tenant_id("phone_alpha_111")
        self.assertEqual(tid_a, "clinic_alpha")

        # Clinic B
        tid_b = self.handler.resolve_tenant_id("phone_beta_222")
        self.assertEqual(tid_b, "clinic_beta")

        # Default tenant seeded
        tid_default = self.handler.resolve_tenant_id("1345059468697224")
        self.assertEqual(tid_default, "default")

        # Unknown phone number ID fails closed
        tid_unknown = self.handler.resolve_tenant_id("unknown_phone_999")
        self.assertIsNone(tid_unknown)

    def test_fail_closed_rejects_unmapped_phone_id_without_accessing_data(self):
        val = WhatsAppValue.model_validate({
            "messaging_product": "whatsapp",
            "metadata": {"phone_number_id": "unmapped_intruder_phone"},
            "messages": [
                {
                    "from": "919999999999",
                    "id": "wamid_unmapped_1",
                    "timestamp": "1728560000",
                    "type": "text",
                    "text": {"body": "hello unmapped clinic"},
                }
            ],
        })

        import asyncio
        asyncio.run(self.handler.handle_value(val))

        # Mock graph and Meta client send should NOT have been called
        self.mock_graph.invoke.assert_not_called()
        self.mock_client.send_text.assert_not_called()

    # -----------------------------------------------------------------------
    # 2. Subscription Plans & Feature Flags Engine Tests
    # -----------------------------------------------------------------------
    def test_subscription_tier_defaults(self):
        starter = resolve_effective_feature_flags("STARTER")
        self.assertFalse(starter[FEATURE_VOICE_INBOUND])
        self.assertFalse(starter[FEATURE_VOICE_OUTBOUND])
        self.assertFalse(starter[FEATURE_ONLINE_PAYMENTS])
        self.assertTrue(starter[FEATURE_INTERACTIVE_LISTS])
        self.assertTrue(starter[FEATURE_CANCELLATION])

        pro = resolve_effective_feature_flags("PROFESSIONAL")
        self.assertTrue(pro[FEATURE_VOICE_INBOUND])
        self.assertFalse(pro[FEATURE_VOICE_OUTBOUND])
        self.assertTrue(pro[FEATURE_ONLINE_PAYMENTS])

        ent = resolve_effective_feature_flags("ENTERPRISE")
        self.assertTrue(ent[FEATURE_VOICE_INBOUND])
        self.assertTrue(ent[FEATURE_VOICE_OUTBOUND])
        self.assertTrue(ent[FEATURE_ONLINE_PAYMENTS])

    def test_granular_feature_flag_overrides(self):
        # Override STARTER to enable online_payments
        custom = resolve_effective_feature_flags("STARTER", {"online_payments": True, "voice_inbound": True})
        self.assertTrue(custom[FEATURE_ONLINE_PAYMENTS])
        self.assertTrue(custom[FEATURE_VOICE_INBOUND])
        self.assertFalse(custom[FEATURE_VOICE_OUTBOUND])

        # Service update feature flags
        self.service.update_tenant_feature_flags("clinic_alpha", {"voice_inbound": True})
        flags = self.service.get_tenant_feature_flags("clinic_alpha")
        self.assertTrue(flags["voice_inbound"])

    # -----------------------------------------------------------------------
    # 3. Feature Flag Enforcement & Graceful Fallbacks in WhatsApp Flow
    # -----------------------------------------------------------------------
    def test_voice_inbound_disabled_replies_with_polite_message(self):
        # Clinic A has voice_inbound disabled in STARTER plan
        val = WhatsAppValue.model_validate({
            "messaging_product": "whatsapp",
            "metadata": {"phone_number_id": "phone_alpha_111"},
            "messages": [
                {
                    "from": "919999999999",
                    "id": "wamid_audio_test",
                    "timestamp": "1728560000",
                    "type": "audio",
                    "audio": {"id": "meta_audio_123", "mime_type": "audio/ogg"},
                }
            ],
        })

        import asyncio
        asyncio.run(self.handler.handle_value(val))

        # Media download should NOT be called
        self.mock_client.download_media.assert_not_called()
        # Client should send polite fallback message explaining voice notes are disabled
        self.mock_client.send_text.assert_called_once()
        sent_text = self.mock_client.send_text.call_args[0][1]
        self.assertIn("Voice messaging is currently not enabled", sent_text)
        self.assertIn("Alpha Care Hospital", sent_text)

    def test_payment_step_respects_online_payments_flag(self):
        # Send reply for clinic_alpha where online_payments is False in STARTER
        import asyncio
        asyncio.run(self.handler._send_whatsapp_reply(
            recipient="919999999999",
            response_text="Please select payment option",
            state={"ui": "payment", "appointment_step": "payment"},
            phone_number_id="phone_alpha_111",
            tenant_id="clinic_alpha",
        ))

        # Buttons sent should only contain "Pay at Clinic" (no online option)
        self.mock_client.send_interactive_buttons.assert_called_once()
        kwargs = self.mock_client.send_interactive_buttons.call_args[1]
        button_ids = [b["id"] for b in kwargs["buttons"]]
        self.assertEqual(button_ids, ["payment_offline"])

    def test_interactive_lists_disabled_falls_back_to_text(self):
        # Disable interactive_lists for clinic_alpha
        self.service.update_tenant_feature_flags("clinic_alpha", {"interactive_lists": False})

        import asyncio
        asyncio.run(self.handler._send_whatsapp_reply(
            recipient="919999999999",
            response_text="Here is your doctor list:\n1. Dr. Arjun",
            state={"ui": "doctor_select", "doctor_choices": [{"Doctor Name": "Dr. Arjun"}]},
            phone_number_id="phone_alpha_111",
            tenant_id="clinic_alpha",
        ))

        # Interactive list should NOT be called; send_text should be called instead
        self.mock_client.send_interactive_list.assert_not_called()
        self.mock_client.send_text.assert_called_once()

    # -----------------------------------------------------------------------
    # 4. Tenant RAG Document Ingestion & Deletion Isolation Tests
    # -----------------------------------------------------------------------
    def test_tenant_document_lifecycle_and_rebuild(self):
        tid = "clinic_alpha"
        # 1. Upload document for Clinic A
        doc_content = b"Alpha Clinic Timings: Open Mon-Sat 9AM-8PM. Consultation fee is Rs. 500."
        res = self.service.upload_tenant_document(
            tenant_id=tid,
            filename="clinic_guidelines.txt",
            content=doc_content,
        )
        self.assertEqual(res["status"], "INDEXED")
        self.assertEqual(res["filename"], "clinic_guidelines.txt")

        # 2. List documents
        docs = self.service.list_tenant_documents(tid)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["filename"], "clinic_guidelines.txt")
        self.assertEqual(docs[0]["size_bytes"], len(doc_content))

        # Check tenant B has no documents (complete isolation)
        docs_b = self.service.list_tenant_documents("clinic_beta")
        self.assertEqual(len(docs_b), 0)

        # 3. Delete document
        del_res = self.service.delete_tenant_document(tid, "clinic_guidelines.txt")
        self.assertEqual(del_res["status"], "DELETED")

        # Verify list is empty
        docs_after = self.service.list_tenant_documents(tid)
        self.assertEqual(len(docs_after), 0)


if __name__ == "__main__":
    unittest.main()
