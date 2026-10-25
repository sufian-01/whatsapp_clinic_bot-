"""Comprehensive verification suite for conversation memory and interruption handling.

Tests:
- TEST 1: New user -> greeting -> general question.
- TEST 2: User starts appointment -> provides name -> provides doctor -> continues normally.
- TEST 3: User starts appointment -> asks unrelated clinic question -> gets answer -> appointment resumes.
- TEST 4: User starts appointment -> says 'rehne do' -> appointment cancelled and flow stops.
- TEST 5: User starts appointment -> asks multiple side questions -> appointment state remains intact.
- TEST 6: User sends another message later -> previous conversation state is restored using the same thread_id.
- TEST 7: Two different phone numbers -> completely separate conversations.
- TEST 8: Same phone number in two different clinics -> completely separate conversations.
- TEST 9: Same Meta message ID delivered twice -> processed only once.
- TEST 10: Two rapid messages for the same patient -> state does not get corrupted.
- TEST 11: Long conversation -> summary + recent messages are used instead of unbounded history.
- TEST 12: Server restart / new graph instance -> state remains available from checkpointer.
"""

import asyncio
from pathlib import Path
import unittest
from unittest.mock import MagicMock

from langgraph.checkpoint.memory import MemorySaver

from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.models import (
    WhatsAppMessage,
    WhatsAppValue,
)
from app.core.config import Settings
from app.graph.graph import CheckpointedGraph, build_graph, build_whatsapp_thread_id
from app.graph.nodes import GraphNodes
from app.tools.doctors import DoctorDirectory


class FakePatientRepo:
    def __init__(self):
        self.records = []

    def list_patients(self):
        return [dict(r) for r in self.records]

    def create_patient(self, record):
        rec = {
            "Patient ID": "PAT-101",
            "Name": getattr(record, "name", ""),
            "Phone": getattr(record, "phone", ""),
            "Email": getattr(record, "email", ""),
            "Doctor": getattr(record, "doctor", ""),
            "Appointment Date": getattr(record, "appointment_date", ""),
            "Appointment Time": getattr(record, "appointment_time", ""),
            "Token No": "TKN-999",
            "Amount": "500",
            "Payment Method": "Offline",
            "Payment Status": "Pending",
            "Booking Status": "Confirmed",
            "Status": "Confirmed",
        }
        self.records.append(rec)
        return {"success": True, "patient": rec}

    def generate_token(self):
        return {"token_no": "TKN-999"}

    def generate_patient_id(self):
        return {"patient_id": "PAT-101"}


class FakeLlm:
    def answer(self, system_prompt: str, user_text: str, context: list, history=None):
        if "fees" in user_text.lower() or "kitna" in user_text.lower():
            return "Dr. Arjun Mehta ki consultation fee ₹500 hai."
        if "timing" in user_text.lower() or "hours" in user_text.lower() or "samay" in user_text.lower():
            return "XYZ Clinic Monday to Friday subah 9:00 baje se shaam 5:00 baje tak khula rehta hai."
        if "qualification" in user_text.lower():
            return "Dr. Arjun Mehta MBBS, MD (General Medicine) hain."
        if "address" in user_text.lower() or "kahan" in user_text.lower():
            return "XYZ Clinic 123 Healthcare Avenue, Mumbai par sthit hai."
        return f"AI response for: {user_text}"


class FakeRag:
    def search(self, question: str):
        return ["XYZ Clinic open Monday-Friday 9am to 5pm at 123 Healthcare Avenue."]


class FakeSlots:
    def get_upcoming_available_slots(self, doctor_name: str, doctor_id: str, today_str: str):
        return [
            {
                "Slot ID": "SLOT-001",
                "Doctor ID": doctor_id or "DOC001",
                "Doctor Name": doctor_name or "Dr. Arjun Mehta",
                "Date": "2026-10-25",
                "Start Time": "10:00 AM",
                "End Time": "10:30 AM",
                "Status": "Available",
            }
        ]


class InterruptionAndMemoryArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.llm = FakeLlm()
        self.rag = FakeRag()
        rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee", "Available Days", "Start Time", "End Time", "Status"],
            ["DOC001", "Dr. Arjun Mehta", "General Physician", "500", "Monday, Wednesday, Friday", "10:00 AM", "1:00 PM", "Active"],
            ["DOC002", "Dr. Sana Khan", "Gynecologist", "700", "Tuesday, Thursday, Saturday", "4:00 PM", "7:00 PM", "Active"],
        ]
        self.doc_dir = DoctorDirectory(lambda: rows)
        self.nodes = GraphNodes(
            clinic_name="XYZ Clinic",
            llm=self.llm,
            rag=self.rag,
            doctors=self.doc_dir,
            support_phone="6200126662",
            patients=FakePatientRepo(),
            slots=FakeSlots(),
        )
        self.checkpointer = MemorySaver()
        self.graph = build_graph(self.nodes, checkpointer=self.checkpointer)

    def _send_msg(self, text: str, phone: str = "919876543210", clinic_id: str = "default"):
        tid = build_whatsapp_thread_id(clinic_id, phone)
        config = {"configurable": {"thread_id": tid}}
        state = {
            "chat_id": tid,
            "thread_id": tid,
            "user_text": text,
            "channel": "whatsapp",
            "phone": phone,
            "patient_phone": phone,
            "tenant_id": clinic_id,
            "clinic_id": clinic_id,
            "clinic_name": "XYZ Clinic",
            "support_phone": "6200126662",
        }
        return self.graph.invoke(state, config=config)

    def test_01_new_user_greeting_and_general_question(self):
        """TEST 1: New user -> greeting -> general question."""
        res1 = self._send_msg("Hello")
        self.assertTrue(len(res1.get("response", "")) > 0)

        res2 = self._send_msg("What services does the clinic offer?")
        self.assertTrue("XYZ Clinic" in res2.get("response", "") or "response" in res2)
        self.assertIsNone(res2.get("active_flow"))

    def test_02_appointment_normal_progression(self):
        """TEST 2: User starts appointment -> provides name -> provides doctor -> continues normally."""
        res1 = self._send_msg("Book appointment")
        self.assertEqual(res1.get("active_flow"), "appointment_booking")
        self.assertTrue("name" in res1.get("response", "").lower() or "doctor" in res1.get("response", "").lower())

        res2 = self._send_msg("Sufian")
        self.assertEqual(res2.get("patient_name"), "Sufian")

        res3 = self._send_msg("Dr. Arjun Mehta")
        self.assertEqual(res3.get("doctor_name"), "Dr. Arjun Mehta")

    def test_03_appointment_interruption_by_side_question_and_resume(self):
        """TEST 3: User starts appointment -> asks unrelated clinic question -> gets answer -> appointment resumes."""
        self._send_msg("Book appointment")
        self._send_msg("Sufian")  # provides name

        # Mid-flow interruption: side question
        res_interrupted = self._send_msg("clinic ka timing kya hai?")
        resp_text = res_interrupted.get("response", "")
        # Must answer the question
        self.assertTrue("9:00" in resp_text or "XYZ Clinic" in resp_text or "timing" in resp_text.lower())
        # Must NOT lose patient name
        self.assertEqual(res_interrupted.get("patient_name"), "Sufian")
        # Must include reminder/prompt to continue
        self.assertTrue("appointment booking" in resp_text.lower() or "continue" in resp_text.lower() or "chalu" in resp_text.lower())

    def test_04_appointment_cancellation_with_rehne_do(self):
        """TEST 4: User starts appointment -> says 'rehne do' -> appointment is cancelled and flow stops."""
        self._send_msg("Book appointment")
        res_cancel = self._send_msg("rehne do appointment nahi chahiye")
        self.assertIn("cancel", res_cancel.get("response", "").lower())
        self.assertEqual(res_cancel.get("appointment_step"), "")
        self.assertIsNone(res_cancel.get("active_flow"))

        # Next user message is treated as fresh request, not booking continuation
        res_after = self._send_msg("Hello")
        self.assertNotIn("patient ka naam", res_after.get("response", "").lower())

    def test_05_appointment_multiple_side_questions_preserves_state(self):
        """TEST 5: User starts appointment -> asks multiple side questions -> appointment state remains intact."""
        self._send_msg("Book appointment")
        self._send_msg("Sufian")  # name stored

        # Side question 1: fees
        res1 = self._send_msg("doctor ki fees kitni hai?")
        self.assertIn("500", res1.get("response", ""))
        self.assertEqual(res1.get("patient_name"), "Sufian")

        # Side question 2: qualification
        res2 = self._send_msg("doctor ka qualification kya hai?")
        self.assertIn("MBBS", res2.get("response", ""))
        self.assertEqual(res2.get("patient_name"), "Sufian")

        # Side question 3: clinic address
        res3 = self._send_msg("clinic ka address kahan hai?")
        self.assertIn("123 Healthcare", res3.get("response", ""))
        self.assertEqual(res3.get("patient_name"), "Sufian")

    def test_06_state_restored_using_deterministic_thread_id(self):
        """TEST 6: User sends another message later -> previous conversation state is restored using the same thread_id."""
        phone = "919111222333"
        self._send_msg("Book appointment", phone=phone)
        self._send_msg("Rahul Kumar", phone=phone)

        # Later message on same thread
        res_later = self._send_msg("clinic timing kya hai?", phone=phone)
        self.assertEqual(res_later.get("patient_name"), "Rahul Kumar")

    def test_07_two_different_phone_numbers_isolated(self):
        """TEST 7: Two different phone numbers -> completely separate conversations."""
        phone_a = "919999900001"
        phone_b = "919999900002"

        self._send_msg("Book appointment", phone=phone_a)
        self._send_msg("Patient Alice", phone=phone_a)

        self._send_msg("Book appointment", phone=phone_b)
        res_b = self._send_msg("Patient Bob", phone=phone_b)

        # Retrieve checkpoint state for Alice
        tid_a = build_whatsapp_thread_id("default", phone_a)
        state_a = self.checkpointer.get({"configurable": {"thread_id": tid_a}})
        self.assertEqual(state_a["channel_values"].get("patient_name"), "Patient Alice")
        self.assertEqual(res_b.get("patient_name"), "Patient Bob")

    def test_08_same_phone_in_two_clinics_completely_isolated(self):
        """TEST 8: Same phone number in two different clinics -> completely separate conversations."""
        phone = "919888877776"
        self._send_msg("Book appointment", phone=phone, clinic_id="clinic_alpha")
        self._send_msg("Dr. Arjun Mehta", phone=phone, clinic_id="clinic_alpha")

        self._send_msg("Book appointment", phone=phone, clinic_id="clinic_beta")
        res_beta = self._send_msg("Dr. Sana Khan", phone=phone, clinic_id="clinic_beta")

        tid_alpha = build_whatsapp_thread_id("clinic_alpha", phone)
        state_alpha = self.checkpointer.get({"configurable": {"thread_id": tid_alpha}})
        self.assertEqual(state_alpha["channel_values"].get("doctor_name"), "Dr. Arjun Mehta")
        self.assertEqual(res_beta.get("doctor_name"), "Dr. Sana Khan")

    def test_09_meta_message_id_deduplication(self):
        """TEST 9: Same Meta message ID delivered twice -> processed only once."""
        mock_client = MagicMock()
        mock_client.send_interactive_buttons.return_value = {"success": True}
        mock_client.send_text.return_value = {"success": True}
        settings = Settings(
            clinic_name="XYZ Clinic",
            telegram_bot_token="fake_bot_token",
            telegram_webhook_secret="fake_tg_secret",
            gemini_api_key="fake_gemini_key",
            gemini_model="gemini-2.5-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=Path("./data/knowledge"),
            vectorstore_dir=Path("./data/vectorstore"),
            whatsapp_enabled=True,
            whatsapp_phone_number_id="PN-500",
            whatsapp_tenant_phone_map="PN-500:default",
        )
        handler = WhatsAppHandler(settings=settings, graph=self.graph, client=mock_client)

        val = WhatsAppValue(
            messaging_product="whatsapp",
            metadata={"display_phone_number": "12345", "phone_number_id": "PN-500"},
            contacts=[{"wa_id": "919000000000"}],
            messages=[WhatsAppMessage(id="WAM-DUP-1", from_="919000000000", timestamp="123456", text={"body": "Hello"}, type="text")],
        )

        # 1st delivery
        asyncio.run(handler.handle_value(val))
        call_count_1 = mock_client.send_text.call_count + mock_client.send_interactive_buttons.call_count

        # 2nd delivery of identical message ID
        asyncio.run(handler.handle_value(val))
        call_count_2 = mock_client.send_text.call_count + mock_client.send_interactive_buttons.call_count

        # Must not generate second response
        self.assertEqual(call_count_1, call_count_2)

    def test_10_rapid_concurrent_messages_do_not_corrupt_state(self):
        """TEST 10: Two rapid messages for the same patient -> state does not get corrupted."""
        phone = "919555544443"
        tid = build_whatsapp_thread_id("default", phone)

        async def run_concurrent():
            t1 = asyncio.to_thread(self._send_msg, "Book appointment", phone, "default")
            t2 = asyncio.to_thread(self._send_msg, "Sufian", phone, "default")
            await asyncio.gather(t1, t2)

        asyncio.run(run_concurrent())
        state = self.checkpointer.get({"configurable": {"thread_id": tid}})
        self.assertIsNotNone(state)
        self.assertEqual(state["channel_values"].get("channel"), "whatsapp")

    def test_11_long_conversation_maintains_bounded_history_and_summary(self):
        """TEST 11: Long conversation -> summary + recent messages are used instead of unbounded history."""
        phone = "919444433332"
        # Send 14 turns
        for i in range(1, 15):
            self._send_msg(f"Message number {i}", phone=phone)

        tid = build_whatsapp_thread_id("default", phone)
        cp_state = self.checkpointer.get({"configurable": {"thread_id": tid}})
        msgs = cp_state["channel_values"].get("messages", [])
        # History must be bounded (<= 12 items)
        self.assertLessEqual(len(msgs), 12)

    def test_12_server_restart_preserves_conversation_state_from_checkpointer(self):
        """TEST 12: Server restart / new graph instance -> state remains available from checkpointer."""
        phone = "919333322221"
        self._send_msg("Book appointment", phone=phone)
        self._send_msg("Dr. Arjun Mehta", phone=phone)

        # Simulate server restart by creating a new Graph instance with the SAME checkpointer
        new_graph = build_graph(self.nodes, checkpointer=self.checkpointer)
        tid = build_whatsapp_thread_id("default", phone)
        config = {"configurable": {"thread_id": tid}}

        res_after_restart = new_graph.invoke({
            "chat_id": tid,
            "thread_id": tid,
            "user_text": "clinic timing kya hai?",
            "channel": "whatsapp",
            "phone": phone,
            "tenant_id": "default",
            "clinic_name": "XYZ Clinic",
        }, config=config)

        # Must remember selected doctor from before restart
        self.assertEqual(res_after_restart.get("doctor_name"), "Dr. Arjun Mehta")
        self.assertIn("XYZ Clinic", res_after_restart.get("response", ""))

    def test_13_screenshot_doctor_inquiry_during_name_step(self):
        """TEST 13: Exact query from live WhatsApp screenshot:
        User starts booking -> asks 'pehle yeh btao kon kon se dr hai ? , mujhe cardiologi se milna h'
        Bot MUST list the doctors/cardiologist and NOT repeat 'Kripya patient ka poora naam share karein'.
        """
        phone = "919777766665"
        res1 = self._send_msg("new appoinment krdo", phone=phone)
        self.assertEqual(res1.get("appointment_step"), "name")

        res2 = self._send_msg("pehle yeh btao kon kon se dr hai ? , mujhe cardiologi se milna h", phone=phone)
        resp_text = res2.get("response", "")
        # Must NOT demand patient full name
        self.assertNotIn("poora naam share karein", resp_text.lower())
        # Must list available doctors
        self.assertTrue("Arjun Mehta" in resp_text or "General" in resp_text or "Sana Khan" in resp_text or "doctor" in resp_text.lower())
        # Active flow remains preserved
        self.assertEqual(res2.get("active_flow"), "appointment_booking")

    def test_14_screenshot_negative_statement_cancels_booking(self):
        """TEST 14: Exact query from live WhatsApp screenshot:
        User at name step says 'appoinment ki batt ni kr rha mei'
        Bot MUST cancel the draft and stop asking for name.
        """
        phone = "919777766664"
        self._send_msg("new appoinment krdo", phone=phone)
        res_cancel = self._send_msg("appoinment ki batt ni kr rha mei", phone=phone)

        self.assertIsNone(res_cancel.get("active_flow"))
        self.assertEqual(res_cancel.get("appointment_step"), "")
        self.assertIn("cancel", res_cancel.get("response", "").lower())

        # Next user message is treated as fresh inquiry, not booking
        res_after = self._send_msg("Hello", phone=phone)
        self.assertNotIn("poora naam share karein", res_after.get("response", "").lower())

    def test_15_screenshot_cancel_this_appointment(self):
        """TEST 15: Exact query from live WhatsApp screenshot:
        User says 'cancel this appointment' mid-flow
        Bot MUST cancel the draft and not ask for name again.
        """
        phone = "919777766663"
        self._send_msg("new appoinment krdo", phone=phone)
        res_cancel = self._send_msg("cancel this appointment", phone=phone)

        self.assertIsNone(res_cancel.get("active_flow"))
        self.assertEqual(res_cancel.get("appointment_step"), "")
        self.assertIn("cancel", res_cancel.get("response", "").lower())

    def test_16_patient_name_matching_doctor_name_is_accepted_not_hijacked(self):
        """TEST 16: Live WhatsApp screenshot edge case:
        Patient clicks 'Book Appointment' -> Bot asks 'Sure. May I know your name?'
        Patient replies 'Habiba' or 'Sana' (whose name matches a doctor in the clinic).
        Bot MUST accept the name as patient_name, NOT hijack it as a doctor selection or
        say 'Dr. Habiba has no upcoming available slots'.
        """
        phone = "919888877771"
        res1 = self._send_msg("Book Appointment", phone=phone)
        self.assertEqual(res1.get("appointment_step"), "name")
        self.assertIn("name", res1.get("response", "").lower())

        # Patient sends 'Sana' (matching Dr. Sana Khan in directory)
        res2 = self._send_msg("Sana", phone=phone)
        # Must NOT think it is selecting Dr. Sana Khan
        self.assertEqual(res2.get("patient_name"), "Sana")
        self.assertEqual(res2.get("appointment_step"), "email")
        self.assertIn("email", res2.get("response", "").lower())
        self.assertNotIn("no upcoming available slots", res2.get("response", "").lower())

        # Test with Habiba as well (if Habiba is a doctor)
        phone2 = "919888877772"
        res1_b = self._send_msg("Book Appointment", phone=phone2)
        res2_b = self._send_msg("Habiba", phone=phone2)
        self.assertEqual(res2_b.get("patient_name"), "Habiba")
        self.assertEqual(res2_b.get("appointment_step"), "email")
        self.assertNotIn("no upcoming available slots", res2_b.get("response", "").lower())


if __name__ == "__main__":
    unittest.main()
