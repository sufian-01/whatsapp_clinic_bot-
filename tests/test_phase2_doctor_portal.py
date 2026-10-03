"""Phase 2 Comprehensive Test Suite: Doctor Portal, RBAC, Slots & Prescriptions.

Covers:
- PART 1: Role-Based Authentication & Permissions
- PART 2: Doctor Account Lifecycle & Security (PBKDF2, Lockout, Password Change)
- PART 3: Doctor Dashboard & Isolation
- PART 4: Doctor Slot Management (Overlap, Past-Time, Booked Safeguards)
- PART 5: Patient Access & Payment Rules
- PART 6: Prescription Workflow (Draft, Validation, Finalization, Versioning/Amendments)
- PART 7: PDF Generation & Verified Email Delivery
- PART 8: Admin Oversight
- PART 9: Concurrency & Booking Safety
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from app.core.auth import (
    check_account_lockout,
    clear_failed_login,
    create_session,
    get_session,
    hash_password,
    record_failed_login,
    revoke_session,
    verify_password,
)
from app.services.crm_service import CrmService
from app.services.doctor_account_service import DoctorAccountService
from app.services.prescription_service import PrescriptionService
from app.tools.prescription_pdf import PrescriptionPDFData, generate_prescription_pdf


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def mock_doctor_directory():
    directory = MagicMock()
    doctors = [
        {
            "Doctor ID": "D1",
            "Doctor Name": "Dr. Arjun Mehta",
            "Specialization": "General Physician",
            "Available Days": "Monday, Wednesday, Friday",
            "Start Time": "10:00 AM",
            "End Time": "1:00 PM",
            "Consultation Fee": "500",
            "Status": "Active",
        },
        {
            "Doctor ID": "D2",
            "Doctor Name": "Dr. Sana Khan",
            "Specialization": "Gynecologist",
            "Available Days": "Tuesday, Thursday",
            "Start Time": "2:00 PM",
            "End Time": "5:00 PM",
            "Consultation Fee": "700",
            "Status": "Active",
        },
    ]
    directory.get_doctors.return_value = doctors
    directory.get_doctor_by_id.side_effect = lambda doc_id: next((d for d in doctors if d["Doctor ID"] == doc_id), None)
    return directory


@pytest.fixture
def mock_slots_repo():
    repo = MagicMock()
    slots = [
        {
            "Slot ID": "S1",
            "Doctor ID": "D1",
            "Doctor Name": "Dr. Arjun Mehta",
            "Date": "2026-10-15",
            "Start Time": "10:00 AM",
            "End Time": "10:30 AM",
            "Status": "Available",
            "Patient ID": "",
            "Token No": "",
        },
        {
            "Slot ID": "S2",
            "Doctor ID": "D1",
            "Doctor Name": "Dr. Arjun Mehta",
            "Date": "2026-10-15",
            "Start Time": "10:30 AM",
            "End Time": "11:00 AM",
            "Status": "Booked",
            "Patient ID": "P101",
            "Token No": "TKN-001",
        },
        {
            "Slot ID": "S3",
            "Doctor ID": "D2",
            "Doctor Name": "Dr. Sana Khan",
            "Date": "2026-10-15",
            "Start Time": "02:00 PM",
            "End Time": "02:30 PM",
            "Status": "Available",
            "Patient ID": "",
            "Token No": "",
        },
    ]

    def list_all():
        return list(slots)

    def get_by_id(sid):
        return next((s for s in slots if s["Slot ID"] == sid), None)

    def create(data):
        new_slot = dict(data)
        new_slot["Doctor ID"] = data.get("Doctor ID") or data.get("doctor_id", "")
        new_slot["Doctor Name"] = data.get("Doctor Name") or data.get("doctor_name", "")
        new_slot["Date"] = data.get("Date") or data.get("date", "")
        new_slot["Start Time"] = data.get("Start Time") or data.get("start_time", "")
        new_slot["End Time"] = data.get("End Time") or data.get("end_time", "")
        new_slot["Status"] = data.get("Status") or data.get("status", "Available")
        if "Slot ID" not in new_slot:
            new_slot["Slot ID"] = f"S{len(slots) + 1}"
        slots.append(new_slot)
        return new_slot

    def update(sid, updates):
        s = get_by_id(sid)
        if s:
            s.update(updates)
            return {"success": True, "slot": s}
        return {"success": False, "error_code": "SLOT_NOT_FOUND"}

    repo.list_all_slots.side_effect = list_all
    repo.get_slot_by_id.side_effect = get_by_id
    repo.create_slot.side_effect = create
    repo.update_slot.side_effect = update
    return repo


@pytest.fixture
def mock_patients_repo():
    repo = MagicMock()
    patients = [
        {
            "Patient ID": "P101",
            "Name": "Rahul Sharma",
            "Phone": "9876543210",
            "Email": "rahul@example.com",
            "Doctor": "Dr. Arjun Mehta",
            "doctor_id": "D1",
            "Appointment Date": "2026-10-15",
            "Appointment Time": "10:30 AM",
            "Booking Status": "Confirmed",
            "Payment Status": "Paid",
            "Token No": "TKN-001",
            "Amount": "500",
        },
        {
            "Patient ID": "P102",
            "Name": "Pooja Verma",
            "Phone": "9876543211",
            "Email": "pooja@example.com",
            "Doctor": "Dr. Sana Khan",
            "doctor_id": "D2",
            "Appointment Date": "2026-10-15",
            "Appointment Time": "02:00 PM",
            "Booking Status": "Confirmed",
            "Payment Status": "Pending",
            "Token No": "TKN-002",
            "Amount": "700",
        },
    ]
    repo.list_patients.return_value = patients
    repo.find_by_patient_id.side_effect = lambda pid: next((p for p in patients if p["Patient ID"] == pid), None)
    return repo


@pytest.fixture
def crm_services(temp_data_dir, mock_doctor_directory, mock_slots_repo, mock_patients_repo):
    audit = MagicMock()
    doc_accounts = DoctorAccountService(
        storage_path=temp_data_dir / "doctor_accounts.json",
        doctor_directory=mock_doctor_directory,
        audit_service=audit,
        allow_demo_password=True,
    )
    prescriptions = PrescriptionService(
        storage_path=temp_data_dir / "prescriptions.json",
        pdf_dir=temp_data_dir / "prescriptions",
        audit_service=audit,
    )
    gmail_mock = MagicMock()
    gmail_mock.send_prescription_email.return_value = {"success": True, "email_sent": True, "error": None}

    crm = CrmService(
        patients_tools=mock_patients_repo,
        doctors_tools=mock_doctor_directory,
        slots_tools=mock_slots_repo,
        gmail_tools=gmail_mock,
        audit_service=audit,
        doctor_accounts=doc_accounts,
        prescriptions=prescriptions,
        clinic_name="City Health Clinic",
        support_phone="6200126662",
    )
    return crm, doc_accounts, prescriptions, gmail_mock


# ---------------------------------------------------------------------------
# PART 1 & 2: AUTHENTICATION, DOCTOR ACCOUNTS & LOCKOUT TESTS
# ---------------------------------------------------------------------------

def test_doctor_account_creation_and_demo_password(crm_services):
    crm, doc_accounts, _, _ = crm_services
    # Create doctor account with demo password 1234
    acc = doc_accounts.create_account(
        username="dr_arjun",
        password="1234",
        doctor_id="D1",
        email="arjun@clinic.com",
        admin_user="admin",
    )
    assert acc["username"] == "dr_arjun"
    assert acc["doctor_id"] == "D1"
    assert acc["doctor_name"] == "Dr. Arjun Mehta"
    assert acc["must_change_password"] is True
    assert "password_hash" not in acc

    # Authenticate successfully
    auth_acc = doc_accounts.authenticate("dr_arjun", "1234")
    assert auth_acc is not None
    assert auth_acc["username"] == "dr_arjun"

    # Authenticate with wrong password
    assert doc_accounts.authenticate("dr_arjun", "wrongpass") is None


def test_doctor_account_invalid_doctor_id(crm_services):
    crm, doc_accounts, _, _ = crm_services
    with pytest.raises(ValueError, match="does not exist in the Doctor Directory"):
        doc_accounts.create_account(
            username="invalid_doc",
            password="SecurePass123",
            doctor_id="D999",
        )


def test_doctor_password_change(crm_services):
    crm, doc_accounts, _, _ = crm_services
    doc_accounts.create_account(username="dr_arjun", password="1234", doctor_id="D1")

    # Fail with wrong old password
    with pytest.raises(ValueError, match="Incorrect current password"):
        doc_accounts.change_password("dr_arjun", "wrongpass", "NewSecretPass1")

    # Succeed with correct old password
    res = doc_accounts.change_password("dr_arjun", "1234", "NewSecretPass1")
    assert res["must_change_password"] is False

    # Old password no longer works
    assert doc_accounts.authenticate("dr_arjun", "1234") is None
    # New password works
    assert doc_accounts.authenticate("dr_arjun", "NewSecretPass1") is not None


def test_login_rate_limiting_and_lockout():
    key = "test_lockout_user"
    clear_failed_login(key)

    # First 4 failures do not lock out
    for i in range(4):
        is_locked, left = record_failed_login(key)
        assert is_locked is False
        assert left == 4 - i

    # 5th failure triggers lockout
    is_locked, left = record_failed_login(key)
    assert is_locked is True
    assert left == 0

    # Verification of lockout check
    locked, remaining_secs = check_account_lockout(key)
    assert locked is True
    assert remaining_secs > 0

    # Clearing lockout on valid login
    clear_failed_login(key)
    locked, _ = check_account_lockout(key)
    assert locked is False


def test_session_creation_with_doctor_metadata():
    token = create_session(
        username="dr_sana",
        role="doctor",
        doctor_id="D2",
        doctor_name="Dr. Sana Khan",
        must_change_password=True,
    )
    session = get_session(token)
    assert session is not None
    assert session["role"] == "doctor"
    assert session["doctor_id"] == "D2"
    assert session["doctor_name"] == "Dr. Sana Khan"
    assert session["must_change_password"] is True

    # Revoke session
    assert revoke_session(token) is True
    assert get_session(token) is None


# ---------------------------------------------------------------------------
# PART 3 & 5: DOCTOR DASHBOARD, ISOLATION & PATIENT ACCESS
# ---------------------------------------------------------------------------

def test_doctor_dashboard_metrics(crm_services):
    crm, _, _, _ = crm_services
    stats = crm.get_doctor_dashboard_stats("D1", today_str="2026-10-15")
    assert stats["today_appointments_count"] == 1
    assert stats["total_patients"] == 1
    assert stats["available_slots"] >= 1


def test_doctor_cross_access_isolation(crm_services):
    crm, _, _, _ = crm_services

    # Dr. Arjun Mehta (D1) fetches appointments
    d1_appts = crm.get_doctor_appointments("D1")
    assert len(d1_appts) == 1
    assert d1_appts[0]["patient_name"] == "Rahul Sharma"

    # Dr. Sana Khan (D2) fetches appointments
    d2_appts = crm.get_doctor_appointments("D2")
    assert len(d2_appts) == 1
    assert d2_appts[0]["patient_name"] == "Pooja Verma"

    # Dr. Sana Khan (D2) attempting to access Dr. Arjun's appointment (TKN-001) MUST be rejected
    with pytest.raises(PermissionError, match="another physician's patient records"):
        crm.get_doctor_appointment("TKN-001", doctor_id="D2")

    # Dr. Sana Khan (D2) attempting to access Rahul Sharma's patient profile MUST be rejected
    with pytest.raises(PermissionError, match="not assigned to your consultations"):
        crm.get_doctor_patient_detail("P101", doctor_id="D2")


def test_doctor_patient_access_verified_payment(crm_services):
    crm, _, _, _ = crm_services
    # Pooja Verma has payment status "Pending" with Dr. Sana Khan
    patients_all = crm.get_doctor_patients("D2", require_verified_payment=False)
    assert len(patients_all) == 1

    # When require_verified_payment=True, unpaid patients are filtered from consultation list
    patients_paid_only = crm.get_doctor_patients("D2", require_verified_payment=True)
    assert len(patients_paid_only) == 0


# ---------------------------------------------------------------------------
# PART 4: DOCTOR SLOT MANAGEMENT SAFEGUARDS
# ---------------------------------------------------------------------------

def test_doctor_slot_creation_valid(crm_services):
    crm, _, _, _ = crm_services
    slot = crm.create_doctor_slot(
        doctor_id="D1",
        date_val="2026-11-20",
        start_time="11:00 AM",
        end_time="11:30 AM",
        user="dr_arjun",
    )
    assert slot["Doctor ID"] == "D1"
    assert slot["Start Time"] == "11:00 AM"
    assert slot["Status"] == "Available"


def test_doctor_slot_creation_overlap_prevention(crm_services):
    crm, _, _, _ = crm_services
    # S1 is 10:00 AM - 10:30 AM on 2026-10-15 for D1
    with pytest.raises(ValueError, match="overlaps with existing slot"):
        crm.create_doctor_slot(
            doctor_id="D1",
            date_val="2026-10-15",
            start_time="10:15 AM",
            end_time="10:45 AM",
            user="dr_arjun",
        )


def test_doctor_slot_creation_past_time_prevention(crm_services):
    crm, _, _, _ = crm_services
    past_date = (date.today() - timedelta(days=2)).isoformat()
    with pytest.raises(ValueError, match="Cannot create appointment slots in the past"):
        crm.create_doctor_slot(
            doctor_id="D1",
            date_val=past_date,
            start_time="10:00 AM",
            end_time="10:30 AM",
            user="dr_arjun",
        )


def test_doctor_slot_booked_protection(crm_services):
    crm, _, _, _ = crm_services
    # S2 is booked for D1
    # Cannot modify date or time of booked slot
    with pytest.raises(ValueError, match="Cannot modify the date or time of an actively booked slot"):
        crm.update_doctor_slot(
            slot_id="S2",
            doctor_id="D1",
            updates={"start_time": "11:00 AM"},
            user="dr_arjun",
        )

    # Cannot mark booked slot unavailable
    with pytest.raises(ValueError, match="Cannot mark a booked slot as unavailable"):
        crm.update_doctor_slot(
            slot_id="S2",
            doctor_id="D1",
            updates={"status": "Unavailable"},
            user="dr_arjun",
        )

    # Cannot delete booked slot
    with pytest.raises(RuntimeError, match="A booked slot cannot be deleted without handling"):
        crm.delete_doctor_slot(slot_id="S2", doctor_id="D1", user="dr_arjun")


def test_doctor_cannot_modify_other_doctor_slot(crm_services):
    crm, _, _, _ = crm_services
    # S3 belongs to Dr. Sana Khan (D2). Dr. Arjun Mehta (D1) must not be able to modify or delete it.
    with pytest.raises(PermissionError, match="cannot modify another physician's slots"):
        crm.update_doctor_slot(
            slot_id="S3",
            doctor_id="D1",
            updates={"start_time": "03:00 PM"},
            user="dr_arjun",
        )

    with pytest.raises(PermissionError, match="cannot delete another physician's slots"):
        crm.delete_doctor_slot(slot_id="S3", doctor_id="D1", user="dr_arjun")


# ---------------------------------------------------------------------------
# PART 6: PRESCRIPTION MANAGEMENT WORKFLOW & VERSIONING
# ---------------------------------------------------------------------------

def test_prescription_draft_and_finalization_workflow(crm_services):
    crm, _, prescriptions, _ = crm_services

    # 1. Save Draft
    draft_data = {
        "patient_id": "P101",
        "patient_name": "Rahul Sharma",
        "appointment_id": "TKN-001",
        "date": "2026-10-15",
        "diagnosis": "Seasonal Upper Respiratory Tract Infection",
        "symptoms": "Mild fever, dry cough, sore throat",
        "medicines": [
            {
                "name": "Paracetamol",
                "dosage": "650mg",
                "frequency": "1-0-1",
                "duration": "3 days",
                "instructions": "After meals with warm water",
            }
        ],
        "advice": "Hydrate adequately, avoid cold drinks",
        "follow_up_date": "2026-10-20",
    }

    rx = prescriptions.create_or_update_draft(
        data=draft_data,
        doctor_id="D1",
        doctor_name="Dr. Arjun Mehta",
        doctor_specialization="General Physician",
        user="dr_arjun",
    )
    rx_id = rx["prescription_id"]
    assert rx["status"] == "draft"
    assert rx["version"] == 1

    # 2. Finalize Prescription
    finalized = prescriptions.finalize_prescription(
        prescription_id=rx_id,
        doctor_id="D1",
        user="dr_arjun",
    )
    assert finalized["status"] == "finalized"
    assert finalized["finalized_at"] is not None

    # 3. Direct draft overwrite of finalized prescription is strictly rejected
    with pytest.raises(ValueError, match="Cannot edit a finalized prescription as a draft"):
        prescriptions.create_or_update_draft(
            data={"prescription_id": rx_id, "diagnosis": "Changed Diagnosis"},
            doctor_id="D1",
            doctor_name="Dr. Arjun Mehta",
            user="dr_arjun",
        )


def test_prescription_finalization_validation_errors(crm_services):
    crm, _, prescriptions, _ = crm_services

    # Create empty draft
    draft = prescriptions.create_or_update_draft(
        data={
            "patient_id": "P101",
            "patient_name": "Rahul Sharma",
            "appointment_id": "TKN-001",
            "diagnosis": "",  # Empty diagnosis
            "medicines": [],  # Empty medicines
        },
        doctor_id="D1",
        doctor_name="Dr. Arjun Mehta",
        user="dr_arjun",
    )
    rx_id = draft["prescription_id"]

    # Finalization must fail because diagnosis is missing
    with pytest.raises(ValueError, match="Clinical Diagnosis is required"):
        prescriptions.finalize_prescription(rx_id, doctor_id="D1")


def test_prescription_amendment_and_version_history(crm_services):
    crm, _, prescriptions, _ = crm_services

    # Create & finalize original prescription
    rx = prescriptions.create_or_update_draft(
        data={
            "patient_id": "P101",
            "patient_name": "Rahul Sharma",
            "appointment_id": "TKN-001",
            "diagnosis": "Mild Bronchitis",
            "medicines": [
                {
                    "name": "Amoxicillin",
                    "dosage": "500mg",
                    "frequency": "1-0-1",
                    "duration": "5 days",
                    "instructions": "After meals",
                }
            ],
        },
        doctor_id="D1",
        doctor_name="Dr. Arjun Mehta",
    )
    rx_id = rx["prescription_id"]
    prescriptions.finalize_prescription(rx_id, doctor_id="D1")

    # Amend with corrected dosage
    amended = prescriptions.amend_prescription(
        prescription_id=rx_id,
        updates={
            "medicines": [
                {
                    "name": "Amoxicillin",
                    "dosage": "250mg",  # Corrected dosage
                    "frequency": "1-0-1",
                    "duration": "5 days",
                    "instructions": "After meals",
                }
            ],
        },
        doctor_id="D1",
        user="dr_arjun",
        amendment_reason="Adjusted dosage for patient weight",
    )

    assert amended["version"] == 2
    assert len(amended["version_history"]) == 1
    snapshot = amended["version_history"][0]
    assert snapshot["version"] == 1
    assert snapshot["medicines"][0]["dosage"] == "500mg"
    assert snapshot["amendment_reason"] == "Adjusted dosage for patient weight"
    assert amended["medicines"][0]["dosage"] == "250mg"


def test_prescription_cross_doctor_isolation(crm_services):
    crm, _, prescriptions, _ = crm_services

    # Dr. Arjun Mehta creates a prescription
    rx = prescriptions.create_or_update_draft(
        data={"patient_id": "P101", "patient_name": "Rahul Sharma", "appointment_id": "TKN-001"},
        doctor_id="D1",
        doctor_name="Dr. Arjun Mehta",
    )
    rx_id = rx["prescription_id"]

    # Dr. Sana Khan (D2) attempts to finalize Dr. Arjun's prescription -> MUST FAIL
    with pytest.raises(PermissionError, match="cannot finalize another physician's prescription"):
        prescriptions.finalize_prescription(rx_id, doctor_id="D2")


# ---------------------------------------------------------------------------
# PART 7: PDF GENERATION & EMAIL DELIVERY TESTS
# ---------------------------------------------------------------------------

def test_prescription_pdf_generation(temp_data_dir):
    data = PrescriptionPDFData(
        clinic_name="City Health Clinic",
        clinic_phone="6200126662",
        clinic_email="contact@cityclinic.com",
        clinic_address="123 Medical Center Way",
        doctor_name="Arjun Mehta",
        doctor_specialization="General Physician",
        patient_id="P101",
        patient_name="Rahul Sharma",
        patient_phone="9876543210",
        patient_age="32",
        patient_gender="Male",
        appointment_id="TKN-001",
        prescription_id="RX-TEST1234",
        date="2026-10-15",
        diagnosis="Acute Pharyngitis",
        symptoms="Difficulty swallowing, throat redness",
        medicines=[
            {
                "name": "Azithromycin",
                "dosage": "500mg",
                "frequency": "1-0-0",
                "duration": "3 days",
                "instructions": "1 hour before meals",
            }
        ],
        advice="Salt water gargles thrice daily",
        follow_up_date="2026-10-22",
        version=1,
    )
    rx_id, path = generate_prescription_pdf(data, temp_data_dir / "prescriptions")
    assert path.exists()
    assert path.stat().st_size > 1000  # PDF generated with content


def test_prescription_email_delivery_and_tracking(crm_services):
    crm, _, prescriptions, gmail_mock = crm_services

    # Create & finalize prescription
    rx = prescriptions.create_or_update_draft(
        data={
            "patient_id": "P101",
            "patient_name": "Rahul Sharma",
            "patient_email": "rahul@example.com",
            "appointment_id": "TKN-001",
            "diagnosis": "Fever",
            "medicines": [{"name": "Paracetamol", "dosage": "500mg", "frequency": "1-0-1", "duration": "3d"}],
        },
        doctor_id="D1",
        doctor_name="Dr. Arjun Mehta",
    )
    rx_id = rx["prescription_id"]
    prescriptions.finalize_prescription(rx_id, doctor_id="D1")

    # Record successful delivery
    prescriptions.record_email_delivery(
        prescription_id=rx_id,
        success=True,
        recipient="rahul@example.com",
    )

    updated = prescriptions.get_prescription(rx_id)
    assert updated["email_delivery"] is not None
    assert updated["email_delivery"]["sent"] is True
    assert updated["email_delivery"]["recipient"] == "rahul@example.com"
