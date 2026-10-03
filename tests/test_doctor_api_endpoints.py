"""FastAPI HTTP Integration tests for Doctor Portal and Admin endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.core.auth import clear_failed_login, create_session
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CRM_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CRM_ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("ALLOW_DEMO_PASSWORD", "true")
    clear_failed_login("admin")
    clear_failed_login("dr_test")
    app = create_app()
    return TestClient(app)


def test_admin_and_doctor_login_endpoints(client):
    # 1. Admin login succeeds
    res_admin = client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_admin.status_code == 200
    admin_data = res_admin.json()
    assert admin_data["role"] == "admin"
    admin_token = admin_data["token"]

    # 2. Get a valid Doctor ID from doctor directory
    res_docs = client.get("/api/admin/doctors", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_docs.status_code == 200
    doctors_list = res_docs.json()
    valid_doc_id = doctors_list[0]["Doctor ID"] if doctors_list else "DOC001"

    # 3. Admin creates a doctor account
    res_create_doc = client.post(
        "/api/admin/doctor-accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "dr_arjun_api",
            "password": "1234",
            "doctor_id": valid_doc_id,
            "email": "dr.arjun@test.com",
        },
    )
    # Status can be 201 or 400 (if already created in prior run)
    assert res_create_doc.status_code in (201, 400)

    # 4. Doctor login succeeds
    res_doc = client.post("/api/admin/auth/login", json={"username": "dr_arjun_api", "password": "1234"})
    assert res_doc.status_code == 200
    doc_data = res_doc.json()
    assert doc_data["role"] == "doctor"
    assert doc_data["doctor_id"] == valid_doc_id
    doc_token = doc_data["token"]

    # 4. Doctor calls /api/doctor/profile
    res_prof = client.get("/api/doctor/profile", headers={"Authorization": f"Bearer {doc_token}"})
    assert res_prof.status_code == 200

    # 5. Doctor tries to call admin-only endpoint -> 403 Forbidden!
    res_forbidden = client.get("/api/admin/doctor-accounts", headers={"Authorization": f"Bearer {doc_token}"})
    assert res_forbidden.status_code == 403

    # 6. Admin tries to call doctor-only endpoint -> 403 Forbidden!
    res_admin_forbidden = client.get("/api/doctor/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_forbidden.status_code == 403


def test_doctor_prescription_lifecycle_api(client):
    # Setup doctor session
    token = create_session(
        username="dr_arjun_api",
        role="doctor",
        doctor_id="D1",
        doctor_name="Dr. Arjun Mehta",
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Save draft
    draft_payload = {
        "appointment_id": "TKN-API-001",
        "patient_id": "P-API-101",
        "patient_name": "Test Patient",
        "patient_email": "patient@example.com",
        "diagnosis": "Viral Fever",
        "symptoms": "High temperature",
        "medicines": [
            {
                "name": "Paracetamol",
                "dosage": "500mg",
                "frequency": "1-0-1",
                "duration": "3 days",
                "instructions": "After food",
            }
        ],
    }
    res_draft = client.post("/api/doctor/prescriptions", headers=headers, json=draft_payload)
    assert res_draft.status_code == 200
    rx_data = res_draft.json()
    rx_id = rx_data["prescription_id"]
    assert rx_data["status"] == "draft"

    # 2. Finalize prescription
    res_fin = client.post(f"/api/doctor/prescriptions/{rx_id}/finalize", headers=headers)
    assert res_fin.status_code == 200
    assert res_fin.json()["status"] == "finalized"

    # 3. Download PDF
    res_pdf = client.get(f"/api/doctor/prescriptions/{rx_id}/pdf", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"

    # 4. Amend prescription
    amend_payload = {
        "amendment_reason": "Corrected duration",
        "medicines": [
            {
                "name": "Paracetamol",
                "dosage": "500mg",
                "frequency": "1-0-1",
                "duration": "5 days",
                "instructions": "After food with warm water",
            }
        ],
    }
    res_amend = client.post(f"/api/doctor/prescriptions/{rx_id}/amend", headers=headers, json=amend_payload)
    assert res_amend.status_code == 200
    amended = res_amend.json()
    assert amended["version"] == 2
    assert len(amended["version_history"]) == 1
