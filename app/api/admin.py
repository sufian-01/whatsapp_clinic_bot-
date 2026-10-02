"""FastAPI Admin API router for the Clinic CRM Dashboard & CMS."""

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from ..core.auth import (
    create_session,
    get_current_admin,
    hash_password,
    revoke_session,
    verify_password,
)
from ..core.config import Settings
from ..services.crm_service import CrmService


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    clinic_name: str


class AdminProfile(BaseModel):
    username: str
    role: str
    clinic_name: str


class PatientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    phone: str = Field(..., min_length=5, max_length=20)
    email: Optional[str] = ""
    age: Optional[str] = ""
    gender: Optional[str] = ""
    doctor: Optional[str] = ""
    appointment_date: Optional[str] = ""
    appointment_time: Optional[str] = ""
    amount: Optional[str] = ""
    payment_method: Optional[str] = "Offline"
    payment_status: Optional[str] = "Pending"
    booking_status: Optional[str] = "Confirmed"


class PatientUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None


class DoctorCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    specialization: str = Field(..., min_length=1, max_length=150)
    available_days: Optional[str] = "Monday, Wednesday, Friday"
    start_time: Optional[str] = "10:00 AM"
    end_time: Optional[str] = "1:00 PM"
    consultation_fee: str = Field(..., min_length=1)
    status: Optional[str] = "Active"


class DoctorUpdateRequest(BaseModel):
    name: Optional[str] = None
    specialization: Optional[str] = None
    available_days: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    consultation_fee: Optional[str] = None
    status: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., min_length=1)


class SlotCreateRequest(BaseModel):
    doctor_id: str = Field(..., min_length=1)
    doctor_name: str = Field(..., min_length=1)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(..., min_length=1)
    end_time: str = Field(..., min_length=1)
    status: Optional[str] = "Available"


class SlotUpdateRequest(BaseModel):
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class RescheduleRequest(BaseModel):
    new_slot_id: str = Field(..., min_length=1)
    new_date: Optional[str] = None
    new_time: Optional[str] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = ""


class AppointmentCreateRequest(BaseModel):
    slot_id: str = Field(..., min_length=1)
    patient_id: Optional[str] = ""
    name: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    age: Optional[str] = ""
    gender: Optional[str] = ""
    payment_method: Optional[str] = "Offline"
    payment_status: Optional[str] = "Pending"
    amount: Optional[str] = ""


class PaymentRecordRequest(BaseModel):
    amount: str = Field(..., min_length=1)
    payment_method: Optional[str] = "Cash"
    transaction_ref: Optional[str] = ""
    notes: Optional[str] = ""


# ---------------------------------------------------------------------------
# Router Factory
# ---------------------------------------------------------------------------

def create_admin_router(crm: CrmService, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/admin", tags=["admin"])

    # -----------------------------------------------------------------------
    # AUTHENTICATION
    # -----------------------------------------------------------------------

    @router.post("/auth/login", response_model=LoginResponse)
    async def login(credentials: LoginRequest, response: Response):
        """Authenticate admin user and issue a secure session token."""
        expected_user = settings.crm_admin_username or "admin"
        username_match = credentials.username.strip().casefold() == expected_user.casefold()

        password_valid = False
        if settings.crm_admin_password_hash:
            password_valid = verify_password(credentials.password, settings.crm_admin_password_hash)
        elif settings.crm_admin_password:
            password_valid = credentials.password == settings.crm_admin_password

        if not (username_match and password_valid):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_session(
            username=expected_user,
            role="admin",
            expires_hours=settings.crm_token_expire_hours,
        )

        response.set_cookie(
            key="admin_session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=settings.crm_token_expire_hours * 3600,
        )

        return LoginResponse(
            token=token,
            username=expected_user,
            role="admin",
            clinic_name=settings.clinic_name,
        )

    @router.post("/auth/logout")
    async def logout(response: Response, current_admin: dict = Depends(get_current_admin)):
        """Revoke current admin session."""
        token = current_admin.get("token")
        if token:
            revoke_session(token)
        response.delete_cookie(key="admin_session")
        return {"success": True, "message": "Logged out successfully"}

    @router.get("/auth/me", response_model=AdminProfile)
    async def me(current_admin: dict = Depends(get_current_admin)):
        """Return authenticated admin profile."""
        return AdminProfile(
            username=current_admin.get("username", "admin"),
            role=current_admin.get("role", "admin"),
            clinic_name=settings.clinic_name,
        )

    # -----------------------------------------------------------------------
    # DASHBOARD & ANALYTICS
    # -----------------------------------------------------------------------

    @router.get("/dashboard/stats")
    async def get_dashboard_stats(
        today: Optional[str] = None,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Aggregated operational metrics for admin dashboard."""
        try:
            return crm.get_dashboard_stats(today_str=today)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to compute dashboard stats: {err}")

    @router.get("/dashboard/analytics")
    async def get_dashboard_analytics(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        preset: Optional[str] = None,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Extended analytics summary for dashboard and reports."""
        try:
            return crm.get_analytics_summary(start_date=start_date, end_date=end_date, range_preset=preset)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to compute analytics: {err}")

    @router.get("/dashboard/today-appointments")
    async def get_today_appointments(
        today: Optional[str] = None,
        current_admin: dict = Depends(get_current_admin),
    ):
        """List today's scheduled appointments."""
        try:
            return crm.get_today_appointments(today_str=today)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch today's appointments: {err}")

    @router.get("/dashboard/recent-patients")
    async def get_recent_patients(
        limit: int = Query(5, ge=1, le=20),
        current_admin: dict = Depends(get_current_admin),
    ):
        """List recently registered or visited patients."""
        try:
            return crm.get_recent_patients(limit=limit)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch recent patients: {err}")

    # -----------------------------------------------------------------------
    # PATIENTS
    # -----------------------------------------------------------------------

    @router.get("/patients")
    async def list_patients(
        search: str = Query("", max_length=100),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        current_admin: dict = Depends(get_current_admin),
    ):
        """Search and list unique patients with pagination."""
        try:
            return crm.list_patients(search=search, page=page, page_size=page_size)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to list patients: {err}")

    @router.get("/patients/check-duplicates")
    async def check_patient_duplicates(
        phone: str = Query("", max_length=30),
        email: str = Query("", max_length=100),
        current_admin: dict = Depends(get_current_admin),
    ):
        """Check for existing patients matching phone or email."""
        return crm.check_patient_duplicates(phone=phone, email=email)

    @router.get("/patients/{patient_id}")
    async def get_patient(
        patient_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Get patient profile and appointment history."""
        patient = crm.get_patient(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
        return patient

    @router.post("/patients", status_code=status.HTTP_201_CREATED)
    async def create_patient(
        payload: PatientCreateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Create a new patient record."""
        try:
            res = crm.create_patient(payload.model_dump(), admin_user=current_admin.get("username", "admin"))
            if isinstance(res, dict) and not res.get("success", True):
                raise HTTPException(status_code=400, detail=res.get("message", "Failed to create patient"))
            return {"success": True, "patient": res}
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to create patient: {err}")

    @router.post("/patients/with-dedup")
    async def create_patient_with_dedup(
        payload: PatientCreateRequest,
        force: bool = Query(False),
        current_admin: dict = Depends(get_current_admin),
    ):
        """Create patient checking for duplicates, or bypass duplicate check if force=true."""
        try:
            res = crm.create_patient_with_dedup(
                payload.model_dump(),
                force=force,
                admin_user=current_admin.get("username", "admin"),
            )
            if not res.get("success"):
                return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=res)
            return res
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    @router.put("/patients/{patient_id}")
    async def update_patient(
        patient_id: str,
        payload: PatientUpdateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Update patient demographic information."""
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        try:
            res = crm.update_patient(patient_id, updates, admin_user=current_admin.get("username", "admin"))
            if isinstance(res, dict) and not res.get("success"):
                raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found or update failed")
            return {"success": True, "patient_id": patient_id}
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to update patient: {err}")

    @router.post("/patients/{patient_id}/deactivate")
    async def deactivate_patient(
        patient_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Soft-deactivate a patient while preserving medical and appointment history."""
        try:
            return crm.deactivate_patient(patient_id, admin_user=current_admin.get("username", "admin"))
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to deactivate patient: {err}")

    @router.get("/patients/{patient_id}/appointments")
    async def get_patient_appointments(
        patient_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """List appointment history for a patient."""
        return crm.get_patient_appointments(patient_id)

    @router.get("/patients/{patient_id}/payments")
    async def get_patient_payments(
        patient_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """List payment history for a patient."""
        return crm.get_patient_payments(patient_id)

    # -----------------------------------------------------------------------
    # DOCTORS
    # -----------------------------------------------------------------------

    @router.get("/doctors")
    async def list_doctors(
        search: str = Query("", max_length=100),
        active_only: bool = False,
        current_admin: dict = Depends(get_current_admin),
    ):
        """List all clinic doctors with optional search and active status filter."""
        try:
            return crm.list_doctors(search=search, active_only=active_only)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to list doctors: {err}")

    @router.get("/doctors/{doctor_id}")
    async def get_doctor(
        doctor_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Get single doctor details."""
        doc = crm.get_doctor(doctor_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Doctor '{doctor_id}' not found")
        return doc

    @router.get("/doctors/{doctor_id}/deactivation-check")
    async def doctor_deactivation_check(
        doctor_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Check if doctor has upcoming active appointments before deactivation."""
        try:
            return crm.check_doctor_deactivation_safety(doctor_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=str(err))

    @router.post("/doctors", status_code=status.HTTP_201_CREATED)
    async def create_doctor(
        payload: DoctorCreateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Add a new doctor to the clinic master sheet."""
        try:
            return crm.create_doctor(payload.model_dump(), admin_user=current_admin.get("username", "admin"))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to add doctor: {err}")

    @router.put("/doctors/{doctor_id}")
    async def update_doctor(
        doctor_id: str,
        payload: DoctorUpdateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Update doctor profile details."""
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        try:
            updated = crm.update_doctor(doctor_id, updates, admin_user=current_admin.get("username", "admin"))
            if not updated:
                raise HTTPException(status_code=404, detail=f"Doctor '{doctor_id}' not found")
            return {"success": True, "doctor": updated}
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to update doctor: {err}")

    @router.patch("/doctors/{doctor_id}/status")
    async def set_doctor_status(
        doctor_id: str,
        payload: StatusUpdateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Activate or deactivate a doctor."""
        valid_statuses = ("Active", "Inactive")
        target = payload.status.strip().title()
        if target not in valid_statuses:
            raise HTTPException(status_code=400, detail="Status must be 'Active' or 'Inactive'")
        try:
            success = crm.set_doctor_status(doctor_id, target, admin_user=current_admin.get("username", "admin"))
            if not success:
                raise HTTPException(status_code=404, detail=f"Doctor '{doctor_id}' not found")
            return {"success": True, "doctor_id": doctor_id, "status": target}
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to change doctor status: {err}")

    @router.get("/doctors/{doctor_id}/availability")
    async def get_doctor_availability(
        doctor_id: str,
        from_date: Optional[str] = None,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Fetch available slots for a doctor."""
        return crm.get_doctor_availability(doctor_id=doctor_id, from_date=from_date)

    # -----------------------------------------------------------------------
    # APPOINTMENTS
    # -----------------------------------------------------------------------

    @router.get("/appointments")
    async def list_appointments(
        search: str = Query("", max_length=100),
        date: str = Query("", max_length=20),
        doctor: str = Query("", max_length=100),
        status: str = Query("", max_length=50),
        payment_status: str = Query("", max_length=50),
        page: int = Query(1, ge=1),
        page_size: int = Query(15, ge=1, le=100),
        current_admin: dict = Depends(get_current_admin),
    ):
        """List appointments with filters and pagination."""
        try:
            return crm.list_appointments(
                search=search,
                date_filter=date,
                doctor_filter=doctor,
                status_filter=status,
                payment_status_filter=payment_status,
                page=page,
                page_size=page_size,
            )
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to list appointments: {err}")

    @router.post("/appointments", status_code=status.HTTP_201_CREATED)
    async def create_appointment(
        payload: AppointmentCreateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Create a new appointment manually from the CRM with concurrency slot locking."""
        try:
            return crm.create_appointment_manual(
                payload.model_dump(),
                admin_user=current_admin.get("username", "admin"),
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except RuntimeError as err:
            raise HTTPException(status_code=409, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to create appointment: {err}")

    @router.get("/appointments/{appointment_id}")
    async def get_appointment(
        appointment_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Get appointment details by Token No or Patient ID."""
        appt = crm.get_appointment(appointment_id)
        if not appt:
            raise HTTPException(status_code=404, detail=f"Appointment '{appointment_id}' not found")
        return appt

    @router.get("/appointments/{appointment_id}/invoice")
    async def get_appointment_invoice(
        appointment_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Generate and stream a PDF invoice for an appointment."""
        try:
            inv = crm.generate_appointment_invoice(appointment_id)
            pdf_path = Path(inv["file_path"])
            if not pdf_path.exists():
                raise HTTPException(status_code=500, detail="Generated invoice PDF could not be found.")
            return FileResponse(
                path=str(pdf_path),
                media_type="application/pdf",
                filename=f"invoice_{appointment_id}.pdf",
            )
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to generate invoice: {err}")

    @router.patch("/appointments/{appointment_id}/status")
    async def update_appointment_status(
        appointment_id: str,
        payload: StatusUpdateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Update appointment status (e.g. Confirmed -> Completed)."""
        try:
            return crm.update_appointment_status(
                appointment_id,
                payload.status,
                admin_user=current_admin.get("username", "admin"),
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to update appointment status: {err}")

    @router.post("/appointments/{appointment_id}/reschedule")
    async def reschedule_appointment(
        appointment_id: str,
        payload: RescheduleRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Reschedule an existing appointment to a new slot."""
        try:
            return crm.reschedule_appointment(
                identifier=appointment_id,
                new_slot_id=payload.new_slot_id,
                new_date=payload.new_date or "",
                new_time=payload.new_time or "",
                admin_user=current_admin.get("username", "admin"),
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except RuntimeError as err:
            raise HTTPException(status_code=409, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to reschedule appointment: {err}")

    @router.post("/appointments/{appointment_id}/cancel")
    async def cancel_appointment(
        appointment_id: str,
        payload: Optional[CancelRequest] = None,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Cancel an appointment safely, preserving history and freeing the slot."""
        try:
            reason = payload.reason if payload else ""
            return crm.cancel_appointment(
                identifier=appointment_id,
                reason=reason,
                admin_user=current_admin.get("username", "admin"),
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to cancel appointment: {err}")

    # -----------------------------------------------------------------------
    # CALENDAR
    # -----------------------------------------------------------------------

    @router.get("/calendar")
    async def get_calendar(
        start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
        end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
        doctor: str = Query("", max_length=100),
        current_admin: dict = Depends(get_current_admin),
    ):
        """Get appointments formatted for calendar schedule views within a date range."""
        try:
            return crm.get_calendar_events(start_date=start_date, end_date=end_date, doctor_filter=doctor)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch calendar events: {err}")

    # -----------------------------------------------------------------------
    # APPOINTMENT SLOTS
    # -----------------------------------------------------------------------

    @router.get("/slots")
    async def list_slots(
        date: str = Query("", max_length=20),
        doctor: str = Query("", max_length=100),
        status: str = Query("", max_length=50),
        current_admin: dict = Depends(get_current_admin),
    ):
        """List appointment slots with optional filters."""
        try:
            return crm.list_slots(date_filter=date, doctor_filter=doctor, status_filter=status)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to list slots: {err}")

    @router.post("/slots", status_code=status.HTTP_201_CREATED)
    async def create_slot(
        payload: SlotCreateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Add a new slot to the appointment slots sheet."""
        try:
            res = crm.create_slot(payload.model_dump(), admin_user=current_admin.get("username", "admin"))
            return {"success": True, "slot": res}
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to create slot: {err}")

    @router.put("/slots/{slot_id}")
    async def update_slot(
        slot_id: str,
        payload: SlotUpdateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Update slot details. Cannot mark an actively booked slot available without validation."""
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        try:
            res = crm.update_slot(slot_id, updates, admin_user=current_admin.get("username", "admin"))
            if not res:
                raise HTTPException(status_code=404, detail=f"Slot '{slot_id}' not found")
            return {"success": True, "slot": res}
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to update slot: {err}")

    @router.patch("/slots/{slot_id}/status")
    async def set_slot_status(
        slot_id: str,
        payload: StatusUpdateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Update slot availability status. Rejects unsafe changes to booked slots."""
        try:
            success = crm.set_slot_status(slot_id, payload.status, admin_user=current_admin.get("username", "admin"))
            if not success:
                raise HTTPException(status_code=404, detail=f"Slot '{slot_id}' not found")
            return {"success": True, "slot_id": slot_id, "status": payload.status}
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to change slot status: {err}")

    # -----------------------------------------------------------------------
    # PAYMENTS & BILLING
    # -----------------------------------------------------------------------

    @router.get("/payments")
    async def list_payments(
        status: str = Query("", max_length=50),
        search: str = Query("", max_length=100),
        page: int = Query(1, ge=1),
        page_size: int = Query(15, ge=1, le=100),
        current_admin: dict = Depends(get_current_admin),
    ):
        """List payment records with pending/paid status filter."""
        try:
            return crm.list_payments(
                status_filter=status,
                search=search,
                page=page,
                page_size=page_size,
            )
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to list payments: {err}")

    @router.get("/payments/{payment_id}")
    async def get_payment(
        payment_id: str,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Get payment details for an appointment."""
        pay = crm.get_payment(payment_id)
        if not pay:
            raise HTTPException(status_code=404, detail=f"Payment record '{payment_id}' not found")
        return pay

    @router.patch("/payments/{payment_id}/status")
    async def update_payment_status(
        payment_id: str,
        payload: StatusUpdateRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Mark payment status (e.g. mark offline payment collected at clinic as Paid)."""
        try:
            return crm.update_payment_status(payment_id, payload.status, admin_user=current_admin.get("username", "admin"))
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to update payment status: {err}")

    @router.post("/payments/{payment_id}/record")
    async def record_payment(
        payment_id: str,
        payload: PaymentRecordRequest,
        current_admin: dict = Depends(get_current_admin),
    ):
        """Record manual collection of payment at the clinic desk."""
        try:
            return crm.record_manual_payment(
                identifier=payment_id,
                amount=payload.amount,
                payment_method=payload.payment_method or "Cash",
                transaction_ref=payload.transaction_ref or "",
                notes=payload.notes or "",
                admin_user=current_admin.get("username", "admin"),
            )
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to record payment: {err}")

    # -----------------------------------------------------------------------
    # REPORTS & EXPORTS
    # -----------------------------------------------------------------------

    @router.get("/reports/export")
    async def export_report(
        type: str = Query(..., pattern=r"^(appointments|patients|payments)$"),
        start_date: str = Query("", max_length=20),
        end_date: str = Query("", max_length=20),
        current_admin: dict = Depends(get_current_admin),
    ):
        """Export CSV report with formula injection neutralization (CWE-1236)."""
        try:
            csv_content = crm.export_report_csv(
                report_type=type,
                start_date=start_date,
                end_date=end_date,
            )
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{type}_report.csv"',
                    "Cache-Control": "no-cache",
                },
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to export report: {err}")

    # -----------------------------------------------------------------------
    # AUDIT & ACTIVITY LOGS
    # -----------------------------------------------------------------------

    @router.get("/audit-logs")
    async def get_audit_logs(
        action: Optional[str] = Query(None, max_length=50),
        entity_type: Optional[str] = Query(None, max_length=50),
        entity_id: Optional[str] = Query(None, max_length=50),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        current_admin: dict = Depends(get_current_admin),
    ):
        """Query immutable audit log entries."""
        try:
            return crm.audit.get_logs(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit,
                offset=offset,
            )
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Failed to fetch audit logs: {err}")

    return router
