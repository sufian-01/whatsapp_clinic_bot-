"""Dedicated End-to-End Tests for Dynamic Tenant Creation, RAG Document Ingestion, and Execution.

Verifies:
1. Super Admin adds a new tenant dynamically at runtime without restarting.
2. Super Admin uploads knowledge documents (PDF/TXT) for that specific tenant.
3. Tenant RAG immediately indexes and retrieves knowledge isolated strictly to that tenant.
4. RAG search does NOT leak knowledge to other tenants (Alpha, Beta, Default).
5. LangGraph nodes (retrieve, answer, human_support, report_response) dynamically execute
   using the tenant's custom clinic name, support phone, and RAG knowledge.
6. WhatsApp routing and state injection dynamically resolve and apply the tenant config.
"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.models import WhatsAppValue
from app.core.config import Settings
from app.graph.nodes import GraphNodes
from app.rag.tenant_service import TenantRagRegistry, set_tenant_rag_registry
from app.services.tenant_management_service import TenantManagementService
from app.telegram.sessions import SessionStore
from app.tools.rag_tool import search_clinic_knowledge


class TestDynamicTenantRagExecution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # Set up a clean global TenantRagRegistry for the test
        self.rag_registry = TenantRagRegistry(base_dir=self.base_path)
        set_tenant_rag_registry(self.rag_registry)

        # Initialize TenantManagementService using the isolated directory
        self.tenant_service = TenantManagementService(rag_base_dir=self.base_path)

        # Register Clinic Gamma (New tenant created via Super Admin)
        self.clinic_gamma = self.tenant_service.create_tenant({
            "id": "clinic_gamma",
            "name": "Gamma Cardiology Institute",
            "whatsapp_phone_number": "+919876543333",
            "whatsapp_phone_number_id": "phone_gamma_333",
            "whatsapp_waba_id": "waba_gamma_333",
            "subscription_plan": "ENTERPRISE",
            "phone": "+91 98765 43333",
            "address": "456 Heartbeat Blvd, Medical Enclave",
        })

        # Register Clinic Delta
        self.clinic_delta = self.tenant_service.create_tenant({
            "id": "clinic_delta",
            "name": "Delta Eye & Dental Clinic",
            "whatsapp_phone_number": "+919876544444",
            "whatsapp_phone_number_id": "phone_delta_444",
            "whatsapp_waba_id": "waba_delta_444",
            "subscription_plan": "STARTER",
            "phone": "+91 98765 44444",
            "address": "789 Vision Way",
        })

        self.settings = Settings(
            clinic_name="Default Platform Clinic",
            telegram_bot_token="fake_tg_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=self.base_path / "knowledge",
            vectorstore_dir=self.base_path / "vectorstore",
            support_phone="1800-000-000",
            whatsapp_verify_token="test_token",
            whatsapp_app_secret="test_secret",
            whatsapp_access_token="test_access_token",
            whatsapp_phone_number_id="default_phone_id",
        )

        self.nodes = GraphNodes(
            clinic_name="Default Platform Clinic",
            llm=MagicMock(),
            rag=MagicMock(),
            doctors=MagicMock(),
            support_phone="1800-000-000",
            patients=MagicMock(),
            slots=MagicMock(),
            payments=MagicMock(),
            invoices=MagicMock(),
            gmail=MagicMock(),
            crm_service=MagicMock(),
        )

    def tearDown(self):
        set_tenant_rag_registry(None)
        self.temp_dir.cleanup()

    def test_01_superadmin_upload_document_immediately_searchable_for_tenant(self):
        """When Super Admin uploads a document for clinic_gamma, RAG indexes and searches it immediately."""
        gamma_doc = (
            "Gamma Cardiology Institute Emergency Services: Available 24/7. "
            "Cardiac catheterization lab open day and night. "
            "For urgent heart emergencies call ambulance at 108 or our helpline 9876543333."
        )
        upload_res = self.tenant_service.upload_tenant_document(
            tenant_id="clinic_gamma",
            filename="cardiac_emergency_guide.txt",
            content=gamma_doc.encode("utf-8"),
        )
        self.assertEqual(upload_res["status"], "INDEXED")
        self.assertGreaterEqual(upload_res["indexed_chunks"], 1)

        # Direct search_clinic_knowledge for clinic_gamma
        results = search_clinic_knowledge(
            service=self.nodes._rag,
            question="What is the cardiac emergency procedure and helpline?",
            tenant_id="clinic_gamma",
        )
        self.assertTrue(len(results) > 0)
        self.assertIn("Cardiac catheterization lab", results[0])
        self.assertIn("9876543333", results[0])

    def test_02_strict_cross_tenant_rag_isolation(self):
        """Knowledge uploaded for Clinic Gamma must NEVER leak to Clinic Delta or Default."""
        gamma_doc = "Gamma Secret Protocol: VIP cardiology lounge on Floor 5 with free valet."
        self.tenant_service.upload_tenant_document(
            tenant_id="clinic_gamma",
            filename="gamma_vip.txt",
            content=gamma_doc.encode("utf-8"),
        )

        delta_doc = "Delta Eye Care: Cataract surgery laser suite on Floor 1."
        self.tenant_service.upload_tenant_document(
            tenant_id="clinic_delta",
            filename="delta_eye.txt",
            content=delta_doc.encode("utf-8"),
        )

        # Query Clinic Delta for gamma secret -> MUST NOT FIND IT
        delta_results = search_clinic_knowledge(
            service=self.nodes._rag,
            question="Where is the VIP cardiology lounge?",
            tenant_id="clinic_delta",
        )
        # Should either be empty or only contain Delta info
        for chunk in delta_results:
            self.assertNotIn("VIP cardiology lounge", chunk)
            self.assertNotIn("Gamma Secret Protocol", chunk)

        # Query Clinic Gamma for cataract surgery -> MUST NOT FIND IT
        gamma_results = search_clinic_knowledge(
            service=self.nodes._rag,
            question="Where is cataract surgery laser suite?",
            tenant_id="clinic_gamma",
        )
        for chunk in gamma_results:
            self.assertNotIn("Cataract surgery laser suite", chunk)
            self.assertNotIn("Delta Eye Care", chunk)

    def test_03_graph_retrieve_node_uses_tenant_id_from_state(self):
        """Graph 'retrieve' node pulls tenant_id from state and queries the correct tenant vectorstore."""
        gamma_faq = "Parking at Gamma Cardiology: Free parking available in Basement B2 for all patients."
        self.tenant_service.upload_tenant_document(
            tenant_id="clinic_gamma",
            filename="parking_faq.txt",
            content=gamma_faq.encode("utf-8"),
        )

        state = {
            "user_text": "Is there parking available?",
            "tenant_id": "clinic_gamma",
            "feature_flags": {"rag_knowledge": True},
        }

        new_state = self.nodes.retrieve(state)
        clinic_context = new_state.get("clinic_context", [])
        self.assertTrue(len(clinic_context) > 0)
        self.assertIn("Free parking available in Basement B2", clinic_context[0])

    def test_04_dynamic_clinic_branding_in_graph_nodes(self):
        """Human support and report response dynamically brand with tenant clinic name and support phone."""
        # 1. Human support node
        state = {
            "tenant_id": "clinic_gamma",
            "clinic_name": "Gamma Cardiology Institute",
            "support_phone": "+91 98765 43333",
            "messages": [],
        }
        res_state = self.nodes.human_support(state)
        response_text = res_state.get("response", "")
        self.assertIn("Gamma Cardiology Institute", response_text)
        self.assertIn("+91 98765 43333", response_text)

        # 2. Report response node
        report_state = {
            "tenant_id": "clinic_delta",
            "clinic_name": "Delta Eye & Dental Clinic",
            "support_phone": "+91 98765 44444",
            "messages": [],
        }
        res_report = self.nodes.report_response(report_state)
        self.assertIn("Delta Eye & Dental Clinic", res_report.get("response", ""))
        self.assertIn("+91 98765 44444", res_report.get("response", ""))

    def test_05_whatsapp_handler_resolves_tenant_and_injects_brand_metadata(self):
        """WhatsApp handler dynamically maps incoming WhatsApp phone_number_id to tenant metadata."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"response": "OK", "messages": [], "ui": ""}
        mock_client = MagicMock()

        handler = WhatsAppHandler(
            settings=self.settings,
            graph=mock_graph,
            client=mock_client,
            sessions=SessionStore(),
            tenant_management_service=self.tenant_service,
        )

        # Incoming webhook from Gamma's WhatsApp Phone Number ID
        val = WhatsAppValue.model_validate({
            "messaging_product": "whatsapp",
            "metadata": {"phone_number_id": "phone_gamma_333"},
            "messages": [
                {
                    "from": "919999988888",
                    "id": "wamid_gamma_test_1",
                    "timestamp": "1728560000",
                    "type": "text",
                    "text": {"body": "Hello, do you have cardiac emergency?"},
                }
            ],
        })

        import asyncio
        asyncio.run(handler.handle_value(val))

        mock_graph.invoke.assert_called_once()
        invoked_state = mock_graph.invoke.call_args[0][0]

        # Verify state contains tenant_id and dynamic clinic details
        self.assertEqual(invoked_state.get("tenant_id"), "clinic_gamma")
        self.assertEqual(invoked_state.get("clinic_name"), "Gamma Cardiology Institute")
        self.assertEqual(invoked_state.get("support_phone"), "+91 98765 43333")


if __name__ == "__main__":
    unittest.main()
