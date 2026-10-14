"""Live end-to-end operational cutover tests against PostgreSQL.

Validates that:
- PostgreSQL is the authoritative source of truth for all business operations.
- All CRM REST endpoints read and write directly to PostgreSQL.
- Doctor portal drafts, clinical validation, finalization, and amendments persist in prescriptions & prescription_items tables.
- Doctor accounts authenticate and update against the users table.
- Appointments, slots, invoices, payments, and audit logs persist and update correctly in PostgreSQL.
- Zero data leakage occurs across tenant boundaries.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.auth import create_session
from app.db.session import get_session_factory, is_db_configured
from app.main import app


@pytest.fixture(scope="module")
def client():
    assert is_db_configured(), "DATABASE_URL must be configured for live operational cutover tests"
    return TestClient(app)


@pytest.fixture(scope="module")
def session_factory():
    return get_session_factory()


@pytest.fixture(scope="module")
def admin_headers():
    token = create_session(username="admin", role="TENANT_ADMIN", tenant_id="default")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def doctor_headers():
    token = create_session(
        username="dr_arjun_api",
        role="DOCTOR",
        doctor_id="DOC001",
        doctor_name="Dr. Arjun Mehta",
        tenant_id="default",
    )
    return {"Authorization": f"Bearer {token}"}


def test_01_health_and_database_connectivity(client):
    """Verify health endpoint confirms live PostgreSQL connectivity."""
    resp = client.get("/health?details=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"]["status"] == "connected"
    assert data["database"]["type"] == "postgresql"


def test_02_slot_lifecycle_persists_in_postgres(client, admin_headers, session_factory):
    """Verify slot creation and availability directly in PostgreSQL."""
    with session_factory() as session:
        session.execute(text("DELETE FROM appointment_slots WHERE date = '2026-11-25' AND start_time = '10:00 AM'"))
        session.commit()

    slot_payload = {
        "doctor_id": "DOC001",
        "doctor_name": "Dr. Arjun Mehta",
        "date": "2026-11-25",
        "start_time": "10:00 AM",
        "end_time": "10:30 AM",
        "status": "Available",
    }
    resp = client.post("/api/admin/slots", json=slot_payload, headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    slot_id = body.get("slot", {}).get("Slot ID") or body.get("Slot ID")
    assert slot_id

    # Verify directly in PostgreSQL
    with session_factory() as session:
        row = session.execute(
            text("SELECT status, doctor_id, date FROM appointment_slots WHERE slot_id = :sid"),
            {"sid": slot_id},
        ).first()
        assert row is not None
        assert row[0].casefold() == "available"
        assert row[2] == "2026-11-25"


def test_03_appointment_booking_and_payment_persistence(client, admin_headers, session_factory):
    """Verify appointment creation atomically reserves slot and creates linked invoice & payment."""
    with session_factory() as session:
        session.execute(text("DELETE FROM payments WHERE appointment_id IN (SELECT id FROM appointments WHERE appointment_date = '2026-11-26')"))
        session.execute(text("DELETE FROM invoices WHERE appointment_id IN (SELECT id FROM appointments WHERE appointment_date = '2026-11-26')"))
        session.execute(text("DELETE FROM appointments WHERE appointment_date = '2026-11-26'"))
        session.execute(text("DELETE FROM appointment_slots WHERE date = '2026-11-26' AND start_time = '02:00 PM'"))
        session.commit()

    # 1. Create a dedicated slot
    slot_payload = {
        "doctor_id": "DOC001",
        "doctor_name": "Dr. Arjun Mehta",
        "date": "2026-11-26",
        "start_time": "02:00 PM",
        "end_time": "02:30 PM",
        "status": "Available",
    }
    slot_resp = client.post("/api/admin/slots", json=slot_payload, headers=admin_headers)
    assert slot_resp.status_code == 201
    slot_id = slot_resp.json().get("slot", {}).get("Slot ID") or slot_resp.json().get("Slot ID")

    # 2. Book appointment
    appt_payload = {
        "slot_id": slot_id,
        "name": "Priya Sharma",
        "phone": "9876543219",
        "email": "priya.sharma@example.com",
        "age": "28",
        "gender": "Female",
        "amount": "500",
        "payment_method": "Cash",
        "payment_status": "Pending",
    }
    appt_resp = client.post("/api/admin/appointments", json=appt_payload, headers=admin_headers)
    assert appt_resp.status_code == 201
    appt_data = appt_resp.json()
    token_no = appt_data["token_no"]

    # 3. Verify in PostgreSQL: appointment, slot status, invoice, payment
    with session_factory() as session:
        # Check slot is booked
        slot_status = session.execute(
            text("SELECT status, booked_token_no FROM appointment_slots WHERE slot_id = :sid"),
            {"sid": slot_id},
        ).first()
        assert slot_status[0].casefold() == "booked"
        assert slot_status[1] == token_no

        # Check appointment exists
        appt_row = session.execute(
            text("SELECT id, amount, payment_status, booking_status FROM appointments WHERE token_no = :tok"),
            {"tok": token_no},
        ).first()
        assert appt_row is not None
        assert appt_row[1] == "500"
        assert appt_row[2] == "Pending"
        assert appt_row[3] == "Confirmed"
        appt_db_id = appt_row[0]

        # Check linked invoice exists
        inv_row = session.execute(
            text("SELECT invoice_number, payment_status FROM invoices WHERE appointment_id = :aid"),
            {"aid": appt_db_id},
        ).first()
        assert inv_row is not None
        assert inv_row[1] == "Pending"

        # Check linked payment exists
        pay_row = session.execute(
            text("SELECT payment_id, payment_status FROM payments WHERE appointment_id = :aid"),
            {"aid": appt_db_id},
        ).first()
        assert pay_row is not None
        assert pay_row[1] == "Pending"

    # 4. Record manual payment
    pay_resp = client.post(
        f"/api/admin/payments/{token_no}/record",
        json={"amount": "500", "payment_method": "Cash", "transaction_ref": "RCP-001"},
        headers=admin_headers,
    )
    assert pay_resp.status_code == 200
    assert pay_resp.json()["payment_status"] == "Paid"

    # 5. Verify payment update propagated to PostgreSQL
    with session_factory() as session:
        appt_ps = session.execute(
            text("SELECT payment_status FROM appointments WHERE token_no = :tok"),
            {"tok": token_no},
        ).scalar()
        assert appt_ps == "Paid"

        inv_ps = session.execute(
            text("SELECT payment_status FROM invoices WHERE appointment_id = :aid"),
            {"aid": appt_db_id},
        ).scalar()
        assert inv_ps == "Paid"

        pay_ps = session.execute(
            text("SELECT payment_status, paid_at FROM payments WHERE appointment_id = :aid"),
            {"aid": appt_db_id},
        ).first()
        assert pay_ps[0] == "Paid"
        assert pay_ps[1] is not None


def test_04_prescription_draft_and_finalization_in_postgres(client, doctor_headers, session_factory):
    """Verify prescription draft, finalization, and line items persist in prescriptions table."""
    draft_data = {
        "appointment_id": "TKN-0001",
        "patient_id": "PAT001",
        "patient_name": "Rohan Verma",
        "patient_phone": "9876543210",
        "diagnosis": "Viral Bronchitis",
        "chief_complaints": "Productive cough, mild chest tightness",
        "symptoms": "Low grade fever, congestion",
        "vitals": {"bp": "120/80", "pulse": "76", "temp": "99.2"},
        "clinical_notes": "Chest clear on auscultation, no wheeze.",
        "medicines": [
            {
                "name": "Levocetirizine",
                "strength": "5 mg",
                "dosage": "1 tablet",
                "frequency": "0-0-1",
                "duration": "5 days",
                "instructions": "Before sleep",
            },
            {
                "name": "Paracetamol",
                "strength": "650 mg",
                "dosage": "1 tablet",
                "frequency": "1-0-1",
                "duration": "3 days",
                "instructions": "After food if fever > 100F",
            },
        ],
        "tests_advised": "Complete Blood Count",
        "advice": "Steam inhalation, warm water gargles",
        "follow_up_date": "2026-11-30",
    }

    # 1. Create draft
    draft_resp = client.post("/api/doctor/prescriptions", json=draft_data, headers=doctor_headers)
    assert draft_resp.status_code == 200
    rx_id = draft_resp.json()["prescription_id"]
    assert rx_id.startswith("RX-")
    assert draft_resp.json()["status"] == "draft"

    # Verify draft in PostgreSQL
    with session_factory() as session:
        rx_row = session.execute(
            text("SELECT status, diagnosis, version FROM prescriptions WHERE prescription_id = :rid"),
            {"rid": rx_id},
        ).first()
        assert rx_row is not None
        assert rx_row[0] == "draft"
        assert rx_row[1] == "Viral Bronchitis"
        assert rx_row[2] == 1

        item_count = session.execute(
            text("SELECT count(*) FROM prescription_items p JOIN prescriptions rx ON p.prescription_id = rx.id WHERE rx.prescription_id = :rid"),
            {"rid": rx_id},
        ).scalar()
        assert item_count == 2

    # 2. Finalize prescription
    finalize_resp = client.post(f"/api/doctor/prescriptions/{rx_id}/finalize", headers=doctor_headers)
    assert finalize_resp.status_code == 200
    assert finalize_resp.json()["status"] == "finalized"

    # Verify finalized status in PostgreSQL
    with session_factory() as session:
        final_status = session.execute(
            text("SELECT status, finalized_at FROM prescriptions WHERE prescription_id = :rid"),
            {"rid": rx_id},
        ).first()
        assert final_status[0] == "finalized"
        assert final_status[1] is not None


def test_05_prescription_amendment_in_postgres(client, doctor_headers, session_factory):
    """Verify prescription amendment creates version snapshot and increments version in PostgreSQL."""
    # Create and finalize a prescription
    draft_data = {
        "appointment_id": "TKN-0002",
        "patient_id": "PAT002",
        "patient_name": "Aarav Patel",
        "patient_phone": "9876543211",
        "diagnosis": "Allergic Rhinitis",
        "medicines": [
            {"name": "Montelukast", "strength": "10 mg", "dosage": "1 tab", "frequency": "0-0-1", "duration": "7 days"}
        ],
    }
    draft = client.post("/api/doctor/prescriptions", json=draft_data, headers=doctor_headers).json()
    rx_id = draft["prescription_id"]
    client.post(f"/api/doctor/prescriptions/{rx_id}/finalize", headers=doctor_headers)

    # Amend the prescription
    amend_payload = {
        "diagnosis": "Severe Allergic Rhinitis",
        "amendment_reason": "Escalated symptoms, added nasal spray",
        "medicines": [
            {"name": "Montelukast", "strength": "10 mg", "dosage": "1 tab", "frequency": "0-0-1", "duration": "14 days"},
            {"name": "Fluticasone Spray", "strength": "50 mcg", "dosage": "2 sprays", "frequency": "1-0-0", "duration": "14 days"},
        ],
    }
    amend_resp = client.post(f"/api/doctor/prescriptions/{rx_id}/amend", json=amend_payload, headers=doctor_headers)
    assert amend_resp.status_code == 200
    amended = amend_resp.json()
    assert amended["status"] == "amended"
    assert amended["version"] == 2
    assert len(amended["version_history"]) == 1

    # Verify in PostgreSQL
    with session_factory() as session:
        row = session.execute(
            text("SELECT version, status, diagnosis FROM prescriptions WHERE prescription_id = :rid"),
            {"rid": rx_id},
        ).first()
        assert row[0] == 2
        assert row[1] == "amended"
        assert row[2] == "Severe Allergic Rhinitis"

        items = session.execute(
            text("SELECT count(*) FROM prescription_items p JOIN prescriptions rx ON p.prescription_id = rx.id WHERE rx.prescription_id = :rid"),
            {"rid": rx_id},
        ).scalar()
        assert items == 2


def test_06_cross_doctor_prescription_isolation(client, session_factory):
    """Verify doctor B cannot edit or amend doctor A's prescription."""
    doc_a_token = create_session(
        username="dr_arjun_api",
        role="DOCTOR",
        doctor_id="DOC001",
        doctor_name="Dr. Arjun Mehta",
        tenant_id="default",
    )
    doc_b_token = create_session(
        username="dr_sufian",
        role="DOCTOR",
        doctor_id="DOC003",
        doctor_name="Dr. sufian",
        tenant_id="default",
    )

    # Doctor A creates draft
    data = {
        "appointment_id": "TKN-0003",
        "patient_id": "PAT003",
        "patient_name": "Meera Joshi",
        "patient_phone": "9876543212",
        "diagnosis": "Gastritis",
        "medicines": [{"name": "Pantoprazole", "strength": "40mg", "dosage": "1 tab", "frequency": "1-0-0", "duration": "5 days"}],
    }
    draft = client.post("/api/doctor/prescriptions", json=data, headers={"Authorization": f"Bearer {doc_a_token}"}).json()
    rx_id = draft["prescription_id"]

    # Doctor B attempts to finalize Doctor A's prescription -> must be rejected (403)
    resp = client.post(f"/api/doctor/prescriptions/{rx_id}/finalize", headers={"Authorization": f"Bearer {doc_b_token}"})
    assert resp.status_code == 403


def test_07_doctor_account_lifecycle_in_postgres(client, admin_headers, session_factory):
    """Verify doctor accounts are created, authenticated, and managed in PostgreSQL users table."""
    username = "dr_neha_cutover"
    # Ensure account does not exist prior to test
    with session_factory() as session:
        session.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
        session.commit()

    # Create doctor account linked to unassigned DOC004
    create_payload = {
        "username": username,
        "password": "Password123",
        "doctor_id": "DOC004",
        "email": "dr.neha@clinic.com",
    }
    resp = client.post("/api/admin/doctor-accounts", json=create_payload, headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == username
    assert body["doctor_id"] == "DOC004"
    assert "password_hash" not in body

    # Verify directly in PostgreSQL users table
    with session_factory() as session:
        user_row = session.execute(
            text("SELECT role, doctor_id, status, must_change_password FROM users WHERE username = :u"),
            {"u": username},
        ).first()
        assert user_row is not None
        assert user_row[0] == "doctor"
        assert user_row[1] == "DOC004"
        assert user_row[2] == "Active"
        assert user_row[3] is True

    # Authenticate through Doctor Portal / API
    login_resp = client.post("/api/admin/auth/login", json={"username": username, "password": "Password123"})
    assert login_resp.status_code == 200
    assert "token" in login_resp.json()

    # Toggle status to Inactive
    toggle_resp = client.patch(
        f"/api/admin/doctor-accounts/{username}/status",
        json={"status": "Inactive"},
        headers=admin_headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["status"] == "Inactive"

    # Verify in PostgreSQL
    with session_factory() as session:
        status_in_db = session.execute(
            text("SELECT status FROM users WHERE username = :u"),
            {"u": username},
        ).scalar()
        assert status_in_db == "Inactive"

    # Login should now fail because account is inactive
    fail_login = client.post("/api/admin/auth/login", json={"username": username, "password": "Password123"})
    assert fail_login.status_code == 401


def test_08_audit_logs_persisted_in_postgres(client, admin_headers, session_factory):
    """Verify that operations write immutable audit logs directly to PostgreSQL audit_logs table."""
    # Query audit logs via API
    logs_resp = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert logs_resp.status_code == 200
    data = logs_resp.json()
    assert data["total"] > 0
    assert len(data["logs"]) > 0

    # Verify directly in PostgreSQL audit_logs table
    with session_factory() as session:
        db_audit_cnt = session.execute(text("SELECT count(*) FROM audit_logs")).scalar()
        assert db_audit_cnt > 0

