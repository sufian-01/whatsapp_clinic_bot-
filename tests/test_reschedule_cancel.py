"""Comprehensive test suite for Appointment Rescheduling & Cancellation.

Covers:
1. CrmService reschedule & cancel logic (safety, zero-loss, slot release).
2. Admin REST API endpoints (POST /api/admin/appointments/{id}/reschedule & cancel).
3. Chatbot LangGraph router classification (reschedule, cancel, my appointments, Hinglish).
4. Chatbot LangGraph nodes execution (reschedule_node, cancel_node, my_appointments_node).
"""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.auth import create_session
from app.services.crm_service import CrmService
from app.api.admin import create_admin_router
from app.graph.router import classify_intent, _is_reschedule_query, _is_cancel_query, _is_my_appointments_query
from app.graph.nodes import GraphNodes


class FakePatientRepo:
    def __init__(self, records=None):
        self.records = records or []

    def list_patients(self):
        return [dict(r) for r in self.records]

    def find_by_token(self, token_no):
        for r in self.records:
            if r.get("Token No", "").strip().casefold() == token_no.strip().casefold():
                return dict(r)
        return None

    def update_booking_status(self, identifier, new_status):
        for r in self.records:
            if r.get("Token No") == identifier or r.get("Patient ID") == identifier:
                r["Booking Status"] = new_status
                r["Status"] = new_status
                return {"success": True, "token_no": r.get("Token No"), "status": new_status}
        return {"success": False, "message": f"Appointment {identifier} not found"}

    def update_appointment_details(self, identifier, updates):
        for r in self.records:
            if r.get("Token No") == identifier or r.get("Patient ID") == identifier:
                if "appointment_date" in updates:
                    r["Appointment Date"] = updates["appointment_date"]
                if "appointment_time" in updates:
                    r["Appointment Time"] = updates["appointment_time"]
                return {"success": True, "token_no": r.get("Token No")}
        return {"success": False, "message": f"Appointment {identifier} not found"}


class FakeSlotRepo:
    def __init__(self, slots=None):
        self.slots = slots or []

    def get_slot_by_id(self, slot_id):
        for s in self.slots:
            if s.get("Slot ID") == slot_id:
                return dict(s)
        return None

    def find_slot_by_booking(self, token_no=None, patient_id=None, doctor_name=None, date=None, start_time=None):
        for s in self.slots:
            if token_no and s.get("Token No") == token_no:
                return dict(s)
            if patient_id and s.get("Patient ID") == patient_id and s.get("Date") == date:
                return dict(s)
        return None

    def book_slot(self, slot_id, patient_id, token_no):
        for s in self.slots:
            if s.get("Slot ID") == slot_id:
                if s.get("Status", "").casefold() != "available":
                    return {"success": False, "message": "Slot unavailable"}
                s["Status"] = "Booked"
                s["Patient ID"] = patient_id
                s["Token No"] = token_no
                return {"success": True, "slot_id": slot_id}
        return {"success": False, "message": "Slot not found"}

    def release_slot_if_needed(self, slot_id, patient_id=None):
        for s in self.slots:
            if s.get("Slot ID") == slot_id:
                s["Status"] = "Available"
                s["Patient ID"] = ""
                s["Token No"] = ""
                return {"success": True, "slot_id": slot_id}
        return {"success": False, "message": "Slot not found"}

    def get_available_slots(self, doctor_name, date_str):
        matched = [
            dict(s) for s in self.slots
            if s.get("Doctor Name", "").casefold() == doctor_name.casefold()
            and s.get("Date") == date_str
            and s.get("Status", "").casefold() == "available"
        ]
        return {"success": True, "slots": matched}


@pytest.fixture
def sample_data():
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()

    patients = [
        {
            "Patient ID": "PAT-001",
            "Name": "Aarav Sharma",
            "Phone": "9876543210",
            "Email": "aarav@example.com",
            "Doctor": "Dr. Arjun Mehta",
            "Appointment Date": tomorrow,
            "Appointment Time": "10:00 AM",
            "Token No": "TKN-1001",
            "Amount": "500",
            "Payment Method": "Offline",
            "Payment Status": "Pending",
            "Booking Status": "Confirmed",
            "Status": "Confirmed",
        },
        {
            "Patient ID": "PAT-002",
            "Name": "Pooja Verma",
            "Phone": "9811122233",
            "Email": "pooja@example.com",
            "Doctor": "Dr. Sana Khan",
            "Appointment Date": next_week,
            "Appointment Time": "02:00 PM",
            "Token No": "TKN-1002",
            "Amount": "700",
            "Payment Method": "Offline",
            "Payment Status": "Pending",
            "Booking Status": "Completed",
            "Status": "Completed",
        },
    ]

    slots = [
        # Old slot currently booked for TKN-1001
        {
            "Slot ID": "SLOT-OLD-1",
            "Doctor ID": "DOC-1",
            "Doctor Name": "Dr. Arjun Mehta",
            "Date": tomorrow,
            "Start Time": "10:00 AM",
            "End Time": "10:30 AM",
            "Status": "Booked",
            "Patient ID": "PAT-001",
            "Token No": "TKN-1001",
        },
        # Target open slot
        {
            "Slot ID": "SLOT-NEW-2",
            "Doctor ID": "DOC-1",
            "Doctor Name": "Dr. Arjun Mehta",
            "Date": next_week,
            "Start Time": "11:00 AM",
            "End Time": "11:30 AM",
            "Status": "Available",
            "Patient ID": "",
            "Token No": "",
        },
    ]

    return FakePatientRepo(patients), FakeSlotRepo(slots)


# ===========================================================================
# 1. CrmService Unit Tests
# ===========================================================================

def test_crm_reschedule_success(sample_data):
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo, clinic_name="Test Clinic")

    res = crm.reschedule_appointment(
        identifier="TKN-1001",
        new_slot_id="SLOT-NEW-2",
    )

    assert res["success"] is True
    assert res["new_slot_id"] == "SLOT-NEW-2"
    assert res["old_slot_id"] == "SLOT-OLD-1"

    # Verify new slot is now booked
    new_slot = s_repo.get_slot_by_id("SLOT-NEW-2")
    assert new_slot["Status"] == "Booked"
    assert new_slot["Token No"] == "TKN-1001"
    assert new_slot["Patient ID"] == "PAT-001"

    # Verify old slot is released to Available
    old_slot = s_repo.get_slot_by_id("SLOT-OLD-1")
    assert old_slot["Status"] == "Available"
    assert old_slot["Token No"] == ""

    # Verify patient sheet updated with new date & time
    appt = crm.get_appointment("TKN-1001")
    assert appt["time"] == "11:00 AM"


def test_crm_reschedule_rejects_completed(sample_data):
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo)

    with pytest.raises(ValueError, match="Completed appointments cannot be rescheduled"):
        crm.reschedule_appointment(
            identifier="TKN-1002",  # Completed appointment
            new_slot_id="SLOT-NEW-2",
        )


def test_crm_cancel_success(sample_data):
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo)

    res = crm.cancel_appointment(identifier="TKN-1001", reason="Family emergency")
    assert res["success"] is True
    assert res["status"] == "Cancelled"

    # Verify status changed in repo
    appt = crm.get_appointment("TKN-1001")
    assert appt["status"] == "Cancelled"

    # Verify slot was freed
    old_slot = s_repo.get_slot_by_id("SLOT-OLD-1")
    assert old_slot["Status"] == "Available"
    assert old_slot["Token No"] == ""


def test_crm_cancel_rejects_already_cancelled(sample_data):
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo)

    crm.cancel_appointment(identifier="TKN-1001")

    with pytest.raises(ValueError, match="already cancelled"):
        crm.cancel_appointment(identifier="TKN-1001")


# ===========================================================================
# 2. Admin REST API Tests
# ===========================================================================

def test_admin_api_reschedule_and_cancel(sample_data):
    from fastapi import FastAPI
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo)
    from pathlib import Path
    settings = Settings(
        clinic_name="Hope Clinic",
        telegram_bot_token="fake_token",
        telegram_webhook_secret="fake_secret",
        gemini_api_key="fake_key",
        gemini_model="gemini-2.0-flash",
        telegram_webhook_url="https://example.com/webhook",
        knowledge_dir=Path("./data/knowledge"),
        vectorstore_dir=Path("./data/vectorstore"),
        crm_admin_username="admin",
        crm_admin_password="password123",
    )

    app = FastAPI()
    app.include_router(create_admin_router(crm, settings))
    client = TestClient(app)

    token = create_session("admin", "admin")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Reschedule via API
    res = client.post(
        "/api/admin/appointments/TKN-1001/reschedule",
        json={"new_slot_id": "SLOT-NEW-2"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["new_slot_id"] == "SLOT-NEW-2"

    # 2. Cancel via API
    res = client.post(
        "/api/admin/appointments/TKN-1001/cancel",
        json={"reason": "Schedule change"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "Cancelled"


# ===========================================================================
# 3. Router Intent Classification Tests
# ===========================================================================

def test_router_reschedule_intent_detection():
    cases = [
        "I need to reschedule my appointment",
        "Can I change my appointment date to tomorrow?",
        "Please change time for token TKN-1001",
        "Mujhe appointment reschedule karni hai",
        "Mera booking badal do please",
        "Kal ka time change karna hai",
        "Dusra time mil sakta hai kya?",
    ]
    for text in cases:
        res = classify_intent({"user_text": text})
        assert res["intent"] == "appointment_reschedule", f"Failed on '{text}'"


def test_router_cancel_intent_detection():
    cases = [
        "Cancel my appointment",
        "I want to cancel booking TKN-1001",
        "Please drop my appointment",
        "Mera appointment cancel kar do",
        "Appointment radd karni hai",
        "Mujhe kal nahi aana booking cancel karo",
    ]
    for text in cases:
        res = classify_intent({"user_text": text})
        assert res["intent"] == "appointment_cancel", f"Failed on '{text}'"


def test_router_my_appointments_intent_detection():
    cases = [
        "Show my upcoming appointments",
        "My appointment details",
        "When is my appointment?",
        "Mera appointment kab hai?",
        "Meri booking check karo",
    ]
    for text in cases:
        res = classify_intent({"user_text": text})
        assert res["intent"] == "patient_appointments", f"Failed on '{text}'"


# ===========================================================================
# 4. Chatbot LangGraph Nodes Tests
# ===========================================================================

def test_chatbot_reschedule_flow(sample_data):
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo)
    nodes = GraphNodes(
        clinic_name="City Clinic",
        llm=None,
        rag=None,
        patients=p_repo,
        slots=s_repo,
        crm_service=crm,
    )

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()

    # Step 1: User says "reschedule TKN-1001"
    s1 = {"user_text": "I want to reschedule appointment TKN-1001"}
    r1 = nodes.reschedule_node(s1)
    assert r1["reschedule_step"] == "select_date"
    assert "Dr. Arjun Mehta" in r1["response"]

    # Step 2: User provides new date
    s2 = {**r1, "user_text": next_week}
    r2 = nodes.reschedule_node(s2)
    assert r2["reschedule_step"] == "select_slot"
    assert r2["ui"] == "slots"
    assert len(r2["available_slots"]) > 0

    # Step 3: User picks slot
    s3 = {**r2, "user_text": "slot:SLOT-NEW-2"}
    r3 = nodes.reschedule_node(s3)
    assert r3["reschedule_step"] == "confirm"
    assert r3["ui"] == "reschedule_confirm"
    assert "Reschedule Confirmation" in r3["response"]

    # Step 4: User confirms
    s4 = {**r3, "user_text": "confirm_reschedule"}
    r4 = nodes.reschedule_node(s4)
    assert r4["reschedule_step"] == ""
    assert "Appointment Rescheduled Successfully" in r4["response"]

    # Verify slot was updated in repository
    assert s_repo.get_slot_by_id("SLOT-NEW-2")["Status"] == "Booked"
    assert s_repo.get_slot_by_id("SLOT-OLD-1")["Status"] == "Available"


def test_chatbot_cancel_flow(sample_data):
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo)
    nodes = GraphNodes(
        clinic_name="City Clinic",
        llm=None,
        rag=None,
        patients=p_repo,
        slots=s_repo,
        crm_service=crm,
    )

    # Step 1: User says "cancel TKN-1001"
    s1 = {"user_text": "cancel my booking TKN-1001"}
    r1 = nodes.cancel_node(s1)
    assert r1["cancel_step"] == "confirm"
    assert r1["ui"] == "cancel_confirm"
    assert "Confirm Appointment Cancellation" in r1["response"]

    # Step 2: User confirms cancellation
    s2 = {**r1, "user_text": "confirm_cancel"}
    r2 = nodes.cancel_node(s2)
    assert r2["cancel_step"] == ""
    assert "successfully cancelled" in r2["response"]

    # Verify slot was released
    assert s_repo.get_slot_by_id("SLOT-OLD-1")["Status"] == "Available"


def test_chatbot_my_appointments_flow(sample_data):
    p_repo, s_repo = sample_data
    crm = CrmService(patients_tools=p_repo, slots_tools=s_repo)
    nodes = GraphNodes(
        clinic_name="City Clinic",
        llm=None,
        rag=None,
        patients=p_repo,
        slots=s_repo,
        crm_service=crm,
    )

    # Query with phone number
    s = {"user_text": "Show appointments for 9876543210"}
    r = nodes.my_appointments_node(s)
    assert "Your Upcoming Appointments" in r["response"]
    assert "TKN-1001" in r["response"]
    assert "Dr. Arjun Mehta" in r["response"]
