"""Unit and integration tests for performance optimizations.

Tests:
1. In-memory TTL caching and invalidation for DoctorDirectory.
2. In-memory TTL caching and invalidation for PatientRepository.
3. In-memory TTL caching, atomic locking, and live consistency for SlotRepository.
4. O(1) single-pass batching for CrmService.list_doctors() preventing N+1 queries.
5. FastAPI performance logging middleware and X-Process-Time response header.
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import pytest

from app.services.crm_service import CrmService
from app.tools.doctors import DoctorDirectory
from app.tools.patients import PatientRepository
from app.tools.slots import SlotRepository


# ---------------------------------------------------------------------------
# 1. DoctorDirectory Caching & Invalidation
# ---------------------------------------------------------------------------

def test_doctor_directory_caching_and_invalidation():
    mock_reader = MagicMock()
    mock_reader.return_value = [
        ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
        ["DOC001", "Dr. Sarah Khan", "Cardiology", "Mon, Wed", "09:00", "13:00", "500", "Active"],
        ["DOC002", "Dr. Sufian Ali", "General Physician", "Mon-Fri", "10:00", "16:00", "400", "Active"],
    ]
    mock_appender = MagicMock()
    mock_updater = MagicMock()

    doc_dir = DoctorDirectory(
        read_rows=mock_reader,
        append_row=mock_appender,
        update_cells=mock_updater,
        sheet_range="doctor!A1:Z1000",
        cache_ttl_seconds=60.0,
    )

    # First read -> triggers mock_reader
    doctors_1 = doc_dir.get_doctors()
    assert len(doctors_1) == 2
    assert mock_reader.call_count == 1

    # Second read within TTL -> uses cache, mock_reader NOT called again
    doctors_2 = doc_dir.get_doctors()
    assert len(doctors_2) == 2
    assert mock_reader.call_count == 1

    # Invalidate cache -> next read triggers mock_reader
    doc_dir.invalidate_cache()
    doctors_3 = doc_dir.get_doctors()
    assert len(doctors_3) == 2
    assert mock_reader.call_count == 2

    # Status change -> auto-invalidates
    doc_dir.set_doctor_status("DOC001", "Inactive")
    assert mock_updater.call_count == 1
    # Next get_doctors should re-fetch
    doc_dir.get_doctors()
    assert mock_reader.call_count == 4


# ---------------------------------------------------------------------------
# 2. PatientRepository Caching & Invalidation
# ---------------------------------------------------------------------------

def test_patient_repository_caching_and_invalidation():
    rows = [
        ["Patient ID", "Name", "Email", "Phone", "Age", "Gender", "Doctor", "Appointment Date", "Appointment Time", "Status", "Token No", "Amount", "Payment Method", "Payment Status", "Booking Status", "Created At"],
        ["PAT-101", "John Doe", "john@example.com", "9876543210", "30", "Male", "Dr. Khan", "2026-10-05", "10:00 AM", "Confirmed", "TKN-0001", "500", "Cash", "Pending", "Confirmed", "2026-10-01T10:00:00Z"],
    ]
    read_counter = [0]

    def read_rows():
        read_counter[0] += 1
        return [list(r) for r in rows]

    mock_appender = MagicMock()
    mock_updater = MagicMock()

    repo = PatientRepository(
        read_rows=read_rows,
        append_row=mock_appender,
        update_cells=mock_updater,
        sheet_range="patients!A1:Z1000",
        cache_ttl_seconds=20.0,
    )

    # Read 1 -> calls read_rows
    records_1 = repo.list_records()
    assert len(records_1) == 1
    assert read_counter[0] == 1

    # Read 2 within TTL -> cached
    records_2 = repo.list_records()
    assert len(records_2) == 1
    assert read_counter[0] == 1

    # update_payment_status -> force-refreshes to locate row and invalidates cache
    repo.update_payment_status("PAT-101", "Paid")
    assert mock_updater.call_count == 1
    assert read_counter[0] == 2

    # Read after mutation -> re-fetches from sheet
    records_3 = repo.list_records()
    assert read_counter[0] == 3


# ---------------------------------------------------------------------------
# 3. SlotRepository Caching & Atomic Booking Consistency
# ---------------------------------------------------------------------------

def test_slot_repository_caching_and_atomic_booking():
    rows = [
        ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
        ["S1", "DOC001", "Dr. Sarah Khan", "2026-10-10", "10:00", "10:30", "Available", "", "", ""],
    ]
    read_counter = [0]

    def read_rows():
        read_counter[0] += 1
        return [list(r) for r in rows]

    def update_cells(range_name, values):
        row_num = int(range_name.split("A", 1)[1].split(":", 1)[0])
        rows[row_num - 1] = list(values)

    repo = SlotRepository(
        read_rows=read_rows,
        update_cells=update_cells,
        sheet_range="slots!A1:Z1000",
        cache_ttl_seconds=20.0,
    )

    # list_all_slots uses cache
    slots_1 = repo.list_all_slots()
    assert len(slots_1) == 1
    assert read_counter[0] == 1

    # Call 2 -> cached
    slots_2 = repo.list_all_slots()
    assert len(slots_2) == 1
    assert read_counter[0] == 1

    # book_slot MUST bypass cache and do a fresh live read for atomic check
    ok = repo.book_slot("S1", "PAT-101", "TKN-0001")
    assert ok is True
    # Live state was atomically updated
    assert rows[1][6] == "Booked"
    # Live read happened during check & verification
    assert read_counter[0] >= 3

    # Subsequent booking of already booked slot MUST fail atomically
    double_book = repo.book_slot("S1", "PAT-999", "TKN-0002")
    assert double_book is False


# ---------------------------------------------------------------------------
# 4. CrmService.list_doctors O(1) Batching (No N+1 Queries)
# ---------------------------------------------------------------------------

def test_crm_service_list_doctors_batching():
    # Setup 5 doctors
    doctor_rows = [
        {"Doctor ID": f"DOC{i:03d}", "Doctor Name": f"Dr. Doctor {i}", "Specialization": "General", "Status": "Active"}
        for i in range(1, 6)
    ]
    mock_doctors = MagicMock()
    mock_doctors.get_doctors.return_value = doctor_rows

    # Setup patient tool with appointments
    mock_patients = MagicMock()
    mock_patients.list_patients.return_value = [
        {"Patient ID": "P1", "Doctor": "Dr. Doctor 1", "Appointment Date": "2026-10-10", "Token No": "TKN-001", "Status": "Confirmed"},
        {"Patient ID": "P2", "Doctor": "Dr. Doctor 1", "Appointment Date": "2026-10-11", "Token No": "TKN-002", "Status": "Confirmed"},
        {"Patient ID": "P3", "Doctor": "Dr. Doctor 2", "Appointment Date": "2026-10-10", "Token No": "TKN-003", "Status": "Confirmed"},
    ]

    mock_prescriptions = MagicMock()
    mock_prescriptions.list_prescriptions.return_value = [
        {"prescription_id": "RX-1", "doctor_id": "DOC001", "status": "finalized"},
        {"prescription_id": "RX-2", "doctor_id": "DOC001", "status": "amended"},
        {"prescription_id": "RX-3", "doctor_id": "DOC002", "status": "draft"},  # draft should not count
    ]

    crm = CrmService(
        patients_tools=mock_patients,
        doctors_tools=mock_doctors,
        prescriptions=mock_prescriptions,
    )

    # Call list_doctors
    doctors = crm.list_doctors()
    assert len(doctors) == 5

    # CRITICAL: list_patients must be called exactly ONCE across all 5 doctors!
    assert mock_patients.list_patients.call_count == 1
    # list_prescriptions must be called exactly ONCE across all 5 doctors!
    assert mock_prescriptions.list_prescriptions.call_count == 1

    # Verify counts
    doc1 = next(d for d in doctors if d["Doctor ID"] == "DOC001")
    assert doc1["assigned_appointments_count"] == 2
    assert doc1["completed_prescriptions_count"] == 2

    doc2 = next(d for d in doctors if d["Doctor ID"] == "DOC002")
    assert doc2["assigned_appointments_count"] == 1
    assert doc2["completed_prescriptions_count"] == 0

    doc3 = next(d for d in doctors if d["Doctor ID"] == "DOC003")
    assert doc3["assigned_appointments_count"] == 0
    assert doc3["completed_prescriptions_count"] == 0


# ---------------------------------------------------------------------------
# 5. Performance Middleware & X-Process-Time Header
# ---------------------------------------------------------------------------

def test_performance_logging_middleware():
    from app.main import create_app
    app = create_app()
    client = TestClient(app)

    # Basic health check
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Process-Time" in response.headers
    assert response.headers["X-Process-Time"].endswith("ms")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0

    # Custom request ID preserved
    custom_res = client.get("/health", headers={"X-Request-ID": "custom-trace-123"})
    assert custom_res.status_code == 200
    assert custom_res.headers["X-Request-ID"] == "custom-trace-123"

    # Detailed health check
    det_res = client.get("/health?details=true")
    assert det_res.status_code == 200
    det_data = det_res.json()
    assert det_data["status"] == "ok"
    assert "uptime_seconds" in det_data
    assert "clinic" in det_data


# ---------------------------------------------------------------------------
# 6. Prescription Appointment Indexing & PDF Disk Caching
# ---------------------------------------------------------------------------

def test_prescription_indexing_and_pdf_caching(tmp_path):
    from app.services.prescription_service import PrescriptionService
    from app.services.audit_service import AuditService

    storage = tmp_path / "prescriptions.json"
    pdf_dir = tmp_path / "prescriptions_pdf"
    audit = AuditService(log_file=tmp_path / "audit.jsonl")

    svc = PrescriptionService(storage_path=storage, pdf_dir=pdf_dir, audit_service=audit)

    # Save draft
    draft = svc.create_or_update_draft(
        data={
            "patient_id": "P-99",
            "patient_name": "Alice Smith",
            "appointment_id": "TKN-9999",
            "diagnosis": "Seasonal Allergy",
            "medicines": [{"name": "Cetirizine", "dosage": "10mg", "frequency": "Once daily", "duration": "5 days"}],
        },
        doctor_id="DOC001",
        doctor_name="Dr. Sarah Khan",
    )
    rx_id = draft["prescription_id"]

    # Verify O(1) index lookup
    rx = svc.get_prescription_by_appointment("TKN-9999")
    assert rx is not None
    assert rx["prescription_id"] == rx_id

    # Case-insensitive lookup
    rx_lower = svc.get_prescription_by_appointment("tkn-9999")
    assert rx_lower is not None
    assert rx_lower["prescription_id"] == rx_id

    # Finalize prescription
    finalized = svc.finalize_prescription(rx_id, doctor_id="DOC001")
    assert finalized["status"] == "finalized"

    # Generate PDF (first time: creates file)
    clean_id, pdf_path = svc.generate_pdf_for_prescription(rx_id, clinic_name="City Clinic")
    assert pdf_path.exists()
    mtime_1 = pdf_path.stat().st_mtime_ns

    # Generate PDF (second time: reuses existing file)
    clean_id_2, pdf_path_2 = svc.generate_pdf_for_prescription(rx_id, clinic_name="City Clinic")
    assert pdf_path_2 == pdf_path
    mtime_2 = pdf_path_2.stat().st_mtime_ns
    assert mtime_1 == mtime_2


# ---------------------------------------------------------------------------
# 7. Admin Perf-Stats Endpoint
# ---------------------------------------------------------------------------

def test_admin_perf_stats_endpoint():
    from app.main import create_app
    from app.core.config import get_settings
    from app.core.auth import create_session

    settings = get_settings()
    app = create_app()
    client = TestClient(app)

    # Unauthenticated request rejected
    res_unauth = client.get("/api/admin/perf-stats")
    assert res_unauth.status_code == 401

    # Authenticated admin request
    admin_token = create_session("admin", role="admin")
    res_auth = client.get(
        "/api/admin/perf-stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert "count" in data
    assert "avg_duration_ms" in data
    assert "p95_duration_ms" in data
    assert "recent" in data


# ---------------------------------------------------------------------------
# 8. Server-Side Pagination and Limit Verification
# ---------------------------------------------------------------------------

def test_server_side_pagination_and_limits():
    mock_patients = MagicMock()
    # 25 appointments
    records = [
        {"Patient ID": f"P{i}", "Name": f"Patient {i}", "Appointment Date": "2026-10-10", "Token No": f"TKN-{i:03d}", "Status": "Confirmed"}
        for i in range(1, 26)
    ]
    mock_patients.list_patients.return_value = records

    crm = CrmService(patients_tools=mock_patients)

    # Page 1, page_size 10
    res_p1 = crm.list_appointments(page=1, page_size=10)
    assert len(res_p1["appointments"]) == 10
    assert res_p1["total"] == 25
    assert res_p1["total_pages"] == 3
    assert res_p1["page"] == 1

    # Page 3, page_size 10 (last page with 5 remaining items)
    res_p3 = crm.list_appointments(page=3, page_size=10)
    assert len(res_p3["appointments"]) == 5
    assert res_p3["page"] == 3


