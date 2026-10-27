"""Tests for Razorpay online payment integration, Super Admin logo, and Admin/Doctor settings & branding."""

import base64
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.auth import clear_failed_login, create_session
from app.main import create_app
from app.services.razorpay_service import RazorpayService
from app.tools.payments import PaymentTools
from app.tools.prescription_pdf import PrescriptionPDFData, generate_prescription_pdf


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CRM_ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("ALLOW_DEMO_PASSWORD", "true")
    clear_failed_login("admin")
    app = create_app()
    return TestClient(app)


def test_razorpay_service_sandbox_and_links():
    service = RazorpayService(
        default_key_id="rzp_test_sampleKeyId123",
        default_key_secret="sampleSecret123",
        default_upi_id="clinic@upi",
    )
    res = service.create_payment(
        amount="500",
        clinic_name="City Specialty Clinic",
        patient_name="Rahul Kumar",
        patient_phone="9876543210",
        appointment_id="TK-101",
        doctor_name="Dr. Sufian",
    )
    assert res["status"] in ("Created", "Pending")
    assert "payment_id" in res
    assert res["payment_id"].upper().startswith("PAY")
    assert "short_url" in res
    assert "upi_uri" in res
    assert "upi://pay?" in res["upi_uri"]
    assert "pa=clinic%40upi" in res["upi_uri"] or "pa=clinic@upi" in res["upi_uri"]
    assert "am=500.00" in res["upi_uri"]


def test_razorpay_signature_verification():
    import hmac
    import hashlib
    secret = "testSecretKey"
    service = RazorpayService(default_key_secret=secret)
    order_id = "order_12345"
    payment_id = "pay_67890"
    message = f"{order_id}|{payment_id}"
    valid_sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    assert service.verify_payment_signature(order_id, payment_id, valid_sig, key_secret=secret) is True
    assert service.verify_payment_signature(order_id, payment_id, "invalid_sig", key_secret=secret) is False


def test_payment_tools_online_flow():
    tools = PaymentTools(upi_id="clinic@upi")
    res = tools.create_online_payment(
        amount="600",
        clinic_name="Alpha Clinic",
        patient_name="Amina",
        patient_phone="9876500000",
        appointment_id="TK-202",
        doctor_name="Dr. Arjun",
    )
    assert res["amount"] == 600.0
    pid = res["payment_id"]

    stat = tools.get_payment_status(pid)
    assert stat["success"] is True

    mark_res = tools.mark_payment_status(pid, "Paid", transaction_reference="pay_rzp_mock123")
    assert mark_res["success"] is True
    assert mark_res["status"] == "Paid"


def test_admin_settings_get_and_put(client):
    # 1. Admin login
    res_login = client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_login.status_code == 200
    token = res_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET clinic settings
    res_get = client.get("/api/admin/settings", headers=headers)
    assert res_get.status_code == 200
    settings_data = res_get.json()
    assert "clinic_name" in settings_data

    # 3. PUT clinic settings (branding & razorpay config)
    dummy_logo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    res_put = client.put(
        "/api/admin/settings",
        headers=headers,
        json={
            "clinic_name": "Metro Super Specialty Clinic",
            "support_phone": "6200129999",
            "clinic_address": "MG Road, Suite 400",
            "logo": dummy_logo,
            "razorpay_key_id": "rzp_test_testKey987",
            "razorpay_key_secret": "mySuperSecretKey123",
            "upi_id": "metroclinic@upi",
        },
    )
    assert res_put.status_code == 200
    updated = res_put.json()
    assert updated["clinic_name"] == "Metro Super Specialty Clinic"
    assert updated["logo"] == dummy_logo
    assert updated["razorpay_key_id"] == "rzp_test_testKey987"
    assert updated["upi_id"] == "metroclinic@upi"


def test_doctor_profile_get_and_put(client):
    # 1. Admin login to get doc ID
    res_login = client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin123"})
    token = res_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_docs = client.get("/api/admin/doctors", headers=headers)
    assert res_docs.status_code == 200
    docs = res_docs.json()
    valid_doc_id = docs[0]["Doctor ID"] if docs else "DOC001"

    import uuid
    uid_str = uuid.uuid4().hex[:6]
    test_doc_id = f"DOC_T_{uid_str}"
    test_doc_name = f"Dr. Test {uid_str}"

    res_add_doc = client.post(
        "/api/admin/doctors",
        headers=headers,
        json={
            "name": test_doc_name,
            "specialization": "Cardiology",
            "consultation_fee": "500",
        },
    )
    assert res_add_doc.status_code in (200, 201)
    doc_data = res_add_doc.json()
    created_doc_id = doc_data.get("Doctor ID") or doc_data.get("id") or test_doc_id

    doc_user = f"dr_{uid_str}"
    clear_failed_login(doc_user)

    # Create / ensure doctor user exists
    res_create_doc = client.post(
        "/api/admin/doctor-accounts",
        headers=headers,
        json={
            "username": doc_user,
            "password": "pass1234_demo",
            "doctor_id": created_doc_id,
            "email": f"{doc_user}@test.com",
        },
    )
    assert res_create_doc.status_code in (200, 201)

    # Login as doctor
    res_doc_login = client.post("/api/admin/auth/login", json={"username": doc_user, "password": "pass1234_demo"})
    assert res_doc_login.status_code == 200
    doc_token = res_doc_login.json()["token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # GET doctor profile
    res_prof = client.get("/api/doctor/profile", headers=doc_headers)
    assert res_prof.status_code == 200

    # PUT doctor profile with photo and signature
    dummy_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    res_update = client.put(
        "/api/doctor/profile",
        headers=doc_headers,
        json={
            "qualification": "MBBS, MD (Medicine)",
            "registration_no": "MCI-2021-99881",
            "phone": "9812345678",
            "photo": "https://example.com/dr_photo.jpg",
            "signature": dummy_sig,
        },
    )
    assert res_update.status_code == 200
    updated_doc = res_update.json()
    assert updated_doc.get("Qualification") == "MBBS, MD (Medicine)" or updated_doc.get("qualification") == "MBBS, MD (Medicine)"
    assert updated_doc.get("Signature") == dummy_sig or updated_doc.get("signature") == dummy_sig

    # Teardown test doctor and account
    from app.db.session import get_session_factory
    from app.db.models.doctor import Doctor
    from app.db.models.user import User
    sf = get_session_factory()
    with sf() as session:
        session.query(User).filter(User.username == doc_user).delete()
        session.query(Doctor).filter((Doctor.id == created_doc_id) | (Doctor.doctor_id == created_doc_id)).delete()
        session.commit()


def test_razorpay_verify_and_simulate_endpoints(client):
    res_login = client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin123"})
    token = res_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a fresh available slot or pick available
    import uuid
    rand_suffix = uuid.uuid4().hex[:6]
    res_add_doc = client.post(
        "/api/admin/doctors",
        headers=headers,
        json={
            "name": f"Dr. PayTest {rand_suffix}",
            "specialization": "Cardiology",
            "consultation_fee": "500",
        },
    )
    if res_add_doc.status_code in (200, 201):
        d_json = res_add_doc.json()
        valid_doc = d_json.get("Doctor ID") or d_json.get("id")
        valid_doc_name = d_json.get("Doctor Name") or f"Dr. PayTest {rand_suffix}"
    else:
        res_docs = client.get("/api/admin/doctors", headers=headers)
        docs_json = res_docs.json() if res_docs.status_code == 200 else []
        valid_doc = docs_json[0].get("Doctor ID") or docs_json[0].get("id") if docs_json else "DOC001"
        valid_doc_name = docs_json[0].get("Doctor Name", "Dr. Specialist") if docs_json else "Dr. Specialist"

    slot_id = None
    res_slot = client.post(
        "/api/admin/slots",
        headers=headers,
        json={
            "doctor_id": valid_doc,
            "doctor_name": valid_doc_name,
            "date": f"2026-11-{(uuid.uuid4().int % 25) + 1:02d}",
            "start_time": f"{(uuid.uuid4().int % 12) + 8:02d}:{(uuid.uuid4().int % 50):02d}",
            "end_time": "18:00",
            "status": "Available",
        },
    )
    if res_slot.status_code in (200, 201):
        slot_data = res_slot.json()
        slot_id = slot_data.get("slot", {}).get("Slot ID") or slot_data.get("id") or slot_data.get("slot_id")

    if not slot_id:
        slots_res = client.get("/api/admin/slots", headers=headers)
        avail = [s for s in slots_res.json() if str(s.get("Status") or s.get("status", "")).title() == "Available"]
        if avail:
            slot_id = avail[0].get("Slot ID") or avail[0].get("id") or avail[0].get("slot_id")

    create_appt = client.post(
        "/api/admin/appointments",
        headers=headers,
        json={
            "slot_id": slot_id,
            "name": "Ananya Sharma",
            "phone": "9988776655",
            "amount": "500",
            "payment_method": "Razorpay / UPI",
            "payment_status": "Pending",
        },
    )
    assert create_appt.status_code in (200, 201)
    appt_data = create_appt.json()
    appt_id = appt_data.get("token_no") or appt_data.get("id") or "TK-APP"

    # 2. Simulate Razorpay payment capture
    sim_res = client.post(f"/api/admin/payments/{appt_id}/simulate-razorpay-success", headers=headers)
    assert sim_res.status_code == 200
    sim_json = sim_res.json()
    assert sim_json.get("success") is True
    assert sim_json.get("payment_status") == "Paid"

    # 3. Direct verification endpoint test
    verify_res = client.post(
        "/api/admin/payments/razorpay/verify",
        headers=headers,
        json={
            "payment_id": appt_id,
            "razorpay_payment_id": "pay_live_mock_verify_99",
            "razorpay_order_id": "order_mock_99",
        },
    )
    assert verify_res.status_code == 200
    assert verify_res.json().get("success") is True
    assert verify_res.json().get("payment_status") == "Paid"

    # Teardown appointment, payment, slot, and test doctor
    from app.db.session import get_session_factory
    from app.db.models.appointment import Appointment
    from app.db.models.payment import Payment
    from app.db.models.slot import AppointmentSlot
    from app.db.models.doctor import Doctor
    sf = get_session_factory()
    with sf() as session:
        session.query(Payment).filter(Payment.appointment_id == appt_id).delete()
        session.query(Appointment).filter(Appointment.token_no == appt_id).delete()
        if slot_id:
            session.query(AppointmentSlot).filter(AppointmentSlot.slot_id == slot_id).delete()
        if valid_doc and str(valid_doc).startswith("DOC"):
            session.query(Doctor).filter(Doctor.doctor_id == valid_doc).delete()
        session.commit()


def test_prescription_pdf_with_logo_and_signature():
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_1px_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        data = PrescriptionPDFData(
            clinic_name="Apex Care Center",
            clinic_phone="+91 9999988888",
            clinic_email="support@apex.com",
            clinic_address="Sector 14, Health City",
            doctor_name="Dr. Sufian",
            doctor_specialization="Cardiology",
            patient_id="PID-101",
            patient_name="Sameer Verma",
            patient_phone="+91 9876543210",
            patient_age="32",
            patient_gender="Male",
            appointment_id="TK-999",
            prescription_id="RX-TEST-999",
            date="2026-10-20",
            diagnosis="Seasonal Viral Fever",
            clinic_logo=dummy_1px_png,
            doctor_signature=dummy_1px_png,
            doctor_qualification="MBBS, MD Medicine",
            doctor_reg_no="REG-99112",
            chief_complaints="Fever and mild body aches",
            medicines=[
                {
                    "name": "Paracetamol",
                    "strength": "650mg",
                    "dosage": "1 tablet",
                    "frequency": "Thrice daily",
                    "duration": "3 days",
                    "instructions": "After meals",
                }
            ],
            advice="Stay well hydrated and take plenty of rest.",
        )

        clean_id, out_path = generate_prescription_pdf(data, Path(tmpdir))
        assert out_path.exists()
        assert out_path.stat().st_size > 1000


def test_super_admin_tenant_logo_create_and_update(client):
    sa_token = create_session("superadmin", role="SUPER_ADMIN", tenant_id="platform")
    sa_headers = {"Authorization": f"Bearer {sa_token}"}
    import uuid
    tid = f"tenant_{uuid.uuid4().hex[:6]}"
    logo_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    # 1. Create tenant with logo
    res_create = client.post(
        "/api/super-admin/tenants",
        headers=sa_headers,
        json={
            "id": tid,
            "name": f"Clinic {tid}",
            "logo": logo_data,
            "subscription_plan": "ENTERPRISE",
        },
    )
    assert res_create.status_code in (200, 201)
    created = res_create.json()
    assert created["logo"] == logo_data

    # 2. Update tenant with new logo
    new_logo = "https://example.com/new_logo.png"
    res_update = client.patch(
        f"/api/super-admin/tenants/{tid}",
        headers=sa_headers,
        json={
            "logo": new_logo,
        },
    )
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["logo"] == new_logo

    # Teardown test tenant
    from app.db.session import get_session_factory
    from app.db.models.clinic import Clinic
    sf = get_session_factory()
    with sf() as session:
        session.query(Clinic).filter(Clinic.id == tid).delete()
        session.commit()


def test_langgraph_online_payment_selection():
    from unittest.mock import MagicMock
    from app.graph.nodes import GraphNodes
    from app.tools.payments import PaymentTools

    payment_tools = PaymentTools(upi_id="clinic@upi")
    patient_tools = MagicMock()
    patient_tools.book_appointment.return_value = {
        "success": True,
        "token_no": "TK-ONLINE-99",
        "appointment_id": "TK-ONLINE-99",
        "amount": "500",
        "payment_status": "Pending",
        "payment_method": "Razorpay / UPI",
        "booking_status": "Confirmed",
        "doctor": "Dr. Sufian",
        "date": "2026-11-20",
        "time": "10:00",
    }
    nodes = GraphNodes(
        clinic_name="City Hospital",
        llm=MagicMock(),
        rag=MagicMock(),
        payments=payment_tools,
        patients=patient_tools,
        support_phone="6200126662",
    )

    state = {
        "user_phone": "9876543210",
        "user_name": "Vikram",
        "flow": "book",
        "step": "collect_payment_method",
        "selected_slot": "SLOT-01",
        "doctor_name": "Dr. Sufian",
        "date": "2026-11-20",
        "time": "10:00",
        "fee": "500",
        "tenant_id": "default",
    }

    # Simulate user choosing online payment
    out = nodes._complete_online(state)
    assert "reply" in out
    assert "Razorpay" in out["reply"] or "rzp.io" in out["reply"]
    assert "upi://pay?" in out["reply"]
    assert out.get("flow") == "complete"
    assert out.get("payment_method") == "Razorpay / UPI"


def test_missing_upi_qr_fails_gracefully_with_no_broken_qr(tmp_path):
    """When tenant has no UPI ID configured, offline QR generation must fail gracefully with zero broken QR images."""
    from app.tools.payments import PaymentTools
    from app.repositories.postgres_crm_repositories import PostgresPaymentRepository
    from unittest.mock import MagicMock

    # 1. PaymentTools with empty UPI ID
    tools = PaymentTools(upi_id="")
    res = tools.generate_offline_upi_qr("500", "City Clinic", "REF123", tmp_path)
    assert res["success"] is False
    assert res["error_code"] == "UPI_NOT_CONFIGURED"
    assert "not set up" in res["message"].lower()
    assert not (tmp_path / "REF123-upi.png").exists()

    # 2. PostgresPaymentRepository with empty UPI ID
    repo = PostgresPaymentRepository(MagicMock(), upi_id="")
    res2 = repo.generate_offline_upi_qr("500", "City Clinic", "REF124", tmp_path)
    assert res2["success"] is False
    assert res2["error_code"] == "UPI_NOT_CONFIGURED"
    assert "not set up" in res2["message"].lower()
    assert not (tmp_path / "REF124-upi.png").exists()

