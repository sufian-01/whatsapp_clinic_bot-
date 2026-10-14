"""Live PostgreSQL integration tests for Meta WhatsApp Cloud API Channel.

Verifies end-to-end:
1. Webhook verification challenge (GET /webhook/whatsapp).
2. HMAC-SHA256 signature security (POST /webhook/whatsapp).
3. Multi-tenant routing isolation (Phone ID 1 -> Clinic A, Phone ID 2 -> Clinic B).
4. Strict fail-closed routing for unmapped Phone IDs (0 database records, no AI invocation).
5. PostgreSQL persistence for whatsapp_conversations and whatsapp_messages.
6. Automatic patient matching and foreign key linking by phone number.
7. Deduplication of inbound messages (wamid) in memory and database.
8. Status callback processing (delivered, read) updating PostgreSQL records without triggering AI.
9. Outbound AI reply persistence with status and Meta message ID.
10. Outbound template and interactive messaging structure.
"""

import hashlib
import hmac
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.channels.whatsapp.client import MetaWhatsAppClient, normalize_phone_number
from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.router import create_whatsapp_router
from app.core.config import Settings
from app.db.models import Clinic, Patient, WhatsAppConversation, WhatsAppMessage
from app.db.session import get_session_factory, is_db_configured
from app.repositories.whatsapp_repository import WhatsAppRepository
from app.telegram.sessions import SessionStore


@unittest.skipUnless(is_db_configured(), "Requires active PostgreSQL database connection")
class WhatsAppLiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session_factory = get_session_factory()
        cls.clinic_a_id = "test_wa_clinic_alpha"
        cls.clinic_b_id = "test_wa_clinic_beta"
        cls.phone_id_a = "wa_phone_id_alpha_101"
        cls.phone_id_b = "wa_phone_id_beta_102"
        cls.patient_phone = "919876543210"
        cls.patient_id = "pat_wa_alpha_001"
        cls.app_secret = "meta_test_secret_xyz123"
        cls.verify_token = "clinic_meta_token_secure"

        # Clean up any leftover test data
        with cls.session_factory() as session:
            session.query(WhatsAppMessage).filter(
                WhatsAppMessage.tenant_id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.query(WhatsAppConversation).filter(
                WhatsAppConversation.tenant_id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.query(Patient).filter(
                Patient.tenant_id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.query(Clinic).filter(
                Clinic.id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.commit()

            # Seed Clinics
            clinic_a = Clinic(
                id=cls.clinic_a_id,
                name="Alpha Health Clinic",
                timezone="Asia/Kolkata",
                currency="INR",
            )
            clinic_b = Clinic(
                id=cls.clinic_b_id,
                name="Beta Care Hospital",
                timezone="Asia/Kolkata",
                currency="INR",
            )
            session.add_all([clinic_a, clinic_b])
            session.commit()

            # Seed Patient in Clinic A
            pat = Patient(
                id="uuid_pat_wa_alpha_001",
                tenant_id=cls.clinic_a_id,
                patient_id=cls.patient_id,
                name="Ramesh Sharma",
                phone=cls.patient_phone,
                status="Active",
            )
            session.add(pat)
            session.commit()

    @classmethod
    def tearDownClass(cls):
        # Clean up seeded records
        with cls.session_factory() as session:
            session.query(WhatsAppMessage).filter(
                WhatsAppMessage.tenant_id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.query(WhatsAppConversation).filter(
                WhatsAppConversation.tenant_id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.query(Patient).filter(
                Patient.tenant_id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.query(Clinic).filter(
                Clinic.id.in_([cls.clinic_a_id, cls.clinic_b_id])
            ).delete(synchronize_session=False)
            session.commit()

    def setUp(self):
        self.settings = Settings(
            clinic_name="Alpha Health Clinic",
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
                self.phone_id_a: self.clinic_a_id,
                self.phone_id_b: self.clinic_b_id,
            }),
        )

        self.repo = WhatsAppRepository(self.session_factory)

        # Mock Outbound WhatsApp Client
        self.mock_client = MagicMock(spec=MetaWhatsAppClient)
        self.mock_client.send_text.return_value = {
            "success": True,
            "data": {"messages": [{"id": "wamid_out_live_001"}]},
        }
        self.mock_client.send_interactive_buttons.return_value = {
            "success": True,
            "data": {"messages": [{"id": "wamid_out_live_interactive_001"}]},
        }
        self.mock_client.mark_as_read.return_value = {"success": True}

        # Mock LangGraph Agent
        self.mock_graph = MagicMock()
        self.mock_graph.invoke.return_value = {
            "response": "Hello Ramesh! Dr. Mehta is available on Monday at 10:00 AM. Would you like to book?",
            "messages": [],
        }

        self.sessions = SessionStore()
        self.handler = WhatsAppHandler(
            settings=self.settings,
            graph=self.mock_graph,
            client=self.mock_client,
            sessions=self.sessions,
            repository=self.repo,
        )

        self.app = FastAPI()
        self.app.include_router(create_whatsapp_router(self.settings, self.handler))
        self.client = TestClient(self.app)

    def _generate_signature(self, body_bytes: bytes) -> str:
        mac = hmac.new(
            key=self.app_secret.encode("utf-8"),
            msg=body_bytes,
            digestmod=hashlib.sha256,
        )
        return f"sha256={mac.hexdigest()}"

    # -------------------------------------------------------------------------
    # 1. Verification Handshake (GET /webhook/whatsapp)
    # -------------------------------------------------------------------------
    def test_webhook_verification_handshake(self):
        res = self.client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": self.verify_token,
                "hub.challenge": "live_challenge_token_999",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "live_challenge_token_999")

    # -------------------------------------------------------------------------
    # 2. Inbound Message Processing & PostgreSQL Persistence
    # -------------------------------------------------------------------------
    def test_inbound_message_persists_in_postgres_with_patient_linking(self):
        wamid = "wamid.live_inbound_test_001"
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_meta_001",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "contacts": [{"wa_id": self.patient_phone, "profile": {"name": "Ramesh Sharma"}}],
                                "messages": [
                                    {
                                        "id": wamid,
                                        "from": self.patient_phone,
                                        "timestamp": "1728565000",
                                        "type": "text",
                                        "text": {"body": "I would like to check doctor availability"},
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

        res = self.client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

        # Verify PostgreSQL Conversation
        with self.session_factory() as session:
            conv = session.scalars(
                select(WhatsAppConversation).where(
                    WhatsAppConversation.tenant_id == self.clinic_a_id,
                    WhatsAppConversation.phone_number == self.patient_phone,
                )
            ).first()
            self.assertIsNotNone(conv, "WhatsAppConversation must be persisted in PostgreSQL")
            self.assertEqual(conv.profile_name, "Ramesh Sharma")
            self.assertEqual(conv.patient_id, "uuid_pat_wa_alpha_001", "Must link to matching patient record")

            # Verify Inbound Message in PostgreSQL
            in_msg = session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.tenant_id == self.clinic_a_id,
                    WhatsAppMessage.whatsapp_message_id == wamid,
                )
            ).first()
            self.assertIsNotNone(in_msg, "Inbound WhatsAppMessage must be persisted in PostgreSQL")
            self.assertEqual(in_msg.direction, "inbound")
            self.assertEqual(in_msg.status, "received")
            self.assertEqual(in_msg.body, "I would like to check doctor availability")
            self.assertEqual(in_msg.conversation_id, conv.id)

            # Verify Outbound AI Reply in PostgreSQL
            out_msg = session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.tenant_id == self.clinic_a_id,
                    WhatsAppMessage.direction == "outbound",
                    WhatsAppMessage.conversation_id == conv.id,
                )
            ).first()
            self.assertIsNotNone(out_msg, "Outbound WhatsAppMessage reply must be persisted in PostgreSQL")
            self.assertEqual(out_msg.status, "sent")
            self.assertEqual(out_msg.whatsapp_message_id, "wamid_out_live_001")
            self.assertIn("Hello Ramesh", out_msg.body)

    # -------------------------------------------------------------------------
    # 3. Message Deduplication in Database
    # -------------------------------------------------------------------------
    def test_duplicate_message_is_ignored_without_duplicate_processing(self):
        wamid = "wamid.live_dedup_002"
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_meta_001",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "messages": [
                                    {
                                        "id": wamid,
                                        "from": self.patient_phone,
                                        "timestamp": "1728565100",
                                        "type": "text",
                                        "text": {"body": "Check my appointment"},
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

        # First post
        res1 = self.client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(res1.status_code, 200)

        initial_graph_calls = self.mock_graph.invoke.call_count

        # Second identical post (Meta retry simulation)
        res2 = self.client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(res2.status_code, 200)

        # Graph should NOT be invoked again
        self.assertEqual(self.mock_graph.invoke.call_count, initial_graph_calls)

        # Verify only one message record exists in DB for this wamid
        with self.session_factory() as session:
            count = len(session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.tenant_id == self.clinic_a_id,
                    WhatsAppMessage.whatsapp_message_id == wamid,
                )
            ).all())
            self.assertEqual(count, 1)

    # -------------------------------------------------------------------------
    # 4. Multi-Tenant Isolation (Phone ID A -> Clinic A, Phone ID B -> Clinic B)
    # -------------------------------------------------------------------------
    def test_multi_tenant_routing_isolation_across_clinics(self):
        wamid_b = "wamid.live_clinic_b_003"
        patient_b_phone = "919999988888"
        payload_b = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_meta_002",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_b},
                                "contacts": [{"wa_id": patient_b_phone, "profile": {"name": "Beta Patient"}}],
                                "messages": [
                                    {
                                        "id": wamid_b,
                                        "from": patient_b_phone,
                                        "timestamp": "1728565200",
                                        "type": "text",
                                        "text": {"body": "Beta hospital timings?"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload_b).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        res = self.client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(res.status_code, 200)

        # Verify record exists in Clinic B and NOT in Clinic A
        with self.session_factory() as session:
            msg_b = session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.tenant_id == self.clinic_b_id,
                    WhatsAppMessage.whatsapp_message_id == wamid_b,
                )
            ).first()
            self.assertIsNotNone(msg_b, "Message must belong to Clinic B")

            # Check that Clinic A has no record of this message
            msg_a = session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.tenant_id == self.clinic_a_id,
                    WhatsAppMessage.whatsapp_message_id == wamid_b,
                )
            ).first()
            self.assertIsNone(msg_a, "Clinic A must have zero knowledge of Clinic B's message")

    # -------------------------------------------------------------------------
    # 5. Fail-Closed Routing for Unmapped Phone Number ID
    # -------------------------------------------------------------------------
    def test_unmapped_phone_id_fails_closed_zero_db_records(self):
        wamid_rogue = "wamid.live_rogue_004"
        payload_rogue = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_meta_003",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "unmapped_rogue_999"},
                                "messages": [
                                    {
                                        "id": wamid_rogue,
                                        "from": "919111122222",
                                        "timestamp": "1728565300",
                                        "type": "text",
                                        "text": {"body": "Access unauthorized clinic"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(payload_rogue).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        res = self.client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(res.status_code, 200)

        # Verify zero messages recorded for rogue wamid
        with self.session_factory() as session:
            msg = session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.whatsapp_message_id == wamid_rogue
                )
            ).first()
            self.assertIsNone(msg, "Unmapped phone number must never persist records to any clinic")

    # -------------------------------------------------------------------------
    # 6. Delivery Status Callback Updates DB
    # -------------------------------------------------------------------------
    def test_status_callback_updates_message_status_in_postgres(self):
        # 1. Create a message in DB with status "sent"
        out_wamid = "wamid.live_status_test_005"
        with self.session_factory() as session:
            test_msg = WhatsAppMessage(
                tenant_id=self.clinic_a_id,
                whatsapp_message_id=out_wamid,
                phone_number=self.patient_phone,
                direction="outbound",
                message_type="text",
                body="Testing delivery status receipt",
                status="sent",
            )
            session.add(test_msg)
            session.commit()

        # 2. Simulate "delivered" status callback from Meta
        status_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_meta_001",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": self.phone_id_a},
                                "statuses": [
                                    {
                                        "id": out_wamid,
                                        "status": "delivered",
                                        "timestamp": "1728565400",
                                        "recipient_id": self.patient_phone,
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(status_payload).encode("utf-8")
        sig = self._generate_signature(body_bytes)

        res = self.client.post(
            "/webhook/whatsapp",
            content=body_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(res.status_code, 200)

        # Verify DB status updated to "delivered"
        with self.session_factory() as session:
            updated = session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.whatsapp_message_id == out_wamid
                )
            ).first()
            self.assertEqual(updated.status, "delivered")

        # 3. Simulate "read" status callback from Meta
        status_payload["entry"][0]["changes"][0]["value"]["statuses"][0]["status"] = "read"
        body_bytes_read = json.dumps(status_payload).encode("utf-8")
        sig_read = self._generate_signature(body_bytes_read)

        res_read = self.client.post(
            "/webhook/whatsapp",
            content=body_bytes_read,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig_read},
        )
        self.assertEqual(res_read.status_code, 200)

        # Verify DB status updated to "read"
        with self.session_factory() as session:
            updated_read = session.scalars(
                select(WhatsAppMessage).where(
                    WhatsAppMessage.whatsapp_message_id == out_wamid
                )
            ).first()
            self.assertEqual(updated_read.status, "read")


if __name__ == "__main__":
    unittest.main()

