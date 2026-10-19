"""Tests for Smart Natural Language Conversational AI, Specialization Filtering,
Greeting Welcome Menus, and Mid-Booking Question Interruption Handling.
"""

from datetime import date
import unittest
from unittest.mock import MagicMock, patch

from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.models import WhatsAppMessage, WhatsAppValue
from app.core.config import Settings
from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes
from app.graph.router import classify_intent
from app.tools.doctors import DoctorDirectory
from app.tools.patients import PatientRecord


class FakeLlm:
    def __init__(self, answer_text: str = "Welcome! I am your clinic assistant."):
        self._answer = answer_text

    def answer(self, system_prompt: str, user_text: str, context: list):
        if "fees" in user_text.lower():
            return "Our consultation fee for specialists is ₹800."
        if "kahan" in user_text.lower() or "where" in user_text.lower() or "location" in user_text.lower() or "address" in user_text.lower():
            return "Our clinic is conveniently located at MG Road, Central Market."
        return self._answer


class FakeRag:
    def search(self, question: str):
        return ["Clinic open Monday-Saturday 9am to 8pm", "Consultation fee is ₹800"]


class FakeSlots:
    def __init__(self):
        self.booked = False

    def get_upcoming_available_slots(self, doctor_name: str, doctor_id: str, today_str: str):
        return [
            {"Slot ID": "SLOT-1", "Doctor ID": doctor_id, "Doctor Name": doctor_name, "Date": "2026-10-15", "Start Time": "10:00", "End Time": "10:30", "Status": "Available"},
            {"Slot ID": "SLOT-2", "Doctor ID": doctor_id, "Doctor Name": doctor_name, "Date": "2026-10-15", "Start Time": "11:00", "End Time": "11:30", "Status": "Available"},
        ]

    def get_available_slots(self, doctor: str, date_str: str):
        return [{"Slot ID": "SLOT-1", "Start Time": "10:00", "End Time": "10:30"}]

    def book_slot(self, slot_id: str, patient_id: str, token_no: str):
        return True

    def release_slot(self, slot_id: str, patient_id: str):
        return True


class SmartConversationalAiTests(unittest.TestCase):
    def setUp(self):
        # Clinic with Cardiologists (Dr. Vivek Singh, Dr. Kabir Roy), General Physician, Gynecologist
        # Note: Dr. Sufian is NOT in this clinic's directory
        self.rows_no_sufian = [
            ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
            ["DOC-1", "Dr. Arjun Mehta", "General Physician", "Mon, Wed, Fri", "10:00 AM", "1:00 PM", "500", "Active"],
            ["DOC-2", "Dr. Priya Sharma", "Gynecologist", "Tue, Thu, Sat", "4:00 PM", "7:00 PM", "700", "Active"],
            ["DOC-3", "Dr. Vivek Singh", "Cardiologist", "Mon, Tue, Thu", "9:00 AM", "12:00 PM", "800", "Active"],
            ["DOC-4", "Dr. Kabir Roy", "Cardiologist", "Wed, Fri", "2:00 PM", "5:00 PM", "850", "Active"],
        ]
        self.directory_no_sufian = DoctorDirectory(lambda: self.rows_no_sufian)
        self.slots = FakeSlots()
        self.llm = FakeLlm()
        self.rag = FakeRag()
        self.nodes = GraphNodes(
            clinic_name="City Heart Care",
            llm=self.llm,
            rag=self.rag,
            doctors=self.directory_no_sufian,
            support_phone="6200126662",
            slots=self.slots,
            today_provider=lambda: date(2026, 10, 10),
        )
        self.graph = build_graph(self.nodes)

    def test_01_complex_query_filters_only_cardiology_specialists(self):
        """User asks 'mujhe appoinment chahiye 15 tarikh oct ka dr sufian se ya cardio wale se'.
        Since Dr. Sufian is not on panel, AI identifies Cardiology and returns ONLY Cardiology specialists.
        """
        query = "mujhe appoinment chahiye 15 tarikh oct ka dr sufian se ya cardio wale se"
        res = self.graph.invoke({"user_text": query})

        # Correct intent
        self.assertEqual(res["intent"], "appointment_booking")
        # Step is doctor selection
        self.assertEqual(res["appointment_step"], "doctor")
        self.assertEqual(res["ui"], "doctor_select")

        # Must have doctor_choices containing only Cardiologists
        choices = res.get("doctor_choices", [])
        self.assertEqual(len(choices), 2)
        choice_names = [d["Doctor Name"] for d in choices]
        self.assertIn("Dr. Vivek Singh", choice_names)
        self.assertIn("Dr. Kabir Roy", choice_names)
        self.assertNotIn("Dr. Arjun Mehta", choice_names)
        self.assertNotIn("Dr. Priya Sharma", choice_names)

        # Response explains Dr. Sufian is not on panel and lists Cardiology specialists
        self.assertIn("Dr. Sufian is not on our current panel", res["response"])
        self.assertIn("Cardiology specialists", res["response"])
        self.assertIn("Dr. Vivek Singh", res["response"])

    def test_02_direct_doctor_match_when_present(self):
        """When Dr. Sufian IS in the directory, query matches Dr. Sufian directly."""
        rows_with_sufian = [
            ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
            ["DOC-1", "Dr. Arjun Mehta", "General Physician", "Mon, Wed, Fri", "10:00 AM", "1:00 PM", "500", "Active"],
            ["DOC-3", "Dr. Sufian", "Cardiologist", "All Days", "9:00 AM", "12:00 PM", "800", "Active"],
        ]
        directory = DoctorDirectory(lambda: rows_with_sufian)
        nodes = GraphNodes(
            clinic_name="City Heart Care",
            llm=self.llm,
            rag=self.rag,
            doctors=directory,
            support_phone="6200126662",
            slots=self.slots,
            today_provider=lambda: date(2026, 10, 10),
        )
        graph = build_graph(nodes)

        query = "mujhe appoinment chahiye 15 tarikh oct ka dr sufian se ya cardio wale se"
        res = graph.invoke({"user_text": query})

        self.assertEqual(res["intent"], "appointment_booking")
        self.assertEqual(res["doctor_name"], "Dr. Sufian")
        self.assertEqual(res["appointment_date"], "2026-10-15")
        self.assertIn("Dr. Sufian is available on 15 October", res["response"])

    def test_03_greeting_intent_and_welcome_menu(self):
        """Simple greetings like 'hi', 'hello', 'namaste' return intent greeting and ui welcome_menu."""
        for greeting in ["hi", "hii", "hello", "namaste", "hey"]:
            classified = classify_intent({"user_text": greeting})
            self.assertEqual(classified["intent"], "greeting", f"Failed for greeting: {greeting}")

            res = self.graph.invoke({"user_text": greeting})
            self.assertEqual(res["ui"], "welcome_menu")

    def test_04_interactive_button_ids_route_correctly(self):
        """Quick action buttons route to correct business intents."""
        self.assertEqual(classify_intent({"user_text": "btn_book_appointment"})["intent"], "appointment_booking")
        self.assertEqual(classify_intent({"user_text": "btn_clinic_info"})["intent"], "clinic_information")
        self.assertEqual(classify_intent({"user_text": "btn_my_reports"})["intent"], "report_enquiry")

    def test_05_mid_booking_question_interruption_handling(self):
        """When user asks about fees or clinic location during email step,
        it answers the question, preserves appointment_step, and prompts to continue.
        """
        # Step 1: User starts appointment booking with Dr. Arjun
        state = self.graph.invoke({"user_text": "Dr Arjun kab free hain?"})
        state = self.graph.invoke({**state, "user_text": "Appointment book karni hai"})
        self.assertEqual(state["appointment_step"], "name")

        # Step 2: Patient gives name
        state = self.graph.invoke({**state, "user_text": "Rajesh Kumar"})
        self.assertEqual(state["appointment_step"], "email")
        self.assertIn("What email address", state["response"])

        # Step 3: Patient interrupts with side question: 'fees kitni lagegi?'
        interruption = self.graph.invoke({**state, "user_text": "fees kitni lagegi?"})
        self.assertEqual(interruption["intent"], "clinic_information")
        self.assertEqual(interruption["appointment_step"], "email")  # Step preserved!
        self.assertIn("consultation fee", interruption["response"].lower())
        self.assertIn("appointment booking", interruption["response"].lower())  # Resumption prompt added!

        # Step 4: Patient now provides email address -> continues booking without getting stuck!
        continued = self.graph.invoke({**interruption, "user_text": "rajesh@gmail.com"})
        self.assertEqual(continued["appointment_step"], "phone")
        self.assertEqual(continued["patient_email"], "rajesh@gmail.com")

    def test_06_whatsapp_welcome_menu_dispatches_3_buttons(self):
        """WhatsAppHandler dispatches interactive buttons when ui is welcome_menu."""
        from pathlib import Path
        mock_client = MagicMock()
        mock_client.send_interactive_buttons.return_value = {"success": True}
        settings = Settings(
            clinic_name="City Heart Care",
            telegram_bot_token="fake_bot_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=Path("./data/knowledge"),
            vectorstore_dir=Path("./data/vectorstore"),
            whatsapp_enabled=True,
            whatsapp_phone_number_id="PN-100",
            whatsapp_tenant_phone_map="PN-100:default",
        )

        handler = WhatsAppHandler(settings=settings, graph=self.graph, client=mock_client)

        val = WhatsAppValue(
            messaging_product="whatsapp",
            metadata={"display_phone_number": "12345", "phone_number_id": "PN-100"},
            contacts=[{"wa_id": "919876543210"}],
            messages=[WhatsAppMessage(id="WAM-GREET-1", from_="919876543210", timestamp="123456", text={"body": "hii"}, type="text")],
        )

        import asyncio
        asyncio.run(handler.handle_value(val))

        mock_client.send_interactive_buttons.assert_called_once()
        _, kwargs = mock_client.send_interactive_buttons.call_args
        self.assertEqual(kwargs["to"], "919876543210")
        buttons = kwargs["buttons"]
        self.assertEqual(len(buttons), 3)
        self.assertEqual(buttons[0]["id"], "btn_book_appointment")
        self.assertEqual(buttons[1]["id"], "btn_clinic_info")
        self.assertEqual(buttons[2]["id"], "btn_my_reports")

    def test_07_welcome_menu_only_sent_once_and_never_on_follow_up_steps(self):
        """Turn 1: 'hi' sends welcome menu buttons.
        Turn 2: 'Book Appointment' sends plain text asking name (no buttons).
        Turn 3: 'sufian' sends plain text asking email (no buttons).
        Turn 4: 'hi' later in conversation does NOT repeat buttons.
        """
        import asyncio
        from pathlib import Path

        mock_client = MagicMock()
        mock_client.send_interactive_buttons.return_value = {"success": True}
        mock_client.send_text.return_value = {"success": True}
        settings = Settings(
            clinic_name="City Heart Care",
            telegram_bot_token="fake_bot_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=Path("./data/knowledge"),
            vectorstore_dir=Path("./data/vectorstore"),
            whatsapp_enabled=True,
            whatsapp_phone_number_id="PN-100",
            whatsapp_tenant_phone_map="PN-100:default",
        )

        handler = WhatsAppHandler(settings=settings, graph=self.graph, client=mock_client)

        def make_val(msg_id: str, body: str) -> WhatsAppValue:
            return WhatsAppValue(
                messaging_product="whatsapp",
                metadata={"display_phone_number": "12345", "phone_number_id": "PN-100"},
                contacts=[{"wa_id": "919876543210"}],
                messages=[WhatsAppMessage(id=msg_id, from_="919876543210", timestamp="123456", text={"body": body}, type="text")],
            )

        # Turn 1: Inbound "hi"
        asyncio.run(handler.handle_value(make_val("WAM-T1", "hi")))
        self.assertEqual(mock_client.send_interactive_buttons.call_count, 1)
        mock_client.send_interactive_buttons.reset_mock()
        mock_client.send_text.reset_mock()

        # Turn 2: User taps "Book Appointment"
        asyncio.run(handler.handle_value(make_val("WAM-T2", "Book Appointment")))
        mock_client.send_interactive_buttons.assert_not_called()  # NEVER SEND BUTTONS ON STEP 2!
        mock_client.send_text.assert_called_once()
        sent_body_turn2 = mock_client.send_text.call_args.kwargs.get("text") or mock_client.send_text.call_args[0][1]
        self.assertIn("May I know your name", sent_body_turn2)
        mock_client.send_text.reset_mock()

        # Turn 3: User replies "sufian"
        asyncio.run(handler.handle_value(make_val("WAM-T3", "sufian")))
        mock_client.send_interactive_buttons.assert_not_called()  # NEVER SEND BUTTONS ON STEP 3!
        mock_client.send_text.assert_called_once()
        sent_body_turn3 = mock_client.send_text.call_args.kwargs.get("text") or mock_client.send_text.call_args[0][1]
        self.assertIn("What email address", sent_body_turn3)
        mock_client.send_text.reset_mock()

        # Turn 4: User sends "hi" later in active session
        asyncio.run(handler.handle_value(make_val("WAM-T4", "hi")))
        mock_client.send_interactive_buttons.assert_not_called()  # DOES NOT REPEAT BUTTONS!

    def test_08_side_question_for_address_during_doctor_step_answers_address_and_resumes_doctor_step(self):
        """When user is in 'doctor' step and asks 'mujhe hospital ka address dena':
        1. Router classifies intent as 'clinic_information' (NOT forced to appointment_flow/unknown doctor).
        2. Graph returns address and appends continuation prompt.
        3. Response NEVER says 'Is naam se doctor nahi mil rahe hain'.
        """
        initial_state = {
            "appointment_step": "doctor",
            "patient_name": "Sufian",
            "patient_email": "sufian@example.com",
            "patient_phone": "9876543210",
            "user_text": "mujhe hospital ka address dena",
        }
        res = self.graph.invoke(initial_state)

        # Correct intent
        self.assertEqual(res["intent"], "clinic_information")
        # Step remains preserved
        self.assertEqual(res["appointment_step"], "doctor")
        # Response contains clinic info/address
        self.assertTrue(
            "Central Market" in res["response"] or "MG Road" in res["response"] or "open" in res["response"].lower()
        )
        # MUST NOT claim 'Is naam se doctor nahi mil rahe hain'
        self.assertNotIn("Is naam se doctor nahi mil rahe hain", res["response"])
        self.assertNotIn("naam se doctor match nahi", res["response"])
        # Contains reminder to choose doctor
        self.assertIn("appointment booking", res["response"].lower())

    def test_09_conversational_query_during_phone_step_does_not_save_as_phone(self):
        """When user is in 'phone' step and says 'number du ?':
        1. Agent recognizes this as conversational query.
        2. Does NOT save 'number du ?' as patient_phone.
        3. Stays in 'phone' step and politely prompts for 10-digit number.
        4. When a 10-digit number is provided, saves and proceeds.
        """
        state = {
            "appointment_step": "phone",
            "patient_name": "Sufian",
            "patient_email": "sufian@example.com",
            "user_text": "number du ?",
        }
        res = self.graph.invoke(state)
        # Must stay in phone step
        self.assertEqual(res["appointment_step"], "phone")
        self.assertNotEqual(res.get("patient_phone"), "number du ?")
        self.assertIn("10-digit", res["response"])

        # When valid 10-digit phone is entered
        state2 = {**res, "user_text": "9876543210"}
        res2 = self.graph.invoke(state2)
        self.assertEqual(res2.get("patient_phone"), "9876543210")
        self.assertEqual(res2["appointment_step"], "doctor")

    def test_10_doctor_finalize_prescription_triggers_whatsapp_pdf_dispatch(self):
        """When doctor finalizes a prescription via API:
        1. Status transitions to 'finalized'.
        2. PDF is generated.
        3. WhatsApp client upload_media and send_document are invoked with the patient's phone and HealthPlix style caption.
        """
        import asyncio
        from unittest.mock import MagicMock
        from app.api.doctor import create_doctor_router
        from app.services.crm_service import CrmService

        mock_crm = MagicMock()
        mock_crm.prescriptions.finalize_prescription.return_value = {
            "prescription_id": "RX-101",
            "patient_id": "PAT-001",
            "patient_name": "Harsh",
            "patient_phone": "9876543210",
            "doctor_id": "DOC-1",
            "doctor_name": "Naveen Agarwal",
            "appointment_id": "TKN-55",
            "diagnosis": "Seasonal Viral Pharyngitis",
            "status": "finalized",
        }
        # Fake PDF generation returning path
        import tempfile
        from pathlib import Path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(b"%PDF-1.4 mock pdf data")
            fake_pdf = Path(tf.name)

        mock_crm.prescriptions.generate_pdf_for_prescription.return_value = ("RX-101", fake_pdf)
        mock_crm.get_patient.return_value = {"phone": "9876543210", "name": "Harsh"}

        mock_wa = MagicMock()
        mock_wa.upload_media.return_value = "MEDIA-999"
        mock_wa.send_document.return_value = {"messages": [{"id": "WAM-DOC-1"}]}

        settings = Settings(
            clinic_name="City Heart Care",
            telegram_bot_token="fake_bot_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=Path("./data/knowledge"),
            vectorstore_dir=Path("./data/vectorstore"),
            whatsapp_enabled=True,
            whatsapp_phone_number_id="PN-100",
        )

        router = create_doctor_router(mock_crm, settings, whatsapp_client=mock_wa)
        # Find the finalize route handler
        finalize_route = next(r for r in router.routes if r.path == "/api/doctor/prescriptions/{prescription_id}/finalize")
        
        doctor_user = {"doctor_id": "DOC-1", "username": "dr_naveen", "doctor_name": "Naveen Agarwal"}
        res = asyncio.run(finalize_route.endpoint("RX-101", current_doctor=doctor_user))

        self.assertEqual(res["status"], "finalized")
        mock_wa.upload_media.assert_called_once()
        mock_wa.send_document.assert_called_once()
        _, kwargs = mock_wa.send_document.call_args
        self.assertEqual(kwargs["to"], "9876543210")
        self.assertEqual(kwargs["media_id"], "MEDIA-999")
        self.assertIn("Harsh", kwargs["caption"])
        self.assertIn("Naveen Agarwal", kwargs["caption"])
        self.assertIn("City Heart Care", kwargs["caption"])

        # Clean up temp file
        fake_pdf.unlink(missing_ok=True)

    def test_11_ai_agent_feature_flag_defaults_and_toggle(self):
        """Test FEATURE_AI_AGENT is True across all tiers and can be toggled per tenant."""
        from app.core.feature_flags import (
            FEATURE_AI_AGENT,
            SUBSCRIPTION_PLANS,
            get_plan_default_flags,
            resolve_effective_feature_flags,
            is_feature_enabled,
        )

        # Defaults are True
        for plan in ("STARTER", "PROFESSIONAL", "ENTERPRISE"):
            self.assertTrue(SUBSCRIPTION_PLANS[plan][FEATURE_AI_AGENT])
            self.assertTrue(get_plan_default_flags(plan)[FEATURE_AI_AGENT])

        # Can be toggled to False for Rule-Based Mode
        flags_ai_off = resolve_effective_feature_flags("STARTER", {FEATURE_AI_AGENT: False})
        self.assertFalse(is_feature_enabled(flags_ai_off, FEATURE_AI_AGENT))

        # Can be toggled back to True
        flags_ai_on = resolve_effective_feature_flags("STARTER", {FEATURE_AI_AGENT: True})
        self.assertTrue(is_feature_enabled(flags_ai_on, FEATURE_AI_AGENT))


if __name__ == "__main__":
    unittest.main()


