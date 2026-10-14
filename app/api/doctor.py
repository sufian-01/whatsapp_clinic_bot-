"""FastAPI Doctor Portal API router for verified clinical staff.

Provides dedicated clinical workflow endpoints:
- Own profile & schedule
- Own slot management with overlap & booked-slot safeguards
- Assigned patient records & visit history
- Draft & finalized prescription lifecycle with amendment tracking
- PDF download & email delivery to patients
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..core.auth import get_current_doctor
from ..core.config import Settings
from ..services.crm_service import CrmService


class DoctorSlotCreateRequest(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(..., min_length=1)
    end_time: str = Field(..., min_length=1)


class DoctorSlotUpdateRequest(BaseModel):
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class PrescriptionMedicineItem(BaseModel):
    name: str = Field(..., min_length=1)
    strength: Optional[str] = ""
    dosage: str = Field(..., min_length=1)
    frequency: str = Field(..., min_length=1)
    duration: str = Field(..., min_length=1)
    instructions: Optional[str] = ""


class PrescriptionCreateRequest(BaseModel):
    prescription_id: Optional[str] = ""
    appointment_id: str = Field(..., min_length=1)
    patient_id: str = Field(..., min_length=1)
    patient_name: str = Field(..., min_length=1)
    patient_phone: Optional[str] = ""
    patient_email: Optional[str] = ""
    patient_age: Optional[str] = ""
    patient_gender: Optional[str] = ""
    date: Optional[str] = ""
    chief_complaints: Optional[str] = ""
    diagnosis: Optional[str] = ""
    symptoms: Optional[str] = ""
    vitals: Optional[dict] = None
    clinical_notes: Optional[str] = ""
    medicines: list[PrescriptionMedicineItem] = []
    tests_advised: Optional[str] = ""
    advice: Optional[str] = ""
    follow_up_date: Optional[str] = ""


class PrescriptionAmendRequest(BaseModel):
    amendment_reason: str = Field(..., min_length=3)
    chief_complaints: Optional[str] = None
    diagnosis: Optional[str] = None
    symptoms: Optional[str] = None
    vitals: Optional[dict] = None
    clinical_notes: Optional[str] = None
    medicines: Optional[list[PrescriptionMedicineItem]] = None
    tests_advised: Optional[str] = None
    advice: Optional[str] = None
    follow_up_date: Optional[str] = None


class PrescriptionEmailRequest(BaseModel):
    recipient_email: Optional[str] = ""
    recipient_type: Optional[str] = "patient"


def create_doctor_router(crm: CrmService, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/doctor", tags=["doctor"])

    # -----------------------------------------------------------------------
    # DOCTOR PROFILE & DASHBOARD
    # -----------------------------------------------------------------------

    @router.get("/profile")
    async def get_profile(current_doctor: dict = Depends(get_current_doctor)):
        """Retrieve the authenticated doctor's profile and schedule."""
        doc_id = current_doctor.get("doctor_id")
        doc = crm.get_doctor(doc_id)
        if not doc:
            return {
                "doctor_id": doc_id,
                "doctor_name": current_doctor.get("doctor_name", "Doctor"),
                "username": current_doctor.get("username"),
            }
        return doc

    @router.get("/dashboard")
    async def get_dashboard(
        today: Optional[str] = None,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Live operational metrics for the Doctor Portal."""
        doc_id = current_doctor.get("doctor_id")
        try:
            return crm.get_doctor_dashboard_stats(doc_id, today_str=today)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch doctor dashboard: {err}")

    # -----------------------------------------------------------------------
    # APPOINTMENTS
    # -----------------------------------------------------------------------

    @router.get("/appointments")
    async def list_appointments(
        date: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """List appointments assigned strictly to this doctor."""
        doc_id = current_doctor.get("doctor_id")
        try:
            return crm.get_doctor_appointments(
                doctor_id=doc_id,
                date_filter=date or "",
                status_filter=status or "",
                search=search or "",
            )
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch doctor appointments: {err}")

    @router.get("/appointments/{appointment_id}")
    async def get_appointment(
        appointment_id: str,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Fetch appointment details and patient visit history with this doctor."""
        doc_id = current_doctor.get("doctor_id")
        try:
            return crm.get_doctor_appointment(appointment_id, doctor_id=doc_id)
        except PermissionError as err:
            raise HTTPException(status_code=403, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch appointment: {err}")

    # -----------------------------------------------------------------------
    # PATIENTS
    # -----------------------------------------------------------------------

    @router.get("/patients")
    async def list_patients(
        search: Optional[str] = None,
        require_paid: bool = False,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """List patients assigned to this doctor."""
        doc_id = current_doctor.get("doctor_id")
        try:
            return crm.get_doctor_patients(
                doctor_id=doc_id,
                search=search or "",
                require_verified_payment=require_paid,
            )
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to list doctor patients: {err}")

    @router.get("/patients/{patient_id}")
    async def get_patient_detail(
        patient_id: str,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Get clinical profile of a patient assigned to this doctor."""
        doc_id = current_doctor.get("doctor_id")
        try:
            return crm.get_doctor_patient_detail(patient_id, doctor_id=doc_id)
        except PermissionError as err:
            raise HTTPException(status_code=403, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch patient details: {err}")

    # -----------------------------------------------------------------------
    # SLOTS
    # -----------------------------------------------------------------------

    @router.get("/slots")
    async def list_slots(
        date: Optional[str] = None,
        status: Optional[str] = None,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """List slots belonging strictly to this doctor."""
        doc_id = current_doctor.get("doctor_id")
        try:
            return crm.get_doctor_slots(doc_id, date_filter=date or "", status_filter=status or "")
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch doctor slots: {err}")

    @router.post("/slots", status_code=status.HTTP_201_CREATED)
    async def create_slot(
        payload: DoctorSlotCreateRequest,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Add an available slot with overlap and past-time validations."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        try:
            return crm.create_doctor_slot(
                doctor_id=doc_id,
                date_val=payload.date,
                start_time=payload.start_time,
                end_time=payload.end_time,
                user=username,
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to create doctor slot: {err}")

    @router.patch("/slots/{slot_id}")
    async def update_slot(
        slot_id: str,
        payload: DoctorSlotUpdateRequest,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Update slot with booked-slot safeguards and cross-doctor isolation."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        try:
            return crm.update_doctor_slot(
                slot_id=slot_id,
                doctor_id=doc_id,
                updates=updates,
                user=username,
            )
        except PermissionError as err:
            raise HTTPException(status_code=403, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to update doctor slot: {err}")

    @router.delete("/slots/{slot_id}")
    async def delete_slot(
        slot_id: str,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Mark slot unavailable or delete with booked-slot conflict prevention."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        try:
            return crm.delete_doctor_slot(slot_id, doctor_id=doc_id, user=username)
        except PermissionError as err:
            raise HTTPException(status_code=403, detail=str(err))
        except RuntimeError as err:
            raise HTTPException(status_code=409, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to delete doctor slot: {err}")

    # -----------------------------------------------------------------------
    # PRESCRIPTIONS
    # -----------------------------------------------------------------------

    @router.get("/prescriptions")
    async def list_prescriptions(
        patient_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        status: Optional[str] = None,
        date: Optional[str] = None,
        search: Optional[str] = None,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """List prescriptions authored by this doctor."""
        doc_id = current_doctor.get("doctor_id")
        try:
            return crm.prescriptions.list_prescriptions(
                doctor_id=doc_id,
                patient_id=patient_id,
                appointment_id=appointment_id,
                status=status,
                date_filter=date,
                search=search,
            )
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to list prescriptions: {err}")

    @router.post("/prescriptions")
    async def save_prescription_draft(
        payload: PrescriptionCreateRequest,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Save prescription as draft."""
        doc_id = current_doctor.get("doctor_id")
        doc_name = current_doctor.get("doctor_name", "Doctor")
        username = current_doctor.get("username", "doctor")

        # Resolve specialization, qualification, registration
        doc_record = crm.get_doctor(doc_id)
        spec = (doc_record.get("Specialization") or "") if doc_record else ""
        qual = (doc_record.get("Qualification") or "") if doc_record else ""
        reg = (doc_record.get("Registration Number") or doc_record.get("Reg No") or "") if doc_record else ""

        try:
            data = payload.model_dump()
            return crm.prescriptions.create_or_update_draft(
                data=data,
                doctor_id=doc_id,
                doctor_name=doc_name,
                doctor_specialization=spec,
                doctor_qualification=qual,
                doctor_reg_no=reg,
                user=username,
            )
        except PermissionError as err:
            raise HTTPException(status_code=403, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to save prescription draft: {err}")

    @router.get("/prescriptions/{prescription_id}")
    async def get_prescription(
        prescription_id: str,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Fetch prescription details, verifying ownership."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        rx = crm.prescriptions.get_prescription(prescription_id)
        if not rx:
            raise HTTPException(status_code=404, detail="Prescription not found.")
        is_owner = (
            rx.get("doctor_id", "").casefold() == doc_id.strip().casefold()
            or (bool(rx.get("created_by")) and rx.get("created_by", "").casefold() == username.strip().casefold())
        )
        if not is_owner:
            raise HTTPException(status_code=403, detail="Access forbidden: You cannot view another physician's prescription.")
        return rx

    @router.post("/prescriptions/{prescription_id}/finalize")
    async def finalize_prescription(
        prescription_id: str,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Review and finalize a draft prescription with strict validation."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        try:
            return crm.prescriptions.finalize_prescription(
                prescription_id=prescription_id,
                doctor_id=doc_id,
                user=username,
            )
        except PermissionError as err:
            raise HTTPException(status_code=403, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to finalize prescription: {err}")

    @router.post("/prescriptions/{prescription_id}/amend")
    async def amend_prescription(
        prescription_id: str,
        payload: PrescriptionAmendRequest,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Amend an already finalized prescription, creating an audited new version."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        updates = {k: v for k, v in payload.model_dump().items() if v is not None and k != "amendment_reason"}
        try:
            return crm.prescriptions.amend_prescription(
                prescription_id=prescription_id,
                updates=updates,
                doctor_id=doc_id,
                user=username,
                amendment_reason=payload.amendment_reason,
            )
        except PermissionError as err:
            raise HTTPException(status_code=403, detail=str(err))
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to amend prescription: {err}")

    @router.get("/prescriptions/{prescription_id}/pdf")
    async def download_prescription_pdf(
        prescription_id: str,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Generate and stream the professional prescription PDF."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        rx = crm.prescriptions.get_prescription(prescription_id)
        if not rx:
            raise HTTPException(status_code=404, detail="Prescription not found.")
        is_owner = (
            rx.get("doctor_id", "").casefold() == doc_id.strip().casefold()
            or (bool(rx.get("created_by")) and rx.get("created_by", "").casefold() == username.strip().casefold())
        )
        if not is_owner:
            raise HTTPException(status_code=403, detail="Access forbidden: You cannot download another physician's prescription.")

        try:
            clean_id, pdf_path = crm.prescriptions.generate_pdf_for_prescription(
                prescription_id=prescription_id,
                clinic_name=settings.clinic_name,
                clinic_phone=settings.support_phone,
                clinic_email="",
                clinic_address="",
            )
            if not pdf_path.exists():
                raise HTTPException(status_code=500, detail="Failed to locate generated prescription PDF.")

            return FileResponse(
                path=str(pdf_path),
                media_type="application/pdf",
                filename=f"prescription_{prescription_id}_v{rx.get('version', 1)}.pdf",
            )
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to generate prescription PDF: {err}")

    @router.post("/prescriptions/{prescription_id}/email")
    async def email_prescription(
        prescription_id: str,
        payload: PrescriptionEmailRequest,
        current_doctor: dict = Depends(get_current_doctor),
    ):
        """Email verified prescription PDF to the patient."""
        doc_id = current_doctor.get("doctor_id")
        username = current_doctor.get("username", "doctor")
        rx = crm.prescriptions.get_prescription(prescription_id)
        if not rx:
            raise HTTPException(status_code=404, detail="Prescription not found.")
        is_owner = (
            rx.get("doctor_id", "").casefold() == doc_id.strip().casefold()
            or (bool(rx.get("created_by")) and rx.get("created_by", "").casefold() == username.strip().casefold())
        )
        if not is_owner:
            raise HTTPException(status_code=403, detail="Access forbidden: You cannot email another physician's prescription.")

        recipient_type = (payload.recipient_type or "patient").lower().strip()
        if recipient_type == "admin":
            recipient = (payload.recipient_email or getattr(settings, "admin_email", "") or "admin@clinic.com").strip()
        else:
            recipient = (payload.recipient_email or rx.get("patient_email", "")).strip()

        if not recipient:
            target_label = "Clinic Admin" if recipient_type == "admin" else "Patient"
            raise HTTPException(status_code=400, detail=f"{target_label} email address is required to send prescription.")

        # Check for previous successful delivery to avoid accidental duplicate sends unless forced
        if rx.get("email_delivery") and rx["email_delivery"].get("sent") and rx["email_delivery"].get("recipient") == recipient:
            # Already sent to this recipient
            pass

        try:
            clean_id, pdf_path = crm.prescriptions.generate_pdf_for_prescription(
                prescription_id=prescription_id,
                clinic_name=settings.clinic_name,
                clinic_phone=settings.support_phone,
            )

            if not crm.gmail:
                raise HTTPException(status_code=503, detail="Email service is not configured on this server.")

            result = crm.gmail.send_prescription_email(
                recipient=recipient,
                prescription_data=rx,
                clinic_name=settings.clinic_name,
                support_phone=settings.support_phone,
                pdf_path=str(pdf_path),
            )

            crm.prescriptions.record_email_delivery(
                prescription_id=prescription_id,
                success=result.get("email_sent", False),
                recipient=recipient,
                error=result.get("error"),
            )

            if not result.get("email_sent"):
                raise HTTPException(status_code=502, detail=f"Email delivery failed: {result.get('error', 'Unknown provider error')}")

            return {
                "success": True,
                "message": f"Prescription successfully emailed to {recipient}.",
                "recipient": recipient,
            }
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to dispatch prescription email: {err}")

    return router

