"""Comprehensive test suite for the Doctor Prescription Management System.

Covers:
- Phase 1: Doctor Prescription Editor (draft, validation, finalize, amend, PDF, email)
- Phase 2: Admin CRM Integration (oversight, filtering, doctor metrics, patient history)
- Phase 4: Security & Cross-Doctor Isolation safeguards
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.auth import create_session
from app.services.prescription_service import PrescriptionService
from app.tools.prescription_pdf import generate_prescription_pdf
from app.tools.gmail import GmailTools
from app.main import create_app


@pytest.fixture
def temp_rx_file(tmp_path):
    return tmp_path / "prescriptions.json"


@pytest.fixture
def rx_service(temp_rx_file, tmp_path):
    return PrescriptionService(
        storage_path=temp_rx_file,
        pdf_dir=tmp_path / "pdfs",
    )


def test_prescription_draft_and_finalization(rx_service):
    """Test full draft creation, update, and finalization lifecycle."""
    draft_data = {
        "appointment_id": "TKN-101",
        "patient_id": "PAT001",
        "patient_name": "Rohan Verma",
        "patient_phone": "9876543210",
        "patient_email": "rohan@example.com",
        "patient_age": "34",
        "patient_gender": "Male",
        "date": "2026-10-02",
        "chief_complaints": "Persistent dry cough for 4 days",
        "symptoms": "Mild fever, throat irritation",
        "diagnosis": "Acute Pharyngitis",
        "vitals": {
            "bp": "120/80",
            "pulse": "74",
            "temp": "99.1",
            "weight": "72",
            "spo2": "99",
        },
        "clinical_notes": "<p>Throat erythematous, no exudate.</p>",
        "medicines": [
            {
                "name": "Amoxicillin",
                "strength": "500 mg",
                "dosage": "1 capsule",
                "frequency": "1-0-1",
                "duration": "5 days",
                "instructions": "After food",
            }
        ],
        "tests_advised": "Complete Blood Count",
        "advice": "Hydration, warm salt water gargle",
        "follow_up_date": "2026-10-07",
    }

    # 1. Create draft
    draft = rx_service.create_or_update_draft(
        data=draft_data,
        doctor_id="DOC001",
        doctor_name="Dr. Arjun Mehta",
        doctor_specialization="General Physician",
        doctor_qualification="MBBS, MD",
        doctor_reg_no="MED-87654",
        user="dr_arjun_api",
    )

    rx_id = draft["prescription_id"]
    assert rx_id.startswith("RX-")
    assert draft["status"] == "draft"
    assert draft["version"] == 1
    assert draft["doctor_qualification"] == "MBBS, MD"
    assert draft["doctor_reg_no"] == "MED-87654"
    assert draft["vitals"]["bp"] == "120/80"
    assert len(draft["medicines"]) == 1
    assert draft["medicines"][0]["strength"] == "500 mg"

    # 2. Finalize prescription
    finalized = rx_service.finalize_prescription(
        prescription_id=rx_id,
        doctor_id="DOC001",
        user="dr_arjun_api",
    )

    assert finalized["status"] == "finalized"
    assert finalized["finalized_at"] is not None

    # 3. Finalized record cannot be edited as draft
    with pytest.raises(ValueError, match="Cannot edit a finalized prescription as a draft"):
        rx_service.create_or_update_draft(
            data={"prescription_id": rx_id, "diagnosis": "Changed"},
            doctor_id="DOC001",
            doctor_name="Dr. Arjun Mehta",
            user="dr_arjun_api",
        )


def test_prescription_validation_safeguards(rx_service):
    """Test strict validation preventing premature finalization."""
    # Create draft with missing diagnosis
    draft = rx_service.create_or_update_draft(
        data={
            "appointment_id": "TKN-102",
            "patient_id": "PAT002",
            "patient_name": "Pooja Roy",
            "diagnosis": "",
            "medicines": [],
        },
        doctor_id="DOC001",
        doctor_name="Dr. Arjun",
        user="dr_arjun_api",
    )
    rx_id = draft["prescription_id"]

    # Attempt to finalize without diagnosis
    with pytest.raises(ValueError, match="Clinical Diagnosis is required"):
        rx_service.finalize_prescription(rx_id, doctor_id="DOC001")

    # Add diagnosis but no medicines
    rx_service.create_or_update_draft(
        data={"prescription_id": rx_id, "diagnosis": "Bronchitis", "medicines": []},
        doctor_id="DOC001",
        doctor_name="Dr. Arjun",
        user="dr_arjun_api",
    )

    with pytest.raises(ValueError, match="Prescription must include at least one medication"):
        rx_service.finalize_prescription(rx_id, doctor_id="DOC001")


def test_prescription_clinical_amendment(rx_service):
    """Test versioned amendment of finalized prescription."""
    draft = rx_service.create_or_update_draft(
        data={
            "appointment_id": "TKN-103",
            "patient_id": "PAT003",
            "patient_name": "Vikram Singh",
            "diagnosis": "Hypertension",
            "medicines": [
                {
                    "name": "Amlodipine",
                    "strength": "5 mg",
                    "dosage": "1 tab",
                    "frequency": "1-0-0",
                    "duration": "30 days",
                    "instructions": "Morning after breakfast",
                }
            ],
        },
        doctor_id="DOC001",
        doctor_name="Dr. Arjun",
        user="dr_arjun_api",
    )
    rx_id = draft["prescription_id"]
    rx_service.finalize_prescription(rx_id, doctor_id="DOC001")

    # Amend with dosage adjustment
    amended = rx_service.amend_prescription(
        prescription_id=rx_id,
        updates={
            "diagnosis": "Stage 2 Essential Hypertension",
            "medicines": [
                {
                    "name": "Amlodipine",
                    "strength": "10 mg",
                    "dosage": "1 tab",
                    "frequency": "1-0-0",
                    "duration": "30 days",
                    "instructions": "Morning after breakfast",
                }
            ],
            "advice": "DASH diet and daily BP log",
        },
        doctor_id="DOC001",
        user="dr_arjun_api",
        amendment_reason="Dosage escalated due to uncontrolled systolic BP",
    )

    assert amended["version"] == 2
    assert amended["status"] == "amended"
    assert amended["diagnosis"] == "Stage 2 Essential Hypertension"
    assert amended["medicines"][0]["strength"] == "10 mg"
    assert len(amended["version_history"]) == 1
    assert amended["version_history"][0]["version"] == 1
    assert amended["version_history"][0]["amendment_reason"] == "Dosage escalated due to uncontrolled systolic BP"


def test_prescription_pdf_generation_reportlab(rx_service, tmp_path):
    """Test professional PDF generation via ReportLab."""
    rx = rx_service.create_or_update_draft(
        data={
            "appointment_id": "TKN-104",
            "patient_id": "PAT004",
            "patient_name": "Meera Patel",
            "patient_age": "29",
            "patient_gender": "Female",
            "diagnosis": "Acute Bronchitis",
            "vitals": {"bp": "118/76", "pulse": "80", "temp": "98.4", "weight": "58", "spo2": "99"},
            "medicines": [
                {
                    "name": "Azithromycin",
                    "strength": "500 mg",
                    "dosage": "1 tab",
                    "frequency": "1-0-0",
                    "duration": "3 days",
                    "instructions": "1 hour before meals",
                }
            ],
            "tests_advised": "Sputum Culture",
            "advice": "Steam inhalation twice daily",
        },
        doctor_id="DOC001",
        doctor_name="Dr. Arjun Mehta",
        doctor_specialization="General Physician",
        doctor_qualification="MBBS",
        doctor_reg_no="MED-12345",
    )
    rx_id = rx["prescription_id"]
    rx_service.finalize_prescription(rx_id, doctor_id="DOC001")

    clean_id, pdf_path = rx_service.generate_pdf_for_prescription(
        prescription_id=rx_id,
        clinic_name="XYZ Clinic",
        clinic_phone="6200126662",
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_prescription_email_dispatch_and_audit(rx_service, tmp_path):
    """Test prescription email delivery and audit tracking."""
    rx = rx_service.create_or_update_draft(
        data={
            "appointment_id": "TKN-105",
            "patient_id": "PAT005",
            "patient_name": "Suresh Raina",
            "patient_email": "suresh@example.com",
            "diagnosis": "Seasonal Allergic Rhinitis",
            "medicines": [
                {
                    "name": "Levocetirizine",
                    "strength": "5 mg",
                    "dosage": "1 tab",
                    "frequency": "0-0-1",
                    "duration": "10 days",
                    "instructions": "At bedtime",
                }
            ],
        },
        doctor_id="DOC001",
        doctor_name="Dr. Arjun",
    )
    rx_id = rx["prescription_id"]
    rx_service.finalize_prescription(rx_id, doctor_id="DOC001")
    _, pdf_path = rx_service.generate_pdf_for_prescription(rx_id)

    # Mock email sender
    mock_sender = MagicMock()
    gmail_tools = GmailTools(sender=mock_sender)

    # 1. Send to patient
    res_patient = gmail_tools.send_prescription_email(
        recipient="suresh@example.com",
        prescription_data=rx_service.get_prescription(rx_id),
        clinic_name="XYZ Clinic",
        support_phone="6200126662",
        pdf_path=str(pdf_path),
    )
    assert res_patient["email_sent"] is True
    assert mock_sender.called

    # Record delivery
    rx_service.record_email_delivery(rx_id, success=True, recipient="suresh@example.com")
    updated = rx_service.get_prescription(rx_id)
    assert updated["email_delivery"]["sent"] is True
    assert updated["email_delivery"]["recipient"] == "suresh@example.com"

    # 2. Test invalid email format handling
    res_invalid = gmail_tools.send_prescription_email(
        recipient="not-an-email",
        prescription_data=updated,
        clinic_name="XYZ Clinic",
        support_phone="6200126662",
        pdf_path=str(pdf_path),
    )
    assert res_invalid["email_sent"] is False
    assert res_invalid["skipped"] is True


def test_doctor_cross_isolation_safeguards(rx_service):
    """Test strict multi-tenant physician isolation rules."""
    # Doctor 1 authors prescription
    rx1 = rx_service.create_or_update_draft(
        data={
            "appointment_id": "TKN-201",
            "patient_id": "PAT010",
            "patient_name": "Anita Das",
            "diagnosis": "Migraine",
            "medicines": [{"name": "Sumatriptan", "strength": "50mg", "dosage": "1 tab", "frequency": "SOS", "duration": "3 days", "instructions": "At onset"}],
        },
        doctor_id="DOC001",
        doctor_name="Dr. Arjun",
        user="dr_arjun_api",
    )
    rx1_id = rx1["prescription_id"]

    # Doctor 2 attempts to modify Doctor 1's draft
    with pytest.raises(PermissionError, match="cannot modify another physician's prescription"):
        rx_service.create_or_update_draft(
            data={"prescription_id": rx1_id, "diagnosis": "Hacked"},
            doctor_id="DOC003",
            doctor_name="Dr. Sufian",
            user="dr_sufian",
        )

    # Doctor 2 attempts to finalize Doctor 1's prescription
    with pytest.raises(PermissionError, match="cannot finalize another physician's prescription"):
        rx_service.finalize_prescription(rx1_id, doctor_id="DOC003")

    # Doctor 1 finalizes
    rx_service.finalize_prescription(rx1_id, doctor_id="DOC001")

    # Doctor 2 attempts to amend Doctor 1's prescription
    with pytest.raises(PermissionError, match="cannot amend another physician's prescription"):
        rx_service.amend_prescription(
            prescription_id=rx1_id,
            updates={"diagnosis": "Hacked amendment"},
            doctor_id="DOC003",
            amendment_reason="Illegitimate change",
        )


def test_api_endpoints_doctor_and_admin_flows():
    """Integration test of HTTP endpoints for doctor portal and admin oversight."""
    app = create_app()
    client = TestClient(app)

    # Generate auth tokens
    admin_token = create_session(username="admin", role="admin")
    doc_arjun_token = create_session(
        username="dr_arjun_api",
        role="doctor",
        doctor_id="DOC001",
        doctor_name="Dr. Arjun Mehta",
    )
    doc_sufian_token = create_session(
        username="dr_sufian",
        role="doctor",
        doctor_id="DOC003",
        doctor_name="Dr. Sufian",
    )

    arjun_headers = {"Authorization": f"Bearer {doc_arjun_token}"}
    sufian_headers = {"Authorization": f"Bearer {doc_sufian_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Doctor Arjun creates draft via API
    resp_draft = client.post(
        "/api/doctor/prescriptions",
        headers=arjun_headers,
        json={
            "appointment_id": "TKN-301",
            "patient_id": "PAT020",
            "patient_name": "Kavita Rao",
            "patient_phone": "9988776655",
            "patient_email": "kavita@example.com",
            "patient_age": "45",
            "patient_gender": "Female",
            "date": "2026-10-02",
            "chief_complaints": "Joint pain in knees",
            "diagnosis": "Osteoarthritis Grade 1",
            "vitals": {"bp": "130/84", "pulse": "76", "temp": "98.6", "weight": "65", "spo2": "98"},
            "medicines": [
                {
                    "name": "Paracetamol",
                    "strength": "650 mg",
                    "dosage": "1 tab",
                    "frequency": "1-0-1",
                    "duration": "5 days",
                    "instructions": "After meals",
                }
            ],
            "advice": "Gentle physiotherapy exercises",
        },
    )
    assert resp_draft.status_code == 200, resp_draft.text
    rx_id = resp_draft.json()["prescription_id"]

    # 2. Doctor Sufian attempts to read Arjun's prescription -> 403 Forbidden
    resp_forbidden = client.get(f"/api/doctor/prescriptions/{rx_id}", headers=sufian_headers)
    assert resp_forbidden.status_code == 403

    # 3. Doctor Arjun finalizes prescription
    resp_fin = client.post(f"/api/doctor/prescriptions/{rx_id}/finalize", headers=arjun_headers)
    assert resp_fin.status_code == 200
    assert resp_fin.json()["status"] == "finalized"

    # 4. Doctor Arjun downloads PDF
    resp_pdf = client.get(f"/api/doctor/prescriptions/{rx_id}/pdf", headers=arjun_headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"

    # 5. Admin oversight: Admin can list all prescriptions
    resp_admin_list = client.get("/api/admin/prescriptions", headers=admin_headers)
    assert resp_admin_list.status_code == 200
    rxs = resp_admin_list.json()
    assert any(r.get("prescription_id") == rx_id for r in rxs)

    # 6. Admin can fetch single prescription
    resp_admin_get = client.get(f"/api/admin/prescriptions/{rx_id}", headers=admin_headers)
    assert resp_admin_get.status_code == 200
    assert resp_admin_get.json()["diagnosis"] == "Osteoarthritis Grade 1"

    # 7. Admin downloads PDF
    resp_admin_pdf = client.get(f"/api/admin/prescriptions/{rx_id}/pdf", headers=admin_headers)
    assert resp_admin_pdf.status_code == 200
    assert resp_admin_pdf.headers["content-type"] == "application/pdf"
