"""CRM Service layer coordinating Google Sheets repositories for Admin Dashboard & CMS."""

import csv
from datetime import date, datetime, timedelta, timezone
import io
import math
from pathlib import Path
import re
from typing import Optional
from zoneinfo import ZoneInfo

from ..tools.invoice import InvoiceData, generate_invoice
from ..tools.slots import SlotRepository
from .audit_service import AuditService


def sanitize_csv_field(val: object) -> str:
    """Neutralize formula injection (CWE-1236) in CSV exports."""
    s = str(val if val is not None else "").strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


class CrmService:
    def __init__(
        self,
        patients_tools=None,
        doctors_tools=None,
        slots_tools=None,
        payments_tools=None,
        invoices_tools=None,
        audit_service: Optional[AuditService] = None,
        clinic_name: str = "Clinic",
        clinic_timezone: str = "Asia/Kolkata",
    ) -> None:
        self.patients = patients_tools
        self.doctors = doctors_tools
        self.slots = slots_tools
        self.payments = payments_tools
        self.invoices = invoices_tools
        self.audit = audit_service or AuditService()
        self.clinic_name = clinic_name
        self.clinic_timezone = clinic_timezone

    # ------------------------------------------------------------------
    # DASHBOARD & ANALYTICS
    # ------------------------------------------------------------------

    def _get_tz(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.clinic_timezone)
        except Exception:
            return ZoneInfo("UTC")

    def get_dashboard_stats(self, today_str: Optional[str] = None) -> dict:
        """Compute live aggregated metrics from sheet repositories."""
        if today_str:
            today = today_str
        else:
            now_tz = datetime.now(self._get_tz())
            today = now_tz.date().isoformat()

        # Patients & Bookings
        patient_records = self.patients.list_patients() if self.patients else []

        unique_patient_ids = set()
        today_appointments = 0
        upcoming_appointments = 0
        completed_appointments = 0
        pending_payments = 0
        total_revenue = 0.0

        for record in patient_records:
            pid = record.get("Patient ID") or record.get("Phone", "")
            if pid:
                unique_patient_ids.add(pid)

            appt_date = record.get("Appointment Date", "").strip()
            booking_status = (record.get("Booking Status") or record.get("Status", "")).strip().casefold()
            payment_status = record.get("Payment Status", "").strip().casefold()
            amount_str = record.get("Amount", "").replace("₹", "").replace(",", "").strip()

            if appt_date == today and booking_status != "cancelled":
                today_appointments += 1

            if appt_date > today and booking_status in ("confirmed", "pending"):
                upcoming_appointments += 1

            if booking_status == "completed":
                completed_appointments += 1

            if payment_status == "pending" and booking_status != "cancelled":
                pending_payments += 1
            elif payment_status == "paid":
                try:
                    total_revenue += float(amount_str)
                except (ValueError, TypeError):
                    pass

        # Doctors
        doctors = self.doctors.get_doctors() if self.doctors else []
        active_doctors = [d for d in doctors if d.get("Status", "").strip().casefold() not in ("inactive", "disabled")]

        # Available Slots
        all_slots_res = self.slots.list_all_slots() if self.slots else {"slots": []}
        all_slots = all_slots_res.get("slots", []) if isinstance(all_slots_res, dict) else all_slots_res
        available_slots = sum(
            1 for s in all_slots
            if s.get("Status", "").strip().casefold() == "available" and s.get("Date", "") >= today
        )

        return {
            "total_patients": len(unique_patient_ids),
            "total_appointments": len(patient_records),
            "total_doctors": len(doctors),
            "active_doctors": len(active_doctors),
            "today_appointments": today_appointments,
            "upcoming_appointments": upcoming_appointments,
            "completed_appointments": completed_appointments,
            "pending_payments": pending_payments,
            "total_revenue": total_revenue,
            "available_slots": available_slots,
            "today_date": today,
        }

    def get_analytics_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        range_preset: Optional[str] = None,
    ) -> dict:
        """Comprehensive operational and financial analytics within a date range."""
        now_tz = datetime.now(self._get_tz())
        today = now_tz.date()

        if range_preset == "today":
            start_d = today
            end_d = today
        elif range_preset == "yesterday":
            start_d = today - timedelta(days=1)
            end_d = today - timedelta(days=1)
        elif range_preset == "this_week":
            # Monday as start of week
            start_d = today - timedelta(days=today.weekday())
            end_d = start_d + timedelta(days=6)
        elif range_preset == "this_month":
            start_d = today.replace(day=1)
            # End of month
            next_month = (start_d.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_d = next_month - timedelta(days=1)
        elif range_preset == "last_30_days":
            start_d = today - timedelta(days=29)
            end_d = today
        elif start_date and end_date:
            try:
                start_d = date.fromisoformat(start_date)
                end_d = date.fromisoformat(end_date)
            except ValueError:
                start_d = today - timedelta(days=30)
                end_d = today
        else:
            start_d = today - timedelta(days=30)
            end_d = today

        start_str = start_d.isoformat()
        end_str = end_d.isoformat()

        records = self.patients.list_patients() if self.patients else []

        total_appts = 0
        confirmed_count = 0
        completed_count = 0
        cancelled_count = 0
        pending_count = 0
        revenue_collected = 0.0
        pending_revenue = 0.0

        doctor_workload: dict[str, dict] = {}
        daily_counts: dict[str, int] = {}

        for r in records:
            d_str = r.get("Appointment Date", "").strip()
            if not d_str or d_str < start_str or d_str > end_str:
                continue

            total_appts += 1
            status = (r.get("Booking Status") or r.get("Status", "Confirmed")).strip().casefold()
            pay_status = r.get("Payment Status", "").strip().casefold()
            amt_str = r.get("Amount", "").replace("₹", "").replace(",", "").strip()
            try:
                amt = float(amt_str)
            except (ValueError, TypeError):
                amt = 0.0

            if status == "confirmed":
                confirmed_count += 1
            elif status == "completed":
                completed_count += 1
            elif status == "cancelled":
                cancelled_count += 1
            else:
                pending_count += 1

            if pay_status == "paid":
                revenue_collected += amt
            elif pay_status == "pending" and status != "cancelled":
                pending_revenue += amt

            # Doctor breakdown
            doc_name = r.get("Doctor", "").strip() or "Unassigned"
            if doc_name not in doctor_workload:
                doctor_workload[doc_name] = {"doctor": doc_name, "count": 0, "revenue": 0.0}
            doctor_workload[doc_name]["count"] += 1
            if pay_status == "paid":
                doctor_workload[doc_name]["revenue"] += amt

            # Daily trend
            daily_counts[d_str] = daily_counts.get(d_str, 0) + 1

        return {
            "start_date": start_str,
            "end_date": end_str,
            "preset": range_preset or "custom",
            "total_appointments": total_appts,
            "confirmed_count": confirmed_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,
            "pending_count": pending_count,
            "revenue_collected": revenue_collected,
            "pending_revenue": pending_revenue,
            "doctor_workload": sorted(list(doctor_workload.values()), key=lambda x: x["count"], reverse=True),
            "daily_trend": [{"date": k, "count": v} for k, v in sorted(daily_counts.items())],
        }

    def get_today_appointments(self, today_str: Optional[str] = None) -> list[dict]:
        if today_str:
            today = today_str
        else:
            now_tz = datetime.now(self._get_tz())
            today = now_tz.date().isoformat()

        records = self.patients.list_patients() if self.patients else []
        today_appts = [
            r for r in records
            if r.get("Appointment Date", "").strip() == today
        ]
        # Sort by appointment time
        today_appts.sort(key=lambda r: r.get("Appointment Time", ""))
        return today_appts

    def get_recent_patients(self, limit: int = 5) -> list[dict]:
        records = self.patients.list_patients() if self.patients else []
        # Reverse to get newest rows first
        unique = {}
        for r in reversed(records):
            pid = r.get("Patient ID") or r.get("Phone", "")
            if pid and pid not in unique:
                unique[pid] = r
            if len(unique) >= limit:
                break
        return list(unique.values())

    # ------------------------------------------------------------------
    # PATIENTS
    # ------------------------------------------------------------------

    def list_patients(self, search: str = "", page: int = 1, page_size: int = 10) -> dict:
        records = self.patients.list_patients() if self.patients else []

        # Deduplicate/aggregate into distinct patients
        patients_map = {}
        for r in records:
            pid = r.get("Patient ID", "").strip()
            if not pid:
                continue
            if pid not in patients_map:
                patients_map[pid] = {
                    "patient_id": pid,
                    "name": r.get("Name", "").strip(),
                    "email": r.get("Email", "").strip(),
                    "phone": r.get("Phone", "").strip(),
                    "age": r.get("Age", "").strip(),
                    "gender": r.get("Gender", "").strip(),
                    "status": r.get("Status", "Active").strip() if r.get("Status") in ("Active", "Inactive") else "Active",
                    "appointment_count": 0,
                    "last_appointment_date": "",
                    "last_doctor": "",
                    "created_at": r.get("Created At", ""),
                }
            patients_map[pid]["appointment_count"] += 1
            appt_date = r.get("Appointment Date", "")
            if appt_date and (not patients_map[pid]["last_appointment_date"] or appt_date > patients_map[pid]["last_appointment_date"]):
                patients_map[pid]["last_appointment_date"] = appt_date
                patients_map[pid]["last_doctor"] = r.get("Doctor", "")

        patient_list = list(patients_map.values())

        # Search filter
        if search:
            q = search.casefold().strip()
            patient_list = [
                p for p in patient_list
                if (
                    q in p["name"].casefold()
                    or q in p["phone"].casefold()
                    or q in p["email"].casefold()
                    or q in p["patient_id"].casefold()
                )
            ]

        # Sort by last appointment date descending
        patient_list.sort(key=lambda p: p["last_appointment_date"] or p["created_at"], reverse=True)

        total = len(patient_list)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "patients": patient_list[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_patient(self, patient_id: str) -> Optional[dict]:
        records = self.patients.list_patients() if self.patients else []
        patient_records = [r for r in records if r.get("Patient ID", "").strip() == patient_id.strip()]
        if not patient_records:
            return None
        latest = patient_records[-1]

        # Calculate totals
        total_billed = 0.0
        total_paid = 0.0
        for a in patient_records:
            amt_str = a.get("Amount", "").replace("₹", "").replace(",", "").strip()
            try:
                amt = float(amt_str)
            except (ValueError, TypeError):
                amt = 0.0
            total_billed += amt
            if a.get("Payment Status", "").strip().casefold() == "paid":
                total_paid += amt

        return {
            "patient_id": patient_id,
            "name": latest.get("Name", ""),
            "email": latest.get("Email", ""),
            "phone": latest.get("Phone", ""),
            "age": latest.get("Age", ""),
            "gender": latest.get("Gender", ""),
            "status": latest.get("Status", "Active") if latest.get("Status") in ("Active", "Inactive") else "Active",
            "appointments": patient_records,
            "appointment_count": len(patient_records),
            "total_billed": total_billed,
            "total_paid": total_paid,
            "pending_balance": max(0.0, total_billed - total_paid),
        }

    def check_patient_duplicates(self, phone: str = "", email: str = "") -> dict:
        """Find existing patients matching phone or email."""
        records = self.patients.list_patients() if self.patients else []
        clean_phone = phone.strip()
        clean_email = email.strip().casefold()

        duplicates = []
        seen_ids = set()

        for r in records:
            pid = r.get("Patient ID", "").strip()
            if not pid or pid in seen_ids:
                continue

            r_phone = r.get("Phone", "").strip()
            r_email = r.get("Email", "").strip().casefold()

            phone_match = bool(clean_phone and r_phone == clean_phone)
            email_match = bool(clean_email and r_email == clean_email)

            if phone_match or email_match:
                seen_ids.add(pid)
                duplicates.append({
                    "patient_id": pid,
                    "name": r.get("Name", "").strip(),
                    "phone": r_phone,
                    "email": r.get("Email", "").strip(),
                    "match_type": "phone" if phone_match else "email",
                })

        return {
            "has_duplicates": len(duplicates) > 0,
            "duplicates": duplicates,
        }

    def create_patient(self, data: dict, admin_user: str = "admin") -> dict:
        from app.tools.patients import PatientRecord
        rec = PatientRecord(
            name=data.get("name", "").strip(),
            phone=data.get("phone", "").strip(),
            email=data.get("email", "").strip(),
            age=str(data.get("age", "")).strip(),
            gender=data.get("gender", "").strip(),
            doctor=data.get("doctor", "").strip(),
            appointment_date=data.get("appointment_date", "").strip(),
            appointment_time=data.get("appointment_time", "").strip(),
            amount=str(data.get("amount", "")).strip(),
            payment_method=data.get("payment_method", "Offline").strip(),
            payment_status=data.get("payment_status", "Pending").strip(),
            booking_status=data.get("booking_status", "Confirmed").strip(),
            patient_id=data.get("patient_id", "").strip(),
        )
        created = self.patients.create_patient(rec)
        p_id = created.get("patient_id") if isinstance(created, dict) else getattr(created, "patient_id", "")
        self.audit.record(
            user=admin_user,
            action="PATIENT_CREATE",
            entity_type="patient",
            entity_id=p_id,
            details={"name": rec.name, "phone": rec.phone, "email": rec.email},
        )
        return created

    def create_patient_with_dedup(self, data: dict, force: bool = False, admin_user: str = "admin") -> dict:
        """Create patient checking for duplicates unless force is True."""
        if not force:
            dup_check = self.check_patient_duplicates(
                phone=data.get("phone", ""),
                email=data.get("email", ""),
            )
            if dup_check["has_duplicates"]:
                return {
                    "success": False,
                    "duplicate_detected": True,
                    "message": "A patient with this phone or email already exists.",
                    "duplicates": dup_check["duplicates"],
                }

        res = self.create_patient(data, admin_user=admin_user)
        return {"success": True, "patient": res}

    def update_patient(self, patient_id: str, updates: dict, admin_user: str = "admin") -> dict:
        res = self.patients.update_patient_details(patient_id, updates)
        if isinstance(res, dict) and res.get("success"):
            self.audit.record(
                user=admin_user,
                action="PATIENT_UPDATE",
                entity_type="patient",
                entity_id=patient_id,
                details=updates,
            )
        return res

    def deactivate_patient(self, patient_id: str, admin_user: str = "admin") -> dict:
        """Soft-deactivate a patient without destroying historical visit data."""
        patient = self.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found")

        res = self.patients.update_patient_details(patient_id, {"Status": "Inactive"})
        success = res.get("success", False) if isinstance(res, dict) else bool(res)
        if not success:
            raise RuntimeError(f"Failed to deactivate patient '{patient_id}'")

        self.audit.record(
            user=admin_user,
            action="PATIENT_DEACTIVATE",
            entity_type="patient",
            entity_id=patient_id,
            details={"name": patient.get("name"), "status": "Inactive"},
        )
        return {
            "success": True,
            "patient_id": patient_id,
            "status": "Inactive",
            "message": f"Patient '{patient_id}' has been deactivated.",
        }

    def get_patient_appointments(self, patient_id: str) -> list[dict]:
        records = self.patients.list_patients() if self.patients else []
        return [r for r in records if r.get("Patient ID", "").strip() == patient_id.strip()]

    def get_patient_payments(self, patient_id: str) -> list[dict]:
        appts = self.get_patient_appointments(patient_id)
        payments = []
        for a in appts:
            payments.append({
                "patient_id": a.get("Patient ID", ""),
                "patient_name": a.get("Name", ""),
                "token_no": a.get("Token No", ""),
                "appointment_date": a.get("Appointment Date", ""),
                "doctor": a.get("Doctor", ""),
                "amount": a.get("Amount", ""),
                "payment_method": a.get("Payment Method", "Offline"),
                "payment_status": a.get("Payment Status", "Pending"),
            })
        return payments

    # ------------------------------------------------------------------
    # DOCTORS
    # ------------------------------------------------------------------

    def list_doctors(self, search: str = "", active_only: bool = False) -> list[dict]:
        doctors = self.doctors.get_doctors() if self.doctors else []
        if active_only:
            doctors = [d for d in doctors if d.get("Status", "").strip().casefold() not in ("inactive", "disabled")]
        if search:
            q = search.casefold().strip()
            doctors = [
                d for d in doctors
                if (
                    q in d.get("Doctor Name", "").casefold()
                    or q in d.get("Specialization", "").casefold()
                    or q in d.get("Doctor ID", "").casefold()
                )
            ]
        return doctors

    def get_doctor(self, doctor_id: str) -> Optional[dict]:
        if not self.doctors:
            return None
        return self.doctors.get_doctor_by_id(doctor_id)

    def create_doctor(self, data: dict, admin_user: str = "admin") -> dict:
        created = self.doctors.add_doctor(data)
        doc_id = created.get("Doctor ID", "") if isinstance(created, dict) else ""
        self.audit.record(
            user=admin_user,
            action="DOCTOR_CREATE",
            entity_type="doctor",
            entity_id=doc_id,
            details=data,
        )
        return created

    def update_doctor(self, doctor_id: str, updates: dict, admin_user: str = "admin") -> Optional[dict]:
        updated = self.doctors.update_doctor(doctor_id, updates)
        if updated:
            self.audit.record(
                user=admin_user,
                action="DOCTOR_UPDATE",
                entity_type="doctor",
                entity_id=doctor_id,
                details=updates,
            )
        return updated

    def check_doctor_deactivation_safety(self, doctor_id: str, today_str: Optional[str] = None) -> dict:
        """Verify if doctor has upcoming active appointments before deactivation."""
        doc = self.get_doctor(doctor_id)
        if not doc:
            raise ValueError(f"Doctor '{doctor_id}' not found")

        doc_name = doc.get("Doctor Name", "")
        today = today_str or datetime.now(self._get_tz()).date().isoformat()

        records = self.patients.list_patients() if self.patients else []
        active_appts = []
        for r in records:
            if doc_name.casefold() in r.get("Doctor", "").casefold():
                d = r.get("Appointment Date", "").strip()
                status = (r.get("Booking Status") or r.get("Status", "")).strip().casefold()
                if d >= today and status in ("confirmed", "pending"):
                    active_appts.append({
                        "token_no": r.get("Token No"),
                        "patient_name": r.get("Name"),
                        "date": d,
                        "time": r.get("Appointment Time"),
                        "status": r.get("Booking Status") or r.get("Status"),
                    })

        return {
            "safe_to_deactivate": len(active_appts) == 0,
            "upcoming_appointments_count": len(active_appts),
            "upcoming_appointments": active_appts,
            "doctor_id": doctor_id,
            "doctor_name": doc_name,
        }

    def set_doctor_status(self, doctor_id: str, status: str, admin_user: str = "admin") -> bool:
        """Activate or deactivate a doctor."""
        success = self.doctors.set_doctor_status(doctor_id, status)
        if success:
            self.audit.record(
                user=admin_user,
                action="DOCTOR_STATUS_CHANGE",
                entity_type="doctor",
                entity_id=doctor_id,
                details={"status": status},
            )
        return success

    def get_doctor_availability(self, doctor_id: str, from_date: Optional[str] = None) -> list[dict]:
        if not self.slots:
            return []
        res = self.slots.get_upcoming_available_slots(doctor_id=doctor_id, from_date=from_date)
        return res.get("slots", []) if isinstance(res, dict) else res

    # ------------------------------------------------------------------
    # APPOINTMENTS
    # ------------------------------------------------------------------

    def list_appointments(
        self,
        search: str = "",
        date_filter: str = "",
        doctor_filter: str = "",
        status_filter: str = "",
        payment_status_filter: str = "",
        page: int = 1,
        page_size: int = 15,
    ) -> dict:
        records = self.patients.list_patients() if self.patients else []

        appointments = []
        for r in records:
            if not r.get("Appointment Date") and not r.get("Token No"):
                continue

            app = {
                "appointment_id": r.get("Token No") or r.get("Patient ID", ""),
                "token_no": r.get("Token No", ""),
                "patient_id": r.get("Patient ID", ""),
                "patient_name": r.get("Name", ""),
                "phone": r.get("Phone", ""),
                "email": r.get("Email", ""),
                "doctor": r.get("Doctor", ""),
                "date": r.get("Appointment Date", ""),
                "time": r.get("Appointment Time", ""),
                "status": r.get("Booking Status") or r.get("Status", "Confirmed"),
                "amount": r.get("Amount", ""),
                "payment_method": r.get("Payment Method", "Offline"),
                "payment_status": r.get("Payment Status", "Pending"),
                "created_at": r.get("Created At", ""),
            }
            appointments.append(app)

        # Filters
        if search:
            q = search.casefold().strip()
            appointments = [
                a for a in appointments
                if (
                    q in a["patient_name"].casefold()
                    or q in a["phone"].casefold()
                    or q in a["token_no"].casefold()
                    or q in a["doctor"].casefold()
                )
            ]
        if date_filter:
            appointments = [a for a in appointments if a["date"] == date_filter]
        if doctor_filter:
            q = doctor_filter.casefold()
            appointments = [a for a in appointments if q in a["doctor"].casefold()]
        if status_filter:
            q = status_filter.casefold()
            appointments = [a for a in appointments if a["status"].casefold() == q]
        if payment_status_filter:
            q = payment_status_filter.casefold()
            appointments = [a for a in appointments if a["payment_status"].casefold() == q]

        appointments.sort(key=lambda a: (a["date"], a["time"]), reverse=True)

        total = len(appointments)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "appointments": appointments[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_appointment(self, identifier: str) -> Optional[dict]:
        records = self.patients.list_patients() if self.patients else []
        norm = identifier.strip().casefold()
        for r in records:
            if (
                r.get("Token No", "").strip().casefold() == norm
                or r.get("Patient ID", "").strip().casefold() == norm
            ):
                return {
                    "appointment_id": r.get("Token No") or r.get("Patient ID", ""),
                    "token_no": r.get("Token No", ""),
                    "patient_id": r.get("Patient ID", ""),
                    "patient_name": r.get("Name", ""),
                    "phone": r.get("Phone", ""),
                    "email": r.get("Email", ""),
                    "age": r.get("Age", ""),
                    "gender": r.get("Gender", ""),
                    "doctor": r.get("Doctor", ""),
                    "date": r.get("Appointment Date", ""),
                    "time": r.get("Appointment Time", ""),
                    "status": r.get("Booking Status") or r.get("Status", "Confirmed"),
                    "amount": r.get("Amount", ""),
                    "payment_method": r.get("Payment Method", "Offline"),
                    "payment_status": r.get("Payment Status", "Pending"),
                    "created_at": r.get("Created At", ""),
                }
        return None

    def create_appointment_manual(self, data: dict, admin_user: str = "admin") -> dict:
        """Create an appointment manually from the CRM with atomic slot booking."""
        with SlotRepository._booking_lock:
            slot_id = data.get("slot_id", "").strip()
            if not slot_id:
                raise ValueError("Slot ID is required to book an appointment")

            # 1. Validate slot exists and is available
            slot = None
            if hasattr(self.slots, "get_slot_by_id"):
                slot = self.slots.get_slot_by_id(slot_id)
            elif hasattr(self.slots, "get_slot"):
                s_res = self.slots.get_slot(slot_id)
                slot = s_res.get("slot") if isinstance(s_res, dict) else None

            if not slot:
                raise ValueError(f"Slot '{slot_id}' not found")

            if slot.get("Status", "").strip().casefold() != "available":
                raise ValueError(f"Slot '{slot_id}' is not available for booking")

            slot_date = slot.get("Date", "")
            slot_time = slot.get("Start Time", "")
            slot_doc_name = slot.get("Doctor Name", "")

            # 2. Resolve patient
            patient_id = data.get("patient_id", "").strip()
            name = data.get("name", "").strip()
            phone = data.get("phone", "").strip()
            email = data.get("email", "").strip()
            age = str(data.get("age", "")).strip()
            gender = data.get("gender", "").strip()

            if patient_id:
                existing = self.get_patient(patient_id)
                if not existing:
                    raise ValueError(f"Patient '{patient_id}' not found")
                name = name or existing.get("name", "")
                phone = phone or existing.get("phone", "")
                email = email or existing.get("email", "")
                age = age or existing.get("age", "")
                gender = gender or existing.get("gender", "")
            else:
                if not name or not phone:
                    raise ValueError("Patient Name and Phone are required")
                gen_res = self.patients.generate_patient_id()
                patient_id = gen_res.get("patient_id", "") if isinstance(gen_res, dict) else getattr(gen_res, "patient_id", "")

            # 3. Generate token
            tok_res = self.patients.generate_token()
            token_no = tok_res.get("token_no", "") if isinstance(tok_res, dict) else getattr(tok_res, "token_no", "")

            # 4. Determine amount
            amount = str(data.get("amount", "")).strip()
            if not amount:
                # Fallback to doctor's consultation fee
                doc = self.doctors.get_doctor_by_name(slot_doc_name) if hasattr(self.doctors, "get_doctor_by_name") else None
                if doc:
                    amount = doc.get("Consultation Fee", "500").strip()
                else:
                    amount = "500"

            # 5. Book slot
            book_ok = self.slots.book_slot(slot_id, patient_id, token_no)
            if not book_ok:
                raise RuntimeError(f"Failed to reserve slot '{slot_id}'. It may have just been booked.")

            # 6. Record appointment in patient sheet
            from app.tools.patients import PatientRecord
            rec = PatientRecord(
                patient_id=patient_id,
                name=name,
                phone=phone,
                email=email,
                age=age,
                gender=gender,
                doctor=slot_doc_name,
                appointment_date=slot_date,
                appointment_time=slot_time,
                token_no=token_no,
                amount=amount,
                payment_method=data.get("payment_method", "Offline").strip(),
                payment_status=data.get("payment_status", "Pending").strip(),
                booking_status=data.get("booking_status", "Confirmed").strip(),
            )

            try:
                self.patients.create_patient(rec)
            except Exception as err:
                # Rollback slot booking
                self.slots.release_slot_if_needed(slot_id, patient_id)
                raise RuntimeError(f"Failed to record appointment: {err}")

            # 7. Record audit log
            self.audit.record(
                user=admin_user,
                action="APPOINTMENT_CREATE",
                entity_type="appointment",
                entity_id=token_no,
                details={
                    "patient_id": patient_id,
                    "patient_name": name,
                    "doctor": slot_doc_name,
                    "date": slot_date,
                    "time": slot_time,
                    "slot_id": slot_id,
                    "amount": amount,
                },
            )

            return {
                "success": True,
                "appointment_id": token_no,
                "token_no": token_no,
                "patient_id": patient_id,
                "patient_name": name,
                "doctor": slot_doc_name,
                "date": slot_date,
                "time": slot_time,
                "slot_id": slot_id,
                "amount": amount,
                "status": rec.booking_status,
                "payment_status": rec.payment_status,
            }

    def update_appointment_status(self, identifier: str, new_status: str, admin_user: str = "admin") -> dict:
        current = self.get_appointment(identifier)
        if not current:
            raise ValueError(f"Appointment '{identifier}' not found")

        curr_status = current["status"].strip().title()
        target_status = new_status.strip().title()

        valid_transitions = {
            "Pending": ["Confirmed", "Completed", "Cancelled"],
            "Confirmed": ["Completed", "Cancelled", "No-Show"],
            "Completed": [],
            "Cancelled": [],
            "No-Show": [],
        }

        allowed = valid_transitions.get(curr_status, ["Confirmed", "Completed"])
        if target_status not in allowed:
            raise ValueError(
                f"Invalid status transition from '{curr_status}' to '{target_status}'. "
                f"Allowed transitions: {', '.join(allowed) if allowed else 'None (terminal status)'}."
            )

        self.patients.update_booking_status(identifier, target_status)
        self.audit.record(
            user=admin_user,
            action="APPOINTMENT_STATUS_UPDATE",
            entity_type="appointment",
            entity_id=identifier,
            details={"old_status": curr_status, "new_status": target_status},
        )
        return {"success": True, "appointment_id": identifier, "status": target_status}

    def get_patient_upcoming_appointments(self, phone_or_id: str, today_str: Optional[str] = None) -> list[dict]:
        today = today_str or datetime.now(self._get_tz()).date().isoformat()
        records = self.patients.list_patients() if self.patients else []
        query = phone_or_id.strip().casefold()

        upcoming = []
        for r in records:
            pid = r.get("Patient ID", "").strip().casefold()
            phone = r.get("Phone", "").strip().casefold()
            token = r.get("Token No", "").strip().casefold()

            if query not in (pid, phone, token):
                continue

            appt_date = r.get("Appointment Date", "").strip()
            status = (r.get("Booking Status") or r.get("Status", "")).strip()

            if status.casefold() in ("confirmed", "pending") and appt_date >= today:
                upcoming.append({
                    "appointment_id": r.get("Token No") or r.get("Patient ID", ""),
                    "token_no": r.get("Token No", ""),
                    "patient_id": r.get("Patient ID", ""),
                    "patient_name": r.get("Name", ""),
                    "phone": r.get("Phone", ""),
                    "email": r.get("Email", ""),
                    "doctor": r.get("Doctor", ""),
                    "date": appt_date,
                    "time": r.get("Appointment Time", ""),
                    "status": status,
                    "amount": r.get("Amount", ""),
                    "payment_method": r.get("Payment Method", "Offline"),
                    "payment_status": r.get("Payment Status", "Pending"),
                })

        upcoming.sort(key=lambda a: (a["date"], a["time"]))
        return upcoming

    def cancel_appointment(self, identifier: str, reason: str = "", admin_user: str = "admin") -> dict:
        with SlotRepository._booking_lock:
            appt = self.get_appointment(identifier)
            if not appt:
                raise ValueError(f"Appointment '{identifier}' not found")

            curr_status = appt["status"].strip().title()
            if curr_status == "Cancelled":
                raise ValueError("Appointment is already cancelled")
            if curr_status == "Completed":
                raise ValueError("Completed appointments cannot be cancelled")

            update_res = self.patients.update_booking_status(identifier, "Cancelled")
            if isinstance(update_res, dict) and not update_res.get("success"):
                raise RuntimeError("Failed to update appointment status to Cancelled")

            released_slot_id = None
            if self.slots:
                slot = self.slots.find_slot_by_booking(
                    token_no=appt.get("token_no"),
                    patient_id=appt.get("patient_id"),
                    doctor_name=appt.get("doctor"),
                    date=appt.get("date"),
                    start_time=appt.get("time"),
                )
                if slot and slot.get("Status", "").casefold() == "booked":
                    s_id = slot.get("Slot ID")
                    self.slots.release_slot_if_needed(s_id, appt.get("patient_id"))
                    released_slot_id = s_id

            self.audit.record(
                user=admin_user,
                action="APPOINTMENT_CANCEL",
                entity_type="appointment",
                entity_id=identifier,
                details={"reason": reason, "released_slot_id": released_slot_id},
            )

            return {
                "success": True,
                "appointment_id": identifier,
                "token_no": appt.get("token_no"),
                "status": "Cancelled",
                "released_slot_id": released_slot_id,
                "message": f"Appointment {identifier} has been successfully cancelled.",
            }

    def reschedule_appointment(
        self,
        identifier: str,
        new_slot_id: str,
        new_date: str = "",
        new_time: str = "",
        admin_user: str = "admin",
    ) -> dict:
        with SlotRepository._booking_lock:
            appt = self.get_appointment(identifier)
            if not appt:
                raise ValueError(f"Appointment '{identifier}' not found")

            curr_status = appt["status"].strip().title()
            if curr_status == "Cancelled":
                raise ValueError("Cancelled appointments cannot be rescheduled")
            if curr_status == "Completed":
                raise ValueError("Completed appointments cannot be rescheduled")

            if not self.slots:
                raise RuntimeError("Slot repository not available")

            new_slot = None
            if hasattr(self.slots, "get_slot_by_id"):
                new_slot = self.slots.get_slot_by_id(new_slot_id)
            elif hasattr(self.slots, "get_slot"):
                slot_res = self.slots.get_slot(new_slot_id)
                new_slot = slot_res.get("slot") if isinstance(slot_res, dict) else None

            if not new_slot:
                raise ValueError(f"Target slot '{new_slot_id}' not found")

            if new_slot.get("Status", "").strip().casefold() != "available":
                raise ValueError(f"Target slot '{new_slot_id}' is no longer available. Please select an open slot.")

            target_date = new_slot.get("Date") or new_date
            target_time = new_slot.get("Start Time") or new_time

            old_slot = self.slots.find_slot_by_booking(
                token_no=appt.get("token_no"),
                patient_id=appt.get("patient_id"),
                doctor_name=appt.get("doctor"),
                date=appt.get("date"),
                start_time=appt.get("time"),
            )
            old_slot_id = old_slot.get("Slot ID") if old_slot else None

            if old_slot_id and old_slot_id == new_slot_id:
                return {
                    "success": True,
                    "appointment_id": identifier,
                    "status": "unchanged",
                    "message": "Appointment is already scheduled for this slot.",
                }

            patient_id = appt.get("patient_id", "")
            token_no = appt.get("token_no", "")
            book_res = self.slots.book_slot(new_slot_id, patient_id, token_no)
            booked_ok = book_res.get("success", False) if isinstance(book_res, dict) else bool(book_res)
            if not booked_ok:
                raise RuntimeError("Failed to secure new slot. It may have just been booked by another patient.")

            update_payload = {
                "appointment_date": target_date,
                "appointment_time": target_time,
            }
            if hasattr(self.patients, "update_appointment_details"):
                upd_res = self.patients.update_appointment_details(identifier, update_payload)
                upd_ok = upd_res.get("success", False) if isinstance(upd_res, dict) else bool(upd_res)
            else:
                upd_res = self.patients.update_patient_details(patient_id, update_payload)
                upd_ok = upd_res.get("success", False) if isinstance(upd_res, dict) else bool(upd_res)

            if not upd_ok:
                self.slots.release_slot_if_needed(new_slot_id, patient_id)
                raise RuntimeError("Failed to update appointment record in clinic sheet. Reschedule aborted.")

            if old_slot_id and old_slot_id != new_slot_id:
                self.slots.release_slot_if_needed(old_slot_id, patient_id)

            self.audit.record(
                user=admin_user,
                action="APPOINTMENT_RESCHEDULE",
                entity_type="appointment",
                entity_id=identifier,
                details={
                    "old_date": appt.get("date"),
                    "old_time": appt.get("time"),
                    "new_date": target_date,
                    "new_time": target_time,
                    "new_slot_id": new_slot_id,
                },
            )

            return {
                "success": True,
                "appointment_id": identifier,
                "token_no": token_no,
                "patient_id": patient_id,
                "doctor": appt.get("doctor"),
                "old_date": appt.get("date"),
                "old_time": appt.get("time"),
                "new_date": target_date,
                "new_time": target_time,
                "old_slot_id": old_slot_id,
                "new_slot_id": new_slot_id,
                "message": f"Appointment successfully rescheduled to {target_date} at {target_time}.",
            }

    # ------------------------------------------------------------------
    # CALENDAR
    # ------------------------------------------------------------------

    def get_calendar_events(self, start_date: str, end_date: str, doctor_filter: str = "") -> list[dict]:
        records = self.patients.list_patients() if self.patients else []
        events = []
        doc_q = doctor_filter.casefold().strip()

        for r in records:
            d = r.get("Appointment Date", "").strip()
            if not d or d < start_date or d > end_date:
                continue
            doc = r.get("Doctor", "").strip()
            if doc_q and doc_q not in doc.casefold():
                continue

            events.append({
                "id": r.get("Token No") or r.get("Patient ID", ""),
                "title": f"{r.get('Name', 'Patient')} ({r.get('Token No', '')})",
                "patient_name": r.get("Name", ""),
                "doctor": doc,
                "date": d,
                "time": r.get("Appointment Time", ""),
                "status": r.get("Booking Status") or r.get("Status", "Confirmed"),
                "payment_status": r.get("Payment Status", "Pending"),
                "amount": r.get("Amount", ""),
                "token_no": r.get("Token No", ""),
            })

        events.sort(key=lambda e: (e["date"], e["time"]))
        return events

    # ------------------------------------------------------------------
    # SLOTS
    # ------------------------------------------------------------------

    def list_slots(self, date_filter: str = "", doctor_filter: str = "", status_filter: str = "") -> list[dict]:
        if not self.slots:
            return []
        res = self.slots.list_all_slots()
        slots = res.get("slots", []) if isinstance(res, dict) else res

        if date_filter:
            slots = [s for s in slots if s.get("Date") == date_filter]
        if doctor_filter:
            q = doctor_filter.casefold().strip()
            slots = [
                s for s in slots
                if q in s.get("Doctor Name", "").casefold() or q == s.get("Doctor ID", "").casefold()
            ]
        if status_filter:
            q = status_filter.casefold().strip()
            slots = [s for s in slots if s.get("Status", "").casefold() == q]

        slots.sort(key=lambda s: (s.get("Date", ""), s.get("Start Time", "")))
        return slots

    def create_slot(self, data: dict, admin_user: str = "admin") -> dict:
        if not self.slots:
            raise RuntimeError("Slot repository not available")
        created = self.slots.create_slot(data)
        s_id = created.get("Slot ID", "") if isinstance(created, dict) else ""
        self.audit.record(
            user=admin_user,
            action="SLOT_CREATE",
            entity_type="slot",
            entity_id=s_id,
            details=data,
        )
        return created

    def update_slot(self, slot_id: str, updates: dict, admin_user: str = "admin") -> dict:
        if not self.slots:
            raise RuntimeError("Slot repository not available")
        res = self.slots.update_slot(slot_id, updates)
        if isinstance(res, dict) and not res.get("success"):
            if res.get("error_code") == "SLOT_SAFETY_VIOLATION":
                raise ValueError(res.get("message", "Cannot modify actively booked slot"))
            elif res.get("error_code") == "SLOT_NOT_FOUND":
                return None
            raise RuntimeError(res.get("message", "Failed to update slot"))

        self.audit.record(
            user=admin_user,
            action="SLOT_UPDATE",
            entity_type="slot",
            entity_id=slot_id,
            details=updates,
        )
        return res.get("slot") if isinstance(res, dict) and "slot" in res else res

    def set_slot_status(self, slot_id: str, status: str, admin_user: str = "admin") -> bool:
        if not self.slots:
            raise RuntimeError("Slot repository not available")
        res = self.slots.set_slot_status(slot_id, status)
        if isinstance(res, dict) and not res.get("success"):
            if res.get("error_code") == "SLOT_SAFETY_VIOLATION":
                raise ValueError(res.get("message", "Cannot modify actively booked slot"))
            elif res.get("error_code") == "SLOT_NOT_FOUND":
                return False
            raise RuntimeError(res.get("message", "Failed to update slot status"))

        success = res.get("success", False) if isinstance(res, dict) else bool(res)
        if success:
            self.audit.record(
                user=admin_user,
                action="SLOT_STATUS_CHANGE",
                entity_type="slot",
                entity_id=slot_id,
                details={"status": status},
            )
        return success

    # ------------------------------------------------------------------
    # PAYMENTS & BILLING
    # ------------------------------------------------------------------

    def list_payments(
        self,
        status_filter: str = "",
        search: str = "",
        page: int = 1,
        page_size: int = 15,
    ) -> dict:
        records = self.patients.list_patients() if self.patients else []

        payments = []
        for r in records:
            if not r.get("Amount") and not r.get("Token No"):
                continue

            pay = {
                "payment_id": r.get("Token No") or r.get("Patient ID", ""),
                "token_no": r.get("Token No", ""),
                "patient_id": r.get("Patient ID", ""),
                "patient_name": r.get("Name", ""),
                "phone": r.get("Phone", ""),
                "doctor": r.get("Doctor", ""),
                "appointment_date": r.get("Appointment Date", ""),
                "amount": r.get("Amount", ""),
                "payment_method": r.get("Payment Method", "Offline"),
                "payment_status": r.get("Payment Status", "Pending"),
                "booking_status": r.get("Booking Status") or r.get("Status", "Confirmed"),
            }
            payments.append(pay)

        if status_filter:
            q = status_filter.casefold().strip()
            payments = [p for p in payments if p["payment_status"].casefold() == q]

        if search:
            q = search.casefold().strip()
            payments = [
                p for p in payments
                if (
                    q in p["patient_name"].casefold()
                    or q in p["phone"].casefold()
                    or q in p["token_no"].casefold()
                    or q in p["doctor"].casefold()
                )
            ]

        payments.sort(key=lambda p: p["appointment_date"], reverse=True)

        total = len(payments)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "payments": payments[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_payment(self, identifier: str) -> Optional[dict]:
        appt = self.get_appointment(identifier)
        if not appt:
            return None
        return {
            "payment_id": appt["token_no"] or appt["patient_id"],
            "token_no": appt["token_no"],
            "patient_id": appt["patient_id"],
            "patient_name": appt["patient_name"],
            "phone": appt["phone"],
            "doctor": appt["doctor"],
            "appointment_date": appt["date"],
            "amount": appt["amount"],
            "payment_method": appt["payment_method"],
            "payment_status": appt["payment_status"],
            "booking_status": appt["status"],
        }

    def update_payment_status(self, identifier: str, new_status: str, admin_user: str = "admin") -> dict:
        """Mark payment status (e.g. Pending -> Paid when collected at clinic)."""
        valid = ["Pending", "Paid"]
        formatted = new_status.strip().title()
        if formatted not in valid:
            raise ValueError(f"Invalid payment status '{new_status}'. Allowed: {', '.join(valid)}")
        self.patients.update_payment_status(identifier, formatted)
        self.audit.record(
            user=admin_user,
            action="PAYMENT_STATUS_UPDATE",
            entity_type="payment",
            entity_id=identifier,
            details={"payment_status": formatted},
        )
        return {"success": True, "identifier": identifier, "payment_status": formatted}

    def record_manual_payment(
        self,
        identifier: str,
        amount: str,
        payment_method: str = "Cash",
        transaction_ref: str = "",
        notes: str = "",
        admin_user: str = "admin",
    ) -> dict:
        """Record an offline manual payment collection for an appointment."""
        appt = self.get_appointment(identifier)
        if not appt:
            raise ValueError(f"Appointment '{identifier}' not found")

        clean_amt = amount.replace("₹", "").replace(",", "").strip()
        updates = {
            "Amount": clean_amt,
            "Payment Method": payment_method.strip(),
            "Payment Status": "Paid",
        }

        # Update in repository
        if hasattr(self.patients, "update_appointment_details"):
            self.patients.update_appointment_details(identifier, updates)
        else:
            self.patients.update_payment_status(identifier, "Paid")

        self.audit.record(
            user=admin_user,
            action="PAYMENT_RECORD",
            entity_type="payment",
            entity_id=identifier,
            details={
                "amount": clean_amt,
                "payment_method": payment_method,
                "transaction_ref": transaction_ref,
                "notes": notes,
            },
        )

        return {
            "success": True,
            "identifier": identifier,
            "amount": clean_amt,
            "payment_method": payment_method,
            "payment_status": "Paid",
            "transaction_ref": transaction_ref,
            "message": "Payment recorded successfully.",
        }

    def generate_appointment_invoice(self, identifier: str) -> dict:
        """Generate a PDF invoice for an appointment and return invoice info."""
        appt = self.get_appointment(identifier)
        if not appt:
            raise ValueError(f"Appointment '{identifier}' not found")

        # Resolve doctor info for specialization
        specialization = "General Consultation"
        if self.doctors:
            doc = self.doctors.get_doctor_by_name(appt.get("doctor", "")) if hasattr(self.doctors, "get_doctor_by_name") else None
            if doc:
                specialization = doc.get("Specialization", specialization)

        inv_data = InvoiceData(
            clinic_name=self.clinic_name,
            clinic_phone="6200126662",
            clinic_email="admin@clinic.com",
            clinic_address="Clinic Medical Plaza, Suite 101",
            patient_name=appt.get("patient_name", "Patient"),
            patient_email=appt.get("email", ""),
            patient_phone=appt.get("phone", ""),
            doctor_name=appt.get("doctor", ""),
            specialization=specialization,
            appointment_date=appt.get("date", ""),
            appointment_time=appt.get("time", ""),
            token_no=appt.get("token_no", identifier),
            amount=f"₹{appt.get('amount', '500')}",
            payment_method=appt.get("payment_method", "Offline"),
            payment_status=appt.get("payment_status", "Pending"),
        )

        out_dir = Path(__file__).resolve().parents[2] / "data" / "invoices"
        inv_no, path = generate_invoice(inv_data, out_dir)

        return {
            "success": True,
            "invoice_number": inv_no,
            "file_path": str(path),
        }

    # ------------------------------------------------------------------
    # REPORTS & EXPORTS (WITH FORMULA INJECTION SANITIZATION)
    # ------------------------------------------------------------------

    def export_report_csv(
        self,
        report_type: str,
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        """Export sanitized CSV report (neutralizes formula injection)."""
        output = io.StringIO()
        writer = csv.writer(output)

        report_type_clean = report_type.strip().lower()

        if report_type_clean == "appointments":
            writer.writerow([
                "Token No", "Patient ID", "Patient Name", "Phone", "Email",
                "Doctor", "Appointment Date", "Appointment Time", "Status",
                "Amount", "Payment Method", "Payment Status", "Created At"
            ])
            records = self.patients.list_patients() if self.patients else []
            for r in records:
                d = r.get("Appointment Date", "").strip()
                if start_date and d and d < start_date:
                    continue
                if end_date and d and d > end_date:
                    continue
                if not d and not r.get("Token No"):
                    continue

                row = [
                    sanitize_csv_field(r.get("Token No")),
                    sanitize_csv_field(r.get("Patient ID")),
                    sanitize_csv_field(r.get("Name")),
                    sanitize_csv_field(r.get("Phone")),
                    sanitize_csv_field(r.get("Email")),
                    sanitize_csv_field(r.get("Doctor")),
                    sanitize_csv_field(r.get("Appointment Date")),
                    sanitize_csv_field(r.get("Appointment Time")),
                    sanitize_csv_field(r.get("Booking Status") or r.get("Status")),
                    sanitize_csv_field(r.get("Amount")),
                    sanitize_csv_field(r.get("Payment Method")),
                    sanitize_csv_field(r.get("Payment Status")),
                    sanitize_csv_field(r.get("Created At")),
                ]
                writer.writerow(row)

        elif report_type_clean == "patients":
            writer.writerow([
                "Patient ID", "Name", "Phone", "Email", "Age", "Gender",
                "Total Appointments", "Last Appointment Date", "Last Doctor", "Status"
            ])
            patient_data = self.list_patients(page=1, page_size=10000)
            for p in patient_data.get("patients", []):
                row = [
                    sanitize_csv_field(p.get("patient_id")),
                    sanitize_csv_field(p.get("name")),
                    sanitize_csv_field(p.get("phone")),
                    sanitize_csv_field(p.get("email")),
                    sanitize_csv_field(p.get("age")),
                    sanitize_csv_field(p.get("gender")),
                    sanitize_csv_field(p.get("appointment_count")),
                    sanitize_csv_field(p.get("last_appointment_date")),
                    sanitize_csv_field(p.get("last_doctor")),
                    sanitize_csv_field(p.get("status", "Active")),
                ]
                writer.writerow(row)

        elif report_type_clean == "payments":
            writer.writerow([
                "Transaction / Token", "Patient ID", "Patient Name", "Phone",
                "Doctor", "Appointment Date", "Amount", "Payment Method",
                "Payment Status", "Booking Status"
            ])
            pay_data = self.list_payments(page=1, page_size=10000)
            for p in pay_data.get("payments", []):
                d = p.get("appointment_date", "").strip()
                if start_date and d and d < start_date:
                    continue
                if end_date and d and d > end_date:
                    continue

                row = [
                    sanitize_csv_field(p.get("token_no") or p.get("payment_id")),
                    sanitize_csv_field(p.get("patient_id")),
                    sanitize_csv_field(p.get("patient_name")),
                    sanitize_csv_field(p.get("phone")),
                    sanitize_csv_field(p.get("doctor")),
                    sanitize_csv_field(p.get("appointment_date")),
                    sanitize_csv_field(p.get("amount")),
                    sanitize_csv_field(p.get("payment_method")),
                    sanitize_csv_field(p.get("payment_status")),
                    sanitize_csv_field(p.get("booking_status")),
                ]
                writer.writerow(row)
        else:
            raise ValueError(f"Unknown report type '{report_type}'. Allowed: appointments, patients, payments")

        return output.getvalue()
