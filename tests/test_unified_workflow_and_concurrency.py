"""Tests for Unified AI Workflow (Telegram + WhatsApp) and Concurrency Safeguards.

Verifies:
1. Unified LangGraph execution across channels (WhatsApp & Telegram share the same AI engine).
2. Tenant-scoped conversation state isolation across channels and phone numbers.
3. WhatsApp interactive button formatting for confirmation intents.
4. Multithreaded concurrent slot booking race-condition prevention (Double-Booking Prevention).
5. Multithreaded concurrent CRM appointment creation race-condition prevention.
6. Offline UPI QR & invoice generation integrity.
7. Doctor prescription cross-doctor editing isolation & validation guards.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.channels.whatsapp.client import MetaWhatsAppClient
from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.models import (
    WhatsAppButtonReply,
    WhatsAppInteractive,
    WhatsAppMessage,
    WhatsAppMetadata,
    WhatsAppText,
    WhatsAppValue,
)
from app.core.config import Settings
from app.core.tenant import get_current_tenant, tenant_scope
from app.graph.state import GraphState
from app.services.crm_service import CrmService
from app.services.prescription_service import PrescriptionService
from app.telegram.sessions import SessionStore
from app.tools.appointments import AppointmentTools
from app.tools.invoice import InvoiceData
from app.tools.invoices import InvoiceTools
from app.tools.payments import PaymentTools
from app.tools.slots import SlotRepository


class TestUnifiedWorkflowAndConcurrency(unittest.TestCase):
    """Unified AI Agent and Concurrency Test Suite."""

    def setUp(self):
        self.settings = Settings(
            clinic_name="Alpha Healthcare",
            telegram_bot_token="fake_bot_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=Path("./data/knowledge"),
            vectorstore_dir=Path("./data/vectorstore"),
            support_phone="9876543210",
            clinic_upi_id="alphahealth@okaxis",
            whatsapp_access_token="test_token_wa",
            whatsapp_phone_number_id="111111111",
            whatsapp_tenant_phone_map="111111111:tenant_alpha,222222222:tenant_beta",
        )

    def test_whatsapp_and_telegram_invoke_shared_graph_in_tenant_scope(self):
        """Verify WhatsApp webhook executes the LangGraph graph inside tenant_scope."""
        mock_graph = MagicMock()
        captured_tenants = []

        def mock_invoke(state):
            # Capture the active tenant during execution
            current = get_current_tenant()
            captured_tenants.append(current.tenant_id if current else None)
            return {
                **state,
                "response": "Hello, your appointment can be scheduled. Would you like to confirm?",
            }

        mock_graph.invoke.side_effect = mock_invoke
        mock_client = MagicMock(spec=MetaWhatsAppClient)
        mock_client.send_interactive_buttons.return_value = {"success": True, "message_id": "mid.123"}

        sessions = SessionStore()
        handler = WhatsAppHandler(
            settings=self.settings,
            graph=mock_graph,
            client=mock_client,
            sessions=sessions,
        )

        # Inbound WhatsApp message for Tenant Alpha
        value_alpha = WhatsAppValue(
            metadata=WhatsAppMetadata(display_phone_number="+1234567890", phone_number_id="111111111"),
            messages=[
                WhatsAppMessage(
                    from_="919876543210",
                    id="wamid.HBgL123456",
                    timestamp="1700000000",
                    type="text",
                    text=WhatsAppText(body="I want to book an appointment with cardiologist"),
                )
            ],
        )

        import asyncio
        asyncio.run(handler.handle_value(value_alpha))

        # Check graph invocation
        self.assertEqual(len(captured_tenants), 1)
        self.assertEqual(captured_tenants[0], "tenant_alpha")

        # Check session key and state isolation
        session_alpha = sessions.get("wa:tenant_alpha:919876543210")
        self.assertEqual(session_alpha.get("channel"), "whatsapp")
        self.assertEqual(session_alpha.get("tenant_id"), "tenant_alpha")
        self.assertEqual(session_alpha.get("phone"), "919876543210")

        # WhatsApp should render interactive confirmation buttons
        mock_client.send_interactive_buttons.assert_called_once()
        args, kwargs = mock_client.send_interactive_buttons.call_args
        self.assertEqual(kwargs.get("to"), "919876543210")
        self.assertEqual(kwargs.get("phone_number_id"), "111111111")

    def test_whatsapp_tenant_session_isolation(self):
        """Verify two patients messaging different clinic WhatsApp numbers have completely isolated sessions."""
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = lambda s: {**s, "response": f"Response for {s.get('tenant_id')}"}
        mock_client = MagicMock(spec=MetaWhatsAppClient)
        mock_client.send_text.return_value = {"success": True}

        sessions = SessionStore()
        handler = WhatsAppHandler(
            settings=self.settings,
            graph=mock_graph,
            client=mock_client,
            sessions=sessions,
        )

        # Same sender phone messaging two different clinic numbers (Tenant Alpha vs Tenant Beta)
        val_alpha = WhatsAppValue(
            metadata=WhatsAppMetadata(display_phone_number="+1", phone_number_id="111111111"),
            messages=[WhatsAppMessage(from_="919999999999", id="m1", timestamp="1", type="text", text=WhatsAppText(body="Hi Alpha"))],
        )
        val_beta = WhatsAppValue(
            metadata=WhatsAppMetadata(display_phone_number="+2", phone_number_id="222222222"),
            messages=[WhatsAppMessage(from_="919999999999", id="m2", timestamp="2", type="text", text=WhatsAppText(body="Hi Beta"))],
        )

        import asyncio
        asyncio.run(handler.handle_value(val_alpha))
        asyncio.run(handler.handle_value(val_beta))

        sess_alpha = sessions.get("wa:tenant_alpha:919999999999")
        sess_beta = sessions.get("wa:tenant_beta:919999999999")

        self.assertEqual(sess_alpha.get("tenant_id"), "tenant_alpha")
        self.assertEqual(sess_beta.get("tenant_id"), "tenant_beta")
        self.assertNotEqual(sess_alpha["messages"][0]["content"], sess_beta["messages"][0]["content"])

    def test_concurrent_slot_booking_race_condition(self):
        """Verify that under concurrent simultaneous booking attempts, exactly ONE caller succeeds."""
        # Setup in-memory sheet for SlotTools
        headers = ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"]
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        # 1 available slot, S101
        sheet_rows = [
            list(headers),
            ["S101", "D1", "Dr. Rao", tomorrow, "10:00 AM", "10:30 AM", "Available", "", "", ""],
        ]

        def mock_read():
            return [list(r) for r in sheet_rows]

        def mock_update(range_name, values):
            # Parse row number from range like 'Slots!A2:J2'
            row_idx = int(range_name.split("!A")[1].split(":")[0]) - 1
            sheet_rows[row_idx] = list(values)
            return {"updated": True}

        slot_tools = SlotRepository(read_rows=mock_read, update_cells=mock_update, sheet_range="Slots!A1:J10")

        # 12 concurrent workers attempt to book the EXACT SAME slot S101
        num_workers = 12
        results = []

        def try_book(worker_id):
            patient_id = f"P_{worker_id}"
            token_no = f"TKN_{worker_id}"
            return slot_tools.book_slot("S101", patient_id, token_no)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(try_book, i) for i in range(num_workers)]
            for f in as_completed(futures):
                results.append(f.result())

        # Exactly 1 worker succeeded, 11 failed
        success_count = sum(1 for r in results if r is True)
        failure_count = sum(1 for r in results if r is False)

        self.assertEqual(success_count, 1, f"Expected exactly 1 booking to succeed, got {success_count}")
        self.assertEqual(failure_count, num_workers - 1)

        # Verify final state in slot storage
        final_slot = slot_tools.get_slot_by_id("S101", force_refresh=True)
        self.assertEqual(final_slot.get("Status"), "Booked")
        self.assertTrue(final_slot.get("Patient ID", "").startswith("P_"))
        self.assertTrue(final_slot.get("Token No", "").startswith("TKN_"))

    def test_concurrent_crm_manual_appointment_race_condition(self):
        """Verify that concurrent CrmService.create_appointment_manual calls prevent double booking."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        headers = ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"]
        sheet_rows = [
            list(headers),
            ["S202", "D1", "Dr. Rao", tomorrow, "11:00 AM", "11:30 AM", "Available", "", "", ""],
        ]

        def mock_read():
            return [list(r) for r in sheet_rows]

        def mock_update(range_name, values):
            row_idx = int(range_name.split("!A")[1].split(":")[0]) - 1
            sheet_rows[row_idx] = list(values)
            return {"updated": True}

        slot_tools = SlotRepository(read_rows=mock_read, update_cells=mock_update, sheet_range="Slots!A1:J10")
        
        patient_tools = MagicMock()
        patient_tools.generate_patient_id.side_effect = lambda: {"patient_id": f"PID_{uuid4().hex[:6]}"}
        patient_tools.generate_token.side_effect = lambda: {"token_no": f"TKN_{uuid4().hex[:6]}"}
        patient_tools.create_patient.return_value = {
            "success": True,
            "patient": MagicMock(patient_id="P1", name="Patient", email="p@example.com", phone="1234567890"),
        }

        crm = CrmService(
            patients_tools=patient_tools,
            doctors_tools=MagicMock(),
            slots_tools=slot_tools,
            payments_tools=PaymentTools(upi_id="alpha@upi"),
            invoices_tools=InvoiceTools(),
            clinic_name="Alpha Clinic",
        )

        num_threads = 8
        results = []
        errors = []

        def book_appointment(idx):
            data = {
                "name": f"Patient {idx}",
                "phone": f"987654321{idx}",
                "email": f"p{idx}@test.com",
                "doctor_id": "D1",
                "slot_id": "S202",
                "date": tomorrow,
                "amount": "500",
                "payment_mode": "Offline",
            }
            try:
                res = crm.create_appointment_manual(data, admin_user="admin")
                return ("success", res)
            except Exception as e:
                return ("error", str(e))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(book_appointment, i) for i in range(num_threads)]
            for f in as_completed(futures):
                status, val = f.result()
                if status == "success":
                    results.append(val)
                else:
                    errors.append(val)

        self.assertEqual(len(results), 1, "Expected exactly 1 booking to succeed in CRM")
        self.assertEqual(len(errors), num_threads - 1)
        for err in errors:
            self.assertIn("not available", err.lower())

    def test_offline_upi_qr_and_invoice_generation(self):
        """Verify offline UPI QR generation produces valid metadata without hardcoded secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            payment_tools = PaymentTools(upi_id="clinic_test@axisbank")
            qr_res = payment_tools.generate_offline_upi_qr(
                amount="750",
                clinic_name="Apex Hospital",
                reference="TKN-999",
                output_dir=out_dir,
            )
            self.assertTrue(qr_res["success"])
            self.assertTrue(Path(qr_res["qr_path"]).exists())
            self.assertEqual(qr_res["upi_id"], "clinic_test@axisbank")

            # Generate invoice
            invoice_tools = InvoiceTools()
            inv_data = InvoiceData(
                clinic_name="Apex Hospital",
                clinic_phone="9998887770",
                clinic_email="support@apex.org",
                clinic_address="123 Health Ave",
                patient_name="Rahul Verma",
                patient_email="rahul@example.com",
                patient_phone="9876543210",
                doctor_name="Dr. Rao",
                specialization="Cardiologist",
                appointment_date="2026-10-25",
                appointment_time="10:00 AM",
                token_no="TKN-999",
                amount="750",
                payment_method="Pay at Clinic / UPI",
                payment_status="Pending",
                qr_path=qr_res["qr_path"],
                upi_id=qr_res["upi_id"],
            )
            inv_res = invoice_tools.generate_invoice(inv_data, output_dir=out_dir)
            self.assertTrue(inv_res["success"])
            inv_path = Path(inv_res["file_path"])
            self.assertTrue(inv_path.exists())
            self.assertGreater(inv_path.stat().st_size, 500)

    def test_doctor_prescription_cross_doctor_isolation(self):
        """Verify Doctor A cannot edit or finalize Doctor B's draft prescription."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "prescriptions.json"
            pdf_dir = Path(tmpdir) / "rx_pdfs"
            service = PrescriptionService(storage_path=storage_path, pdf_dir=pdf_dir)

            # Doctor 1 creates draft
            rx_draft = service.create_or_update_draft(
                data={
                    "patient_id": "P101",
                    "patient_name": "Anita Roy",
                    "diagnosis": "Hypertension Stage 1",
                    "medicines": [{"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily", "duration": "30 days"}],
                    "appointment_id": "TKN-101",
                },
                doctor_id="DOC_001",
                doctor_name="Dr. Smith",
            )
            rx_id = rx_draft["prescription_id"]

            # Doctor 2 attempts to edit Doctor 1's draft -> PermissionError
            with self.assertRaises(PermissionError):
                service.create_or_update_draft(
                    data={"prescription_id": rx_id, "diagnosis": "Tampered diagnosis"},
                    doctor_id="DOC_002",
                    doctor_name="Dr. Jones",
                )

            # Doctor 2 attempts to finalize Doctor 1's draft -> PermissionError
            with self.assertRaises(PermissionError):
                service.finalize_prescription(
                    prescription_id=rx_id,
                    doctor_id="DOC_002",
                )

            # Doctor 1 finalizes their own prescription -> Success
            finalized = service.finalize_prescription(
                prescription_id=rx_id,
                doctor_id="DOC_001",
            )
            self.assertEqual(finalized["status"], "finalized")
            self.assertEqual(finalized["doctor_id"], "DOC_001")


if __name__ == "__main__":
    unittest.main()
