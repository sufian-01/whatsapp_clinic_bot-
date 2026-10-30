import unittest
from datetime import date
from unittest.mock import MagicMock
from app.graph.checkpoint import MemorySaver
from app.graph.graph import build_graph, build_whatsapp_thread_id
from app.graph.nodes import GraphNodes
from app.tools.doctors import DoctorDirectory

class LiveChatIssuesTests(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock()
        self.llm.answer.return_value = "Dr. Vivek Singh is available."
        self.llm.classify.return_value = {"intent": "doctor_list"}
        self.rag = MagicMock()
        raw_chunk = (
            "llowed. The chatbot should not invent preparation instructions when the knowledge base does not contain them.\n"
            "6. Frequently Asked Questions\nQ: Where is XYZ Clinic located?\nA: XYZ Clinic & Diagnostics is located at 24, Green Park..."
        )
        self.rag.similarity_search.return_value = [MagicMock(page_content=raw_chunk)]

        rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee", "Available Days", "Start Time", "End Time", "Status"],
            ["DOC001", "Dr. Arjun Mehta", "General Physician", "500", "Monday, Wednesday, Friday", "10:00 AM", "1:00 PM", "Active"],
            ["DOC002", "Dr. Sana Khan", "Gynecologist", "700", "Tuesday, Thursday, Saturday", "4:00 PM", "7:00 PM", "Active"],
            ["DOC003", "Dr. sufian", "Cardiologist", "900", "Monday, Tuesday, Wednesday", "03:00 PM", "05:30 PM", "Active"],
            ["DOC007", "Dr. Vivek Singh", "Cardiologist", "1200", "Monday, Wednesday, Friday", "04:30 PM", "07:00 PM", "Active"],
        ]
        self.doc_dir = DoctorDirectory(lambda: rows)
        self.slots = MagicMock()
        self.patients = MagicMock()

        self.nodes = GraphNodes(
            clinic_name="XYZ Hospital & Clinic",
            llm=self.llm,
            rag=self.rag,
            doctors=self.doc_dir,
            support_phone="6200126662",
            patients=self.patients,
            slots=self.slots,
            today_provider=lambda: date(2026, 10, 30),
        )
        self.checkpointer = MemorySaver()
        self.graph = build_graph(self.nodes, checkpointer=self.checkpointer)

    def _send(self, text: str, phone: str = "919999900010"):
        tid = build_whatsapp_thread_id("default", phone)
        cfg = {"configurable": {"thread_id": tid}}
        state = {
            "chat_id": tid,
            "thread_id": tid,
            "user_text": text,
            "channel": "whatsapp",
            "phone": phone,
            "patient_phone": phone,
            "tenant_id": "default",
            "clinic_id": "default",
            "clinic_name": "XYZ Hospital & Clinic",
            "support_phone": "6200126662",
            "feature_flags": {
                "ai_agent": True,
                "booking_guard_v2": True,
                "smart_intent_v2": True,
                "rag_v2": True,
                "family_booking": True,
            },
        }
        return self.graph.invoke(state, config=cfg)

    def test_issue1_no_raw_chunk_dump_on_cardio_question(self):
        """Image 1 & 2: Asking for cardio doctor recommendation MUST NOT dump raw knowledge chunk and only show cardiologists."""
        self._send("Book Appointment")
        r = self._send("inmei se cardio ke liye konse dr. best hai ?")
        resp = r.get("response", "")
        self.assertNotIn("llowed. The chatbot", resp)
        self.assertNotIn("invent preparation instructions", resp)
        self.assertIn("sufian", resp)
        self.assertIn("Vivek", resp)
        self.assertNotIn("Arjun", resp)
        self.assertNotIn("Sana", resp)

    def test_issue3_koi_aur_dr_on_date(self):
        """Image 3: When doctor has no slots, asking 'koi aur dr. baith rhe hai 30 october ko ?' switches doctor."""
        self._send("Book Appointment")
        self._send("Dr. sufian")
        self.slots.get_available_slots.return_value = []
        r1 = self._send("30 october")
        self.assertIn("no available slots", r1.get("response", "").lower())

        # Setup mock snapshot so get_available_doctors_for_date finds Dr. Vivek Singh on 2026-10-30
        self.slots._snapshot.return_value = (
            {},
            [
                {"Doctor Name": "Dr. Vivek Singh", "Date": "2026-10-30", "Status": "Available"}
            ]
        )
        r2 = self._send("koi aur dr. baith rhe hai 30 october ko ?")
        resp2 = r2.get("response", "")
        # MUST NOT repeat that Dr. sufian has no slots!
        self.assertNotIn("dr. sufian has no available slots", resp2.lower())
        self.assertIn("Vivek", resp2)

    def test_issue4_dr_vivek_with_question_mark(self):
        """Image 4: Asking 'dr vivek ?' MUST resolve Dr. Vivek, not dump generic doctor list."""
        self._send("Book Appointment")
        self.slots.get_upcoming_available_slots.return_value = [
            {"Slot ID": "S1", "Doctor ID": "DOC007", "Doctor Name": "Dr. Vivek Singh", "Date": "2026-11-01", "Start Time": "10:00 AM", "End Time": "10:30 AM", "Status": "Available"}
        ]
        r = self._send("dr vivek ?")
        resp = r.get("response", "")
        # Should be selecting Dr. Vivek
        self.assertIn("Vivek", resp)
        self.assertNotIn("Dr. Arjun Mehta", resp)

    def test_issue5_hi_does_not_ask_for_date(self):
        """Image 5: Saying 'hi' during date step MUST NOT say 'Maaf kijiye, aap kis date ki baat kar rahe hain'."""
        self._send("Book Appointment")
        self._send("Dr. sufian")
        r = self._send("hi")
        resp = r.get("response", "")
        self.assertNotIn("30 September", resp)
        self.assertNotIn("kis date ki baat kar rahe hain", resp)
        self.assertIn("Namaste", resp)
        self.assertIn("Dr. sufian", resp)

if __name__ == "__main__":
    unittest.main()
