"""Prescription Management Service.

Provides complete clinical prescription workflow:
- Draft creation & autosave
- Rigorous clinical validation prior to finalization
- Immutable version history & amendment tracking
- Cross-doctor access isolation
- PDF generation & verified email delivery tracking
- Full audit logging
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from threading import RLock
from typing import Optional
from uuid import uuid4

from ..tools.prescription_pdf import PrescriptionPDFData, generate_prescription_pdf
from .audit_service import AuditService


class PrescriptionService:
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        pdf_dir: Optional[Path] = None,
        audit_service: Optional[AuditService] = None,
        session_factory=None,
    ) -> None:
        self._pg = None
        if session_factory is not None:
            from ..repositories.postgres_crm_repositories import PostgresPrescriptionService
            self._pg = PostgresPrescriptionService(session_factory, pdf_dir=pdf_dir, audit_service=audit_service)
        elif storage_path is None:
            from ..db.session import is_db_configured, get_session_factory
            if is_db_configured():
                try:
                    from ..repositories.postgres_crm_repositories import PostgresPrescriptionService
                    self._pg = PostgresPrescriptionService(get_session_factory(), pdf_dir=pdf_dir, audit_service=audit_service)
                except Exception:
                    self._pg = None

        if self._pg is not None:
            self.storage_path = storage_path or Path("data/prescriptions.json")
            self.pdf_dir = self._pg.pdf_dir
            self.audit = self._pg.audit
            self._lock = self._pg._lock
            self._prescriptions = {}
            self._by_appointment = {}
            return

        root_dir = Path(__file__).resolve().parents[2]
        self.storage_path = storage_path or (root_dir / "data" / "prescriptions.json")
        self.pdf_dir = pdf_dir or (root_dir / "data" / "prescriptions")
        self.audit = audit_service or AuditService()
        self._lock = RLock()
        self._prescriptions: dict[str, dict] = {}
        self._by_appointment: dict[str, str] = {}
        self._load_prescriptions()

    def _reindex_appointments(self) -> None:
        """Build O(1) appointment_id to prescription_id lookup index."""
        self._by_appointment = {}
        for rx_id, rx in self._prescriptions.items():
            appt_id = str(rx.get("appointment_id", "")).strip().casefold()
            if appt_id:
                self._by_appointment[appt_id] = rx_id

    def _load_prescriptions(self) -> None:
        """Load stored prescriptions from disk."""
        if not self.storage_path.exists():
            self._prescriptions = {}
            self._by_appointment = {}
            return
        try:
            with self.storage_path.open("r", encoding="utf-8") as f:
                self._prescriptions = json.load(f)
            self._reindex_appointments()
        except Exception:
            self._prescriptions = {}
            self._by_appointment = {}

    def _save_prescriptions(self) -> None:
        """Atomically persist prescriptions to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(self._prescriptions, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.storage_path)

    def validate_medicines(self, medicines: list[dict], allow_empty: bool = True) -> list[dict]:
        """Sanitize and validate medicine items."""
        if self._pg is not None:
            return self._pg.validate_medicines(medicines, allow_empty=allow_empty)
        if not medicines and not allow_empty:
            raise ValueError("Prescription must include at least one medication.")

        cleaned = []
        for idx, med in enumerate(medicines, start=1):
            name = str(med.get("name", "")).strip()
            strength = str(med.get("strength", "")).strip()
            dosage = str(med.get("dosage", "")).strip()
            frequency = str(med.get("frequency", "")).strip()
            duration = str(med.get("duration", "")).strip()
            instructions = str(med.get("instructions", "")).strip()

            if not allow_empty:
                if not name:
                    raise ValueError(f"Medicine row {idx} is missing a medicine name.")
                if not dosage:
                    raise ValueError(f"Medicine row {idx} ('{name}') is missing dosage information.")
                if not frequency:
                    raise ValueError(f"Medicine row {idx} ('{name}') is missing frequency instructions.")
                if not duration:
                    raise ValueError(f"Medicine row {idx} ('{name}') is missing duration.")

            if name:  # only include rows with at least a name
                cleaned.append({
                    "name": name,
                    "strength": strength,
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration": duration,
                    "instructions": instructions,
                })

        if not allow_empty and not cleaned:
            raise ValueError("Prescription must contain at least one valid medication.")
        return cleaned

    def create_or_update_draft(
        self,
        data: dict,
        doctor_id: str,
        doctor_name: str,
        doctor_specialization: str = "",
        doctor_qualification: str = "",
        doctor_reg_no: str = "",
        user: str = "doctor",
    ) -> dict:
        """Save prescription as draft. Safe against overwriting finalized records."""
        if self._pg is not None:
            return self._pg.create_or_update_draft(
                data=data,
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                doctor_specialization=doctor_specialization,
                doctor_qualification=doctor_qualification,
                doctor_reg_no=doctor_reg_no,
                user=user,
            )
        with self._lock:
            rx_id = data.get("prescription_id", "").strip()
            now = datetime.now(timezone.utc).isoformat()

            if rx_id and rx_id in self._prescriptions:
                existing = self._prescriptions[rx_id]
                # Enforce isolation: only owner can edit
                if existing.get("doctor_id", "").casefold() != doctor_id.strip().casefold():
                    raise PermissionError("Access forbidden: You cannot modify another physician's prescription.")

                # Finalized prescriptions cannot be edited directly as drafts
                if existing.get("status") in ("finalized", "amended"):
                    raise ValueError("Cannot edit a finalized prescription as a draft. Please create an amendment.")

                rx = existing
            else:
                rx_id = f"RX-{uuid4().hex[:10].upper()}"
                rx = {
                    "prescription_id": rx_id,
                    "created_at": now,
                    "created_by": user,
                    "version": 1,
                    "version_history": [],
                    "email_delivery": None,
                }

            # Update mutable fields
            rx.update({
                "patient_id": str(data.get("patient_id", rx.get("patient_id", ""))).strip(),
                "patient_name": str(data.get("patient_name", rx.get("patient_name", ""))).strip(),
                "patient_phone": str(data.get("patient_phone", rx.get("patient_phone", ""))).strip(),
                "patient_email": str(data.get("patient_email", rx.get("patient_email", ""))).strip(),
                "patient_age": str(data.get("patient_age", rx.get("patient_age", ""))).strip(),
                "patient_gender": str(data.get("patient_gender", rx.get("patient_gender", ""))).strip(),
                "doctor_id": doctor_id.strip(),
                "doctor_name": doctor_name.strip(),
                "doctor_specialization": doctor_specialization.strip() or rx.get("doctor_specialization", ""),
                "doctor_qualification": doctor_qualification.strip() or str(data.get("doctor_qualification", rx.get("doctor_qualification", ""))).strip(),
                "doctor_reg_no": doctor_reg_no.strip() or str(data.get("doctor_reg_no", rx.get("doctor_reg_no", ""))).strip(),
                "appointment_id": str(data.get("appointment_id", rx.get("appointment_id", ""))).strip(),
                "date": str(data.get("date", rx.get("date", now[:10]))).strip(),
                "chief_complaints": str(data.get("chief_complaints", rx.get("chief_complaints", ""))).strip(),
                "diagnosis": str(data.get("diagnosis", rx.get("diagnosis", ""))).strip(),
                "symptoms": str(data.get("symptoms", rx.get("symptoms", ""))).strip(),
                "vitals": data.get("vitals") if isinstance(data.get("vitals"), dict) else rx.get("vitals", {}),
                "clinical_notes": str(data.get("clinical_notes", rx.get("clinical_notes", ""))).strip(),
                "medicines": self.validate_medicines(data.get("medicines", rx.get("medicines", [])), allow_empty=True),
                "tests_advised": str(data.get("tests_advised", rx.get("tests_advised", ""))).strip(),
                "advice": str(data.get("advice", rx.get("advice", ""))).strip(),
                "follow_up_date": str(data.get("follow_up_date", rx.get("follow_up_date", ""))).strip(),
                "status": "draft",
                "updated_at": now,
                "updated_by": user,
            })

            self._prescriptions[rx_id] = rx
            appt_id = str(rx.get("appointment_id", "")).strip().casefold()
            if appt_id:
                self._by_appointment[appt_id] = rx_id
            self._save_prescriptions()

            self.audit.record(
                user=user,
                action="PRESCRIPTION_DRAFT_SAVE",
                entity_type="prescription",
                entity_id=rx_id,
                details={
                    "patient_id": rx["patient_id"],
                    "appointment_id": rx["appointment_id"],
                    "status": "draft",
                },
            )
            return dict(rx)

    def finalize_prescription(
        self,
        prescription_id: str,
        doctor_id: str,
        user: str = "doctor",
    ) -> dict:
        """Review and finalize a prescription with comprehensive validation."""
        if self._pg is not None:
            return self._pg.finalize_prescription(prescription_id=prescription_id, doctor_id=doctor_id, user=user)
        with self._lock:
            rx = self._prescriptions.get(prescription_id)
            if not rx:
                raise ValueError(f"Prescription '{prescription_id}' not found.")

            if rx.get("doctor_id", "").casefold() != doctor_id.strip().casefold():
                raise PermissionError("Access forbidden: You cannot finalize another physician's prescription.")

            if rx.get("status") in ("finalized", "amended"):
                return dict(rx)

            # Strict clinical validation prior to finalization
            if not rx.get("patient_id"):
                raise ValueError("Patient ID is required before finalizing prescription.")
            if not rx.get("patient_name"):
                raise ValueError("Patient Name is required before finalizing prescription.")
            if not rx.get("appointment_id"):
                raise ValueError("Appointment Token/ID is required before finalizing prescription.")
            if not rx.get("diagnosis"):
                raise ValueError("Clinical Diagnosis is required before finalizing prescription.")

            # Must have at least 1 complete medicine
            rx["medicines"] = self.validate_medicines(rx.get("medicines", []), allow_empty=False)

            now = datetime.now(timezone.utc).isoformat()
            rx["status"] = "finalized"
            rx["finalized_at"] = now
            rx["updated_at"] = now
            rx["updated_by"] = user

            self._prescriptions[prescription_id] = rx
            self._save_prescriptions()

            self.audit.record(
                user=user,
                action="PRESCRIPTION_FINALIZE",
                entity_type="prescription",
                entity_id=prescription_id,
                details={
                    "patient_id": rx["patient_id"],
                    "appointment_id": rx["appointment_id"],
                    "version": rx["version"],
                },
            )
            return dict(rx)

    def amend_prescription(
        self,
        prescription_id: str,
        updates: dict,
        doctor_id: str,
        user: str = "doctor",
        amendment_reason: str = "Clinical dosage correction",
    ) -> dict:
        """Amend an already finalized prescription by creating an explicit new version."""
        if self._pg is not None:
            return self._pg.amend_prescription(
                prescription_id=prescription_id,
                updates=updates,
                doctor_id=doctor_id,
                user=user,
                amendment_reason=amendment_reason,
            )
        with self._lock:
            rx = self._prescriptions.get(prescription_id)
            if not rx:
                raise ValueError(f"Prescription '{prescription_id}' not found.")

            if rx.get("doctor_id", "").casefold() != doctor_id.strip().casefold():
                raise PermissionError("Access forbidden: You cannot amend another physician's prescription.")

            if rx.get("status") not in ("finalized", "amended"):
                raise ValueError("Only finalized prescriptions can be amended. Edit the draft instead.")

            if not amendment_reason.strip():
                raise ValueError("A clear reason for the clinical amendment must be provided.")

            # Snapshot previous finalized version
            now = datetime.now(timezone.utc).isoformat()
            snapshot = {
                "version": rx["version"],
                "chief_complaints": rx.get("chief_complaints", ""),
                "diagnosis": rx.get("diagnosis", ""),
                "symptoms": rx.get("symptoms", ""),
                "vitals": dict(rx.get("vitals", {})),
                "clinical_notes": rx.get("clinical_notes", ""),
                "medicines": list(rx.get("medicines", [])),
                "tests_advised": rx.get("tests_advised", ""),
                "advice": rx.get("advice", ""),
                "follow_up_date": rx.get("follow_up_date", ""),
                "finalized_at": rx.get("finalized_at", rx["updated_at"]),
                "amended_at": now,
                "amended_by": user,
                "amendment_reason": amendment_reason.strip(),
            }
            rx.setdefault("version_history", []).append(snapshot)

            # Apply updates
            rx["version"] += 1
            rx["status"] = "amended"
            if "chief_complaints" in updates:
                rx["chief_complaints"] = str(updates["chief_complaints"]).strip()
            if "diagnosis" in updates and str(updates["diagnosis"]).strip():
                rx["diagnosis"] = str(updates["diagnosis"]).strip()
            if "symptoms" in updates:
                rx["symptoms"] = str(updates["symptoms"]).strip()
            if "vitals" in updates and isinstance(updates["vitals"], dict):
                rx["vitals"] = updates["vitals"]
            if "clinical_notes" in updates:
                rx["clinical_notes"] = str(updates["clinical_notes"]).strip()
            if "medicines" in updates:
                rx["medicines"] = self.validate_medicines(updates["medicines"], allow_empty=False)
            if "tests_advised" in updates:
                rx["tests_advised"] = str(updates["tests_advised"]).strip()
            if "advice" in updates:
                rx["advice"] = str(updates["advice"]).strip()
            if "follow_up_date" in updates:
                rx["follow_up_date"] = str(updates["follow_up_date"]).strip()

            rx["updated_at"] = now
            rx["updated_by"] = user
            rx["finalized_at"] = now

            self._prescriptions[prescription_id] = rx
            self._save_prescriptions()

            self.audit.record(
                user=user,
                action="PRESCRIPTION_AMENDMENT",
                entity_type="prescription",
                entity_id=prescription_id,
                details={
                    "new_version": rx["version"],
                    "reason": amendment_reason.strip(),
                },
            )
            return dict(rx)

    def get_prescription(self, prescription_id: str) -> Optional[dict]:
        """Fetch prescription by ID."""
        if self._pg is not None:
            return self._pg.get_prescription(prescription_id=prescription_id)
        with self._lock:
            rx = self._prescriptions.get(prescription_id)
            return dict(rx) if rx else None

    def get_prescription_by_appointment(self, appointment_id: str) -> Optional[dict]:
        """Find prescription associated with a specific appointment token via O(1) index."""
        if self._pg is not None:
            return self._pg.get_prescription_by_appointment(appointment_id=appointment_id)
        norm_id = appointment_id.strip().casefold()
        if not norm_id:
            return None
        with self._lock:
            rx_id = self._by_appointment.get(norm_id)
            if rx_id and rx_id in self._prescriptions:
                return dict(self._prescriptions[rx_id])
            for r_id, rx in self._prescriptions.items():
                if rx.get("appointment_id", "").strip().casefold() == norm_id:
                    self._by_appointment[norm_id] = r_id
                    return dict(rx)
        return None

    def list_prescriptions(
        self,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        status: Optional[str] = None,
        date_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        """List prescriptions with filtering."""
        if self._pg is not None:
            return self._pg.list_prescriptions(
                doctor_id=doctor_id,
                patient_id=patient_id,
                appointment_id=appointment_id,
                status=status,
                date_filter=date_filter,
                search=search,
            )
        with self._lock:
            items = list(self._prescriptions.values())

        if doctor_id:
            d_norm = doctor_id.strip().casefold()
            items = [rx for rx in items if rx.get("doctor_id", "").strip().casefold() == d_norm]

        if patient_id:
            p_norm = patient_id.strip().casefold()
            items = [rx for rx in items if rx.get("patient_id", "").strip().casefold() == p_norm]

        if appointment_id:
            a_norm = appointment_id.strip().casefold()
            items = [rx for rx in items if rx.get("appointment_id", "").strip().casefold() == a_norm]

        if status:
            s_norm = status.strip().casefold()
            items = [rx for rx in items if rx.get("status", "").strip().casefold() == s_norm]

        if date_filter:
            items = [rx for rx in items if rx.get("date", "").strip() == date_filter.strip()]

        if search:
            q = search.strip().casefold()
            items = [
                rx for rx in items
                if (
                    q in rx.get("patient_name", "").casefold()
                    or q in rx.get("patient_id", "").casefold()
                    or q in rx.get("diagnosis", "").casefold()
                    or q in rx.get("prescription_id", "").casefold()
                    or q in rx.get("doctor_name", "").casefold()
                )
            ]

        items.sort(key=lambda r: (r.get("date", ""), r.get("created_at", "")), reverse=True)
        return items

    def record_email_delivery(
        self,
        prescription_id: str,
        success: bool,
        recipient: str,
        error: Optional[str] = None,
    ) -> None:
        """Track prescription email delivery state."""
        if self._pg is not None:
            return self._pg.record_email_delivery(
                prescription_id=prescription_id,
                success=success,
                recipient=recipient,
                error=error,
            )
        with self._lock:
            rx = self._prescriptions.get(prescription_id)
            if not rx:
                return
            now = datetime.now(timezone.utc).isoformat()
            rx["email_delivery"] = {
                "sent": success,
                "sent_at": now if success else None,
                "recipient": recipient,
                "error": error,
            }
            self._save_prescriptions()

    def generate_pdf_for_prescription(
        self,
        prescription_id: str,
        clinic_name: str = "Clinic",
        clinic_phone: str = "",
        clinic_email: str = "",
        clinic_address: str = "",
        clinic_logo: str = "",
        doctor_signature: str = "",
    ) -> tuple[str, Path]:
        """Generate a ReportLab PDF document for a prescription, reusing cached PDF for finalized records."""
        if self._pg is not None:
            return self._pg.generate_pdf_for_prescription(
                prescription_id=prescription_id,
                clinic_name=clinic_name,
                clinic_phone=clinic_phone,
                clinic_email=clinic_email,
                clinic_address=clinic_address,
                clinic_logo=clinic_logo,
                doctor_signature=doctor_signature,
            )
        rx = self.get_prescription(prescription_id)
        if not rx:
            raise ValueError(f"Prescription '{prescription_id}' not found.")

        clean_id = prescription_id.replace("/", "_").replace("\\", "_")
        version = rx.get("version", 1)
        cached_pdf_path = self.pdf_dir / f"{clean_id}_v{version}.pdf"

        # Reuse existing PDF if prescription is finalized or amended and file already exists
        if rx.get("status") in ("finalized", "amended") and cached_pdf_path.exists() and cached_pdf_path.stat().st_size > 0:
            return clean_id, cached_pdf_path

        effective_logo = clinic_logo or rx.get("clinic_logo") or ""
        effective_sig = doctor_signature or rx.get("doctor_signature") or rx.get("Signature") or ""
        effective_photo = rx.get("doctor_photo") or rx.get("Photo") or ""

        pdf_data = PrescriptionPDFData(
            clinic_name=clinic_name,
            clinic_phone=clinic_phone,
            clinic_email=clinic_email,
            clinic_address=clinic_address,
            doctor_name=rx.get("doctor_name", "Doctor"),
            doctor_specialization=rx.get("doctor_specialization", "Physician"),
            doctor_qualification=rx.get("doctor_qualification", ""),
            doctor_reg_no=rx.get("doctor_reg_no", ""),
            patient_id=rx.get("patient_id", ""),
            patient_name=rx.get("patient_name", ""),
            patient_phone=rx.get("patient_phone", ""),
            patient_age=rx.get("patient_age", ""),
            patient_gender=rx.get("patient_gender", ""),
            appointment_id=rx.get("appointment_id", ""),
            prescription_id=rx.get("prescription_id", ""),
            date=rx.get("date", ""),
            chief_complaints=rx.get("chief_complaints", ""),
            diagnosis=rx.get("diagnosis", ""),
            symptoms=rx.get("symptoms", ""),
            vitals=rx.get("vitals", {}),
            clinical_notes=rx.get("clinical_notes", ""),
            medicines=rx.get("medicines", []),
            tests_advised=rx.get("tests_advised", ""),
            advice=rx.get("advice", ""),
            follow_up_date=rx.get("follow_up_date", ""),
            version=rx.get("version", 1),
            clinic_logo=effective_logo,
            doctor_signature=effective_sig,
            doctor_photo=effective_photo,
        )

        return generate_prescription_pdf(pdf_data, self.pdf_dir)

