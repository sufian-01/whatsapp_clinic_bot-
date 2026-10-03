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
        gmail_tools=None,
        audit_service: Optional[AuditService] = None,
        clinic_name: str = "Clinic",
        clinic_timezone: str = "Asia/Kolkata",
        support_phone: str = "",
        doctor_accounts=None,
        prescriptions=None,
    ) -> None:
        self.patients = patients_tools
        self.doctors = doctors_tools
        self.slots = slots_tools
        self.payments = payments_tools
        self.invoices = invoices_tools
        self.gmail = gmail_tools
        self.audit = audit_service or AuditService()
        self.clinic_name = clinic_name
        self.clinic_timezone = clinic_timezone
        self.support_phone = support_phone

        if doctor_accounts is not None:
            self.doctor_accounts = doctor_accounts
        else:
            from .doctor_account_service import DoctorAccountService
            self.doctor_accounts = DoctorAccountService(
                doctor_directory=self.doctors,
                audit_service=self.audit,
            )

        if prescriptions is not None:
            self.prescriptions = prescriptions
        else:
            from .prescription_service import PrescriptionService
            self.prescriptions = PrescriptionService(audit_service=self.audit)

    def invalidate_patients_cache(self) -> None:
        """Invalidate the patient sheet cache."""
        if self.patients and hasattr(self.patients, "invalidate_cache"):
            self.patients.invalidate_cache()

    def invalidate_doctors_cache(self) -> None:
        """Invalidate the doctor directory cache."""
        if self.doctors and hasattr(self.doctors, "invalidate_cache"):
            self.doctors.invalidate_cache()

    def invalidate_slots_cache(self) -> None:
        """Invalidate the appointment slot sheet cache."""
        if self.slots and hasattr(self.slots, "invalidate_cache"):
            self.slots.invalidate_cache()

    def invalidate_all_caches(self) -> None:
        """Invalidate all sheet-backed in-memory caches."""
        self.invalidate_patients_cache()
        self.invalidate_doctors_cache()
        self.invalidate_slots_cache()

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
        self.invalidate_patients_cache()
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
        self.invalidate_patients_cache()
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
        self.invalidate_patients_cache()
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
        # Pre-fetch appointments once to prevent O(N) Sheet roundtrips
        try:
            res = self.list_appointments(page_size=10000)
            all_appts = res.get("appointments", [])
        except Exception:
            all_appts = []

        # Pre-fetch all prescriptions once
        all_rxs = []
        if self.prescriptions:
            try:
                all_rxs = self.prescriptions.list_prescriptions()
            except Exception:
                all_rxs = []

        rx_counts: dict[str, int] = {}
        for r in all_rxs:
            if r.get("status") in ("finalized", "amended"):
                d_id = str(r.get("doctor_id", "")).strip().casefold()
                if d_id:
                    rx_counts[d_id] = rx_counts.get(d_id, 0) + 1

        enhanced = []
        for d in doctors:
            item = dict(d)
            doc_id = str(item.get("Doctor ID", "")).strip()
            doc_name = str(item.get("Doctor Name", "")).strip()
            norm_name = doc_name.casefold()
            norm_id = doc_id.casefold()

            matching_appts = sum(
                1 for a in all_appts
                if (norm_name and norm_name in a.get("doctor", "").casefold())
                or (norm_id and norm_id == a.get("doctor_id", "").casefold())
            )
            item["assigned_appointments_count"] = matching_appts
            item["completed_prescriptions_count"] = rx_counts.get(norm_id, 0)
            enhanced.append(item)
        return enhanced

    def get_doctor(self, doctor_id: str) -> Optional[dict]:
        if not self.doctors:
            return None
        doc = self.doctors.get_doctor_by_id(doctor_id)
        if not doc:
            return None
        doc_dict = dict(doc)
        try:
            appts = self.get_doctor_appointments(doctor_id)
            doc_dict["assigned_appointments_count"] = len(appts)
        except Exception:
            doc_dict["assigned_appointments_count"] = 0

        rx_count = 0
        if self.prescriptions:
            try:
                rxs = self.prescriptions.list_prescriptions(doctor_id=doctor_id)
                rx_count = len([r for r in rxs if r.get("status") in ("finalized", "amended")])
            except Exception:
                rx_count = 0
        doc_dict["completed_prescriptions_count"] = rx_count
        return doc_dict

    def create_doctor(self, data: dict, admin_user: str = "admin") -> dict:
        created = self.doctors.add_doctor(data)
        self.invalidate_doctors_cache()
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
            self.invalidate_doctors_cache()
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
            self.invalidate_doctors_cache()
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
            self.invalidate_patients_cache()
            self.invalidate_slots_cache()

            # 8. Send confirmation email
            email_result = {"email_sent": False, "skipped": True, "reason": "No email service"}
            if self.gmail and email:
                email_result = self.gmail.send_appointment_confirmation_email(
                    recipient=email,
                    appointment_data={
                        "patient_name": name,
                        "doctor": slot_doc_name,
                        "specialization": slot.get("Specialization", ""),
                        "date": slot_date,
                        "time": slot_time,
                        "token_no": token_no,
                        "amount": amount,
                        "payment_status": rec.payment_status,
                    },
                    clinic_name=self.clinic_name,
                    support_phone=getattr(self, 'support_phone', ''),
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
                "email_result": email_result,
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
        self.invalidate_patients_cache()
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
            self.invalidate_patients_cache()
            self.invalidate_slots_cache()

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
            self.invalidate_patients_cache()
            self.invalidate_slots_cache()

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
        self.invalidate_slots_cache()
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

        self.invalidate_slots_cache()
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
            self.invalidate_slots_cache()
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
        self.invalidate_patients_cache()

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

    # ------------------------------------------------------------------
    # DOCTOR PORTAL & CLINICAL WORKFLOW METHODS
    # ------------------------------------------------------------------

    def _parse_time_minutes(self, time_str: str) -> int:
        """Parse time string to minutes from midnight (handles 12h and 24h formats)."""
        clean = time_str.strip().upper()
        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"):
            try:
                dt = datetime.strptime(clean, fmt)
                return dt.hour * 60 + dt.minute
            except ValueError:
                pass
        m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)?$", clean)
        if m:
            h = int(m.group(1))
            mins = int(m.group(2))
            meridiem = m.group(3)
            if meridiem == "PM" and h < 12:
                h += 12
            elif meridiem == "AM" and h == 12:
                h = 0
            return h * 60 + mins
        raise ValueError(f"Invalid time format: '{time_str}'")

    def _get_doctor_name_by_id(self, doctor_id: str) -> str:
        """Resolve canonical doctor name from Doctor Directory or account."""
        if self.doctors and hasattr(self.doctors, "get_doctor_by_id"):
            doc = self.doctors.get_doctor_by_id(doctor_id)
            if doc:
                return doc.get("Doctor Name", "")
        # Fallback to doctor accounts
        if self.doctor_accounts:
            acc = self.doctor_accounts.get_account_by_doctor_id(doctor_id)
            if acc:
                return acc.get("doctor_name", "")
        return ""

    def get_doctor_slots(self, doctor_id: str, date_filter: str = "", status_filter: str = "") -> list[dict]:
        """Fetch slots belonging strictly to the specified doctor ID."""
        doc_name = self._get_doctor_name_by_id(doctor_id)
        all_slots = self.list_slots(date_filter=date_filter, status_filter=status_filter)
        norm_id = doctor_id.strip().casefold()
        norm_name = doc_name.strip().casefold()

        doc_slots = [
            s for s in all_slots
            if (s.get("Doctor ID", "").strip().casefold() == norm_id)
            or (norm_name and s.get("Doctor Name", "").strip().casefold() == norm_name)
        ]
        return doc_slots

    def create_doctor_slot(
        self,
        doctor_id: str,
        date_val: str,
        start_time: str,
        end_time: str,
        user: str = "doctor",
    ) -> dict:
        """Create a new available slot strictly for the logged-in doctor with safety checks."""
        # 1. Validate date format
        try:
            slot_d = date.fromisoformat(date_val.strip())
        except ValueError:
            raise ValueError("Date must be formatted as YYYY-MM-DD.")

        # 2. Parse and validate times
        start_min = self._parse_time_minutes(start_time)
        end_min = self._parse_time_minutes(end_time)

        if start_min >= end_min:
            raise ValueError(f"Start time ({start_time}) must be strictly earlier than end time ({end_time}).")

        duration = end_min - start_min
        if duration < 10 or duration > 180:
            raise ValueError(f"Slot duration ({duration} mins) must be between 10 and 180 minutes.")

        # Working hours validation: 08:00 AM (480 mins) to 09:00 PM (1260 mins)
        if start_min < 480 or end_min > 1260:
            raise ValueError("Slots can only be scheduled within clinic operating hours (08:00 AM to 09:00 PM).")

        # 3. Prevent past slots
        now_tz = datetime.now(self._get_tz())
        today = now_tz.date()
        current_min = now_tz.hour * 60 + now_tz.minute

        if slot_d < today or (slot_d == today and start_min < current_min):
            raise ValueError("Cannot create appointment slots in the past.")

        # 4. Overlap check with doctor's existing slots on that date
        existing_slots = self.get_doctor_slots(doctor_id, date_filter=date_val)
        for s in existing_slots:
            s_status = s.get("Status", "").strip().casefold()
            if s_status in ("cancelled", "unavailable", "disabled"):
                continue
            try:
                exist_s_min = self._parse_time_minutes(s.get("Start Time", ""))
                exist_e_min = self._parse_time_minutes(s.get("End Time", ""))
                if max(start_min, exist_s_min) < min(end_min, exist_e_min):
                    raise ValueError(
                        f"Slot time {start_time} - {end_time} overlaps with existing slot "
                        f"'{s.get('Slot ID')}' ({s.get('Start Time')} - {s.get('End Time')})."
                    )
            except ValueError as err:
                if "overlaps" in str(err):
                    raise
                continue

        # 5. Resolve doctor name
        doc_name = self._get_doctor_name_by_id(doctor_id)
        if not doc_name:
            doc_name = f"Doctor {doctor_id}"

        # 6. Create slot under booking lock
        with SlotRepository._booking_lock:
            payload = {
                "doctor_id": doctor_id.strip(),
                "Doctor ID": doctor_id.strip(),
                "doctor_name": doc_name.strip(),
                "Doctor Name": doc_name.strip(),
                "date": date_val.strip(),
                "Date": date_val.strip(),
                "start_time": start_time.strip(),
                "Start Time": start_time.strip(),
                "end_time": end_time.strip(),
                "End Time": end_time.strip(),
                "status": "Available",
                "Status": "Available",
            }
            created = self.create_slot(payload, admin_user=user)

        self.audit.record(
            user=user,
            action="DOCTOR_SLOT_CREATE",
            entity_type="slot",
            entity_id=created.get("Slot ID", ""),
            details=payload,
        )
        return created

    def update_doctor_slot(
        self,
        slot_id: str,
        doctor_id: str,
        updates: dict,
        user: str = "doctor",
    ) -> dict:
        """Update doctor's own slot with booked-slot protection and overlap validation."""
        with SlotRepository._booking_lock:
            all_slots = self.slots.list_all_slots() if self.slots else []
            slot = next((s for s in all_slots if s.get("Slot ID") == slot_id), None)
            if not slot:
                raise ValueError(f"Slot '{slot_id}' not found.")

            # Isolation check: slot must belong to this doctor
            doc_name = self._get_doctor_name_by_id(doctor_id)
            slot_doc_id = slot.get("Doctor ID", "").strip().casefold()
            slot_doc_name = slot.get("Doctor Name", "").strip().casefold()
            norm_id = doctor_id.strip().casefold()
            norm_name = doc_name.strip().casefold()

            if slot_doc_id != norm_id and (not norm_name or slot_doc_name != norm_name):
                raise PermissionError("Access forbidden: You cannot modify another physician's slots.")

            slot_status = slot.get("Status", "").strip().casefold()

            # Booked slot protection
            if slot_status == "booked":
                if any(k in updates for k in ("start_time", "end_time", "date", "Start Time", "End Time", "Date")):
                    raise ValueError(
                        "Cannot modify the date or time of an actively booked slot. Reschedule the appointment instead."
                    )
                new_status = updates.get("status", updates.get("Status", "")).strip().casefold()
                if new_status and new_status != "booked":
                    raise ValueError(
                        "Cannot mark a booked slot as unavailable. Reschedule or cancel the appointment first."
                    )

            # If modifying available slot time/date, validate overlap & past time
            target_date = updates.get("date", updates.get("Date", slot.get("Date", "")))
            target_start = updates.get("start_time", updates.get("Start Time", slot.get("Start Time", "")))
            target_end = updates.get("end_time", updates.get("End Time", slot.get("End Time", "")))

            if any(k in updates for k in ("start_time", "end_time", "date", "Start Time", "End Time", "Date")):
                start_min = self._parse_time_minutes(target_start)
                end_min = self._parse_time_minutes(target_end)
                if start_min >= end_min:
                    raise ValueError(f"Start time ({target_start}) must be earlier than end time ({target_end}).")

                # Past date check
                now_tz = datetime.now(self._get_tz())
                today = now_tz.date()
                slot_d = date.fromisoformat(target_date)
                current_min = now_tz.hour * 60 + now_tz.minute
                if slot_d < today or (slot_d == today and start_min < current_min):
                    raise ValueError("Cannot schedule appointment slots in the past.")

                # Overlap check against doctor's other slots
                existing = self.get_doctor_slots(doctor_id, date_filter=target_date)
                for other in existing:
                    if other.get("Slot ID") == slot_id:
                        continue
                    if other.get("Status", "").strip().casefold() in ("cancelled", "unavailable", "disabled"):
                        continue
                    o_s_min = self._parse_time_minutes(other.get("Start Time", ""))
                    o_e_min = self._parse_time_minutes(other.get("End Time", ""))
                    if max(start_min, o_s_min) < min(end_min, o_e_min):
                        raise ValueError(
                            f"Updated time overlaps with slot '{other.get('Slot ID')}' "
                            f"({other.get('Start Time')} - {other.get('End Time')})."
                        )

            updated = self.update_slot(slot_id, updates, admin_user=user)

        self.audit.record(
            user=user,
            action="DOCTOR_SLOT_UPDATE",
            entity_type="slot",
            entity_id=slot_id,
            details=updates,
        )
        return updated

    def delete_doctor_slot(self, slot_id: str, doctor_id: str, user: str = "doctor") -> dict:
        """Mark slot unavailable or delete with booked-slot protection."""
        with SlotRepository._booking_lock:
            all_slots = self.slots.list_all_slots() if self.slots else []
            slot = next((s for s in all_slots if s.get("Slot ID") == slot_id), None)
            if not slot:
                raise ValueError(f"Slot '{slot_id}' not found.")

            doc_name = self._get_doctor_name_by_id(doctor_id)
            slot_doc_id = slot.get("Doctor ID", "").strip().casefold()
            slot_doc_name = slot.get("Doctor Name", "").strip().casefold()
            norm_id = doctor_id.strip().casefold()
            norm_name = doc_name.strip().casefold()

            if slot_doc_id != norm_id and (not norm_name or slot_doc_name != norm_name):
                raise PermissionError("Access forbidden: You cannot delete another physician's slots.")

            if slot.get("Status", "").strip().casefold() == "booked":
                raise RuntimeError("A booked slot cannot be deleted without handling the associated appointment.")

            self.update_slot(slot_id, {"status": "Unavailable"}, admin_user=user)

        self.audit.record(
            user=user,
            action="DOCTOR_SLOT_DELETE",
            entity_type="slot",
            entity_id=slot_id,
            details={"status": "Unavailable"},
        )
        return {"success": True, "slot_id": slot_id, "message": "Slot has been marked unavailable."}

    def get_doctor_appointments(
        self,
        doctor_id: str,
        date_filter: str = "",
        status_filter: str = "",
        search: str = "",
    ) -> list[dict]:
        """List appointments assigned strictly to the specified doctor."""
        doc_name = self._get_doctor_name_by_id(doctor_id)
        res = self.list_appointments(page_size=10000)
        all_appts = res.get("appointments", [])

        norm_name = doc_name.strip().casefold()
        norm_id = doctor_id.strip().casefold()

        # Strict isolation filter
        doc_appts = [
            a for a in all_appts
            if (norm_name and norm_name in a.get("doctor", "").casefold())
            or (norm_id and norm_id == a.get("doctor_id", "").casefold())
        ]

        if date_filter:
            doc_appts = [a for a in doc_appts if a.get("date") == date_filter]
        if status_filter:
            q = status_filter.casefold().strip()
            doc_appts = [a for a in doc_appts if a.get("status", "").casefold() == q]
        if search:
            q = search.casefold().strip()
            doc_appts = [
                a for a in doc_appts
                if (
                    q in a.get("patient_name", "").casefold()
                    or q in a.get("phone", "").casefold()
                    or q in a.get("token_no", "").casefold()
                )
            ]

        # Attach prescription info if available
        if self.prescriptions:
            for a in doc_appts:
                tkn = a.get("token_no") or a.get("appointment_id", "")
                rx = self.prescriptions.get_prescription_by_appointment(tkn)
                a["has_prescription"] = rx is not None
                a["prescription_id"] = rx.get("prescription_id") if rx else None
                a["prescription_status"] = rx.get("status") if rx else None

        doc_appts.sort(key=lambda a: (a.get("date", ""), a.get("time", "")), reverse=True)
        return doc_appts

    def get_doctor_appointment(self, appointment_id: str, doctor_id: str) -> dict:
        """Fetch details of an appointment assigned to the doctor, with clinical history."""
        appt = self.get_appointment(appointment_id)
        if not appt:
            raise ValueError(f"Appointment '{appointment_id}' not found.")

        doc_name = self._get_doctor_name_by_id(doctor_id)
        norm_name = doc_name.strip().casefold()
        norm_id = doctor_id.strip().casefold()
        appt_doc = appt.get("doctor", "").strip().casefold()

        if (not norm_name or norm_name not in appt_doc) and (norm_id != appt.get("doctor_id", "").casefold()):
            raise PermissionError("Access forbidden: You cannot access another physician's patient records.")

        # Attach previous visits with this doctor
        patient_id = appt.get("patient_id")
        history = []
        if patient_id:
            all_visits = self.get_doctor_appointments(doctor_id)
            history = [v for v in all_visits if v.get("patient_id") == patient_id and v.get("appointment_id") != appointment_id]

        # Attach prescription if available
        rx = None
        if self.prescriptions:
            rx = self.prescriptions.get_prescription_by_appointment(appt.get("token_no") or appointment_id)

        appt_detail = dict(appt)
        appt_detail["history"] = history
        appt_detail["prescription"] = rx
        return appt_detail

    def get_doctor_patients(
        self,
        doctor_id: str,
        search: str = "",
        require_verified_payment: bool = False,
    ) -> list[dict]:
        """Fetch patients assigned to this doctor, enforcing payment rules if required."""
        appts = self.get_doctor_appointments(doctor_id)

        if require_verified_payment:
            appts = [a for a in appts if a.get("payment_status", "").casefold() == "paid"]

        # Aggregate unique patients
        patient_map: dict[str, dict] = {}
        for a in appts:
            pid = a.get("patient_id") or a.get("phone", "")
            if not pid:
                continue

            if pid not in patient_map:
                patient_map[pid] = {
                    "patient_id": a.get("patient_id", ""),
                    "name": a.get("patient_name", ""),
                    "phone": a.get("phone", ""),
                    "email": a.get("email", ""),
                    "appointment_count": 0,
                    "last_appointment_date": a.get("date", ""),
                    "last_status": a.get("status", ""),
                    "payment_status": a.get("payment_status", ""),
                }
            patient_map[pid]["appointment_count"] += 1
            if a.get("date", "") > patient_map[pid]["last_appointment_date"]:
                patient_map[pid]["last_appointment_date"] = a.get("date", "")
                patient_map[pid]["last_status"] = a.get("status", "")
                patient_map[pid]["payment_status"] = a.get("payment_status", "")

        patients = list(patient_map.values())
        if search:
            q = search.casefold().strip()
            patients = [
                p for p in patients
                if q in p.get("name", "").casefold() or q in p.get("phone", "").casefold() or q in p.get("patient_id", "").casefold()
            ]

        patients.sort(key=lambda p: p.get("last_appointment_date", ""), reverse=True)
        return patients

    def get_doctor_patient_detail(self, patient_id: str, doctor_id: str) -> dict:
        """Fetch patient clinical profile, verifying the patient has visits with this doctor."""
        appts = self.get_doctor_appointments(doctor_id)
        patient_visits = [a for a in appts if a.get("patient_id") == patient_id]

        if not patient_visits:
            raise PermissionError("Access forbidden: This patient is not assigned to your consultations.")

        patient_info = self.get_patient(patient_id)
        if not patient_info:
            # Fallback from appointment
            first = patient_visits[0]
            patient_info = {
                "patient_id": patient_id,
                "name": first.get("patient_name"),
                "phone": first.get("phone"),
                "email": first.get("email"),
            }

        # Fetch previous prescriptions by this doctor for this patient
        prescriptions = []
        if self.prescriptions:
            prescriptions = self.prescriptions.list_prescriptions(
                doctor_id=doctor_id,
                patient_id=patient_id,
            )

        return {
            "patient": patient_info,
            "visits": patient_visits,
            "prescriptions": prescriptions,
        }

    def get_doctor_dashboard_stats(self, doctor_id: str, today_str: Optional[str] = None) -> dict:
        """Compute live aggregated metrics for the Doctor Dashboard."""
        now_tz = datetime.now(self._get_tz())
        today = today_str or now_tz.date().isoformat()

        appts = self.get_doctor_appointments(doctor_id)

        today_appts = []
        upcoming_appts = []
        completed_count = 0
        cancelled_count = 0
        awaiting_consultation = 0
        pending_prescriptions = 0
        unique_patients = set()

        for a in appts:
            pid = a.get("patient_id") or a.get("phone")
            if pid:
                unique_patients.add(pid)

            d = a.get("date", "").strip()
            st = a.get("status", "").strip().casefold()

            if d == today and st != "cancelled":
                today_appts.append(a)
                if st in ("confirmed", "pending"):
                    awaiting_consultation += 1

            if d > today and st in ("confirmed", "pending"):
                upcoming_appts.append(a)

            if st == "completed":
                completed_count += 1

            if st == "cancelled":
                cancelled_count += 1

            # Pending prescription check
            if st in ("confirmed", "completed") and (d == today or d >= today):
                if not a.get("has_prescription") or a.get("prescription_status") != "finalized":
                    pending_prescriptions += 1

        # Available slots
        slots = self.get_doctor_slots(doctor_id)
        available_slots = sum(
            1 for s in slots
            if s.get("Status", "").strip().casefold() == "available" and s.get("Date", "") >= today
        )

        return {
            "today_date": today,
            "today_appointments_count": len(today_appts),
            "upcoming_appointments_count": len(upcoming_appts),
            "completed_appointments_count": completed_count,
            "cancelled_appointments_count": cancelled_count,
            "awaiting_consultation_count": awaiting_consultation,
            "pending_prescriptions_count": pending_prescriptions,
            "total_patients": len(unique_patients),
            "available_slots": available_slots,
            "today_appointments": today_appts[:10],
            "upcoming_appointments": upcoming_appts[:10],
        }
