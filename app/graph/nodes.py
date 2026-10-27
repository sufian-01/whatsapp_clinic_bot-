from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from typing import TYPE_CHECKING
from ..core.prompts import load_system_prompt

if TYPE_CHECKING:
    from ..llm.gemini import GeminiClient
    from ..rag.service import RagService
from ..tools.date_utils import parse_date, parse_date_from_text
from ..tools.doctors import (
    format_doctor_list_display,
    match_health_concern,
    resolve_specialization,
)
from ..tools.invoice import InvoiceData
from ..tools.invoices import InvoiceTools
from ..tools.patients import PatientRecord
from ..tools.rag_tool import search_clinic_knowledge
from .state import GraphState


logger = logging.getLogger(__name__)

# Maximum doctors to show as interactive buttons (beyond this limit we use text)
_MAX_BUTTON_DOCTORS = 8


def _is_hindi_or_hinglish(text: str) -> bool:
    import re
    lowered = text.casefold()
    hindi_tokens = (
        "kab", "hain", "hai", "karo", "karna", "karni", "kar do", "chahiye", "batao",
        "dikhao", "aaj", "kal", "parso", "aur", "ko", "par", "pe", "mein", "se",
        "meri", "mera", "mere", "mujhe", "hum", "aap", "kripya", "namaste", "dhanyawad",
        "shukriya", "milenge", "milte", "badal", "radd", "kahan", "kitna", "kitne",
    )
    if any(re.search(rf"\b{re.escape(token)}\b", lowered) for token in hindi_tokens):
        return True
    return any("\u0900" <= ch <= "\u097f" for ch in text)


class GraphNodes:
    def __init__(
        self,
        clinic_name: str,
        llm: GeminiClient,
        rag: RagService,
        doctors=None,
        support_phone: str = "6200126662",
        patients=None,
        slots=None,
        email_sender=None,
        payments=None,
        invoices=None,
        gmail=None,
        clinic_timezone: str = "Asia/Kolkata",
        today_provider=None,
        crm_service=None,
    ) -> None:
        self._clinic_name = clinic_name
        self._llm = llm
        self._rag = rag
        self._doctors = doctors
        self._support_phone = support_phone
        self._patients = patients
        self._slots = slots
        self._payments = payments
        self._invoices = invoices or InvoiceTools()
        self._gmail = gmail
        self._clinic_timezone = clinic_timezone
        self._today_provider = today_provider
        if crm_service is not None:
            self._crm = crm_service
        else:
            from ..services.crm_service import CrmService
            self._crm = CrmService(
                patients_tools=self._patients,
                doctors_tools=self._doctors,
                slots_tools=self._slots,
                payments_tools=self._payments,
                clinic_name=self._clinic_name,
                clinic_timezone=self._clinic_timezone,
            )

    # ------------------------------------------------------------------
    # classify
    # ------------------------------------------------------------------

    def classify(self, state: GraphState) -> GraphState:
        from .router import classify_intent
        return classify_intent(state, llm=self._llm)

    # ------------------------------------------------------------------
    # retrieve  (RAG)
    # ------------------------------------------------------------------

    def retrieve(self, state: GraphState) -> GraphState:
        flags = state.get("feature_flags", {})
        from ..core.feature_flags import is_feature_enabled
        if not is_feature_enabled(flags, "rag_knowledge"):
            logger.info("RAG knowledge search disabled by feature flags")
            return {**state, "clinic_context": []}
        logger.info("RAG tool invoked")
        tenant_id = state.get("tenant_id")
        context = search_clinic_knowledge(self._rag, state.get("user_text", ""), tenant_id=tenant_id)
        logger.info("Retrieved %d chunks", len(context))
        return {**state, "clinic_context": context}


    # ------------------------------------------------------------------
    # doctor_lookup  (for doctor_information intent)
    # ------------------------------------------------------------------

    def doctor_lookup(self, state: GraphState) -> GraphState:
        if self._doctors is None:
            return {**state, "doctor_context": []}
        text = state.get("user_text", "")
        matches = self._doctors.get_doctors()
        found_specific = False
        for doctor in matches:
            name = doctor.get("Doctor Name", "")
            if name and name.casefold() in text.casefold():
                matches = self._doctors.get_doctor_by_name(name)
                found_specific = True
                break
        if not found_specific and state.get("doctor_name"):
            name = state.get("doctor_name")
            matched = self._doctors.get_doctor_by_name(name)
            if matched:
                matches = matched
                found_specific = True
        if not found_specific:
            for specialization in ("gynecologist", "physician", "specialist"):
                if specialization in text.casefold():
                    matches = self._doctors.get_doctors_by_specialization(specialization)
                    break
        return {**state, "doctor_context": matches}

    # ------------------------------------------------------------------
    # doctor_list_node  (deterministic doctor discovery, listing & concern matching)
    # ------------------------------------------------------------------

    def doctor_list_node(self, state: GraphState) -> GraphState:
        """Show available doctors or matching specialists without starting appointment flow.

        - If user provided a date -> filter by slot availability (deterministic).
        - If user described a health concern/symptom -> match concern to specialization.
        - If user provided a specialization keyword -> filter by specialization.
        - Otherwise show all active doctors from the Google Sheet.

        Zero LLM calls made here to minimize token usage.
        """
        if self._doctors is None:
            return {**state, "response": "Doctor information is not available right now. Please contact the clinic team at " + self._support_phone + "."}

        text = state.get("user_text", "")
        logger.info(">>> [AGENT NODE TRIGGERED] 'doctor_list' | text=%r", text)

        # Availability always comes from appointment slots, never from the
        # doctors sheet's working-day metadata.
        date_result = parse_date_from_text(text, self._clinic_today())
        target_date: str | None = date_result["date"] if date_result.get("success") else None

        selected = self._selected_doctor(state)
        resolved = self._doctors.resolve_doctor(text)
        named_doctor = resolved.get("doctor") if resolved.get("status") == "matched" else None
        availability_requested = self._is_availability_request(text)
        requested_specialization = resolve_specialization(text)

        if named_doctor and (availability_requested or "recommend" in text.casefold()):
            return self._show_doctor_availability(state, named_doctor, target_date)
        if selected and (availability_requested or target_date):
            return self._show_doctor_availability(state, selected, target_date)
        if availability_requested:
            return self._show_general_availability(state, target_date, requested_specialization)
        if requested_specialization and any(term in text.casefold() for term in ("need", "recommend")):
            return self._show_general_availability(state, target_date, requested_specialization)

        # A date-filtered doctor list remains useful for non-availability
        # queries, but still uses real slot records.
        if target_date and self._slots:
            doctors = self._doctors.get_available_doctors_for_date(target_date, self._slots)
            if not doctors:
                return {**state, "response": f"No doctors have available slots on {date_result['display_date']}. Please try another date or contact the clinic at {self._support_phone}."}
            intro = f"Doctors available on {date_result['display_date']}:"
            response = format_doctor_list_display(doctors, intro=intro)
            return {
                **state,
                "doctor_choices": doctors[:_MAX_BUTTON_DOCTORS],
                "ui": "doctor_select",
                "response": response,
            }

        # 2. Try to match health concern/symptom keywords (deterministic)
        concern_phrase, concern_spec = match_health_concern(text)
        if concern_spec:
            spec_doctors = self._doctors.get_doctors_by_specialization(concern_spec)
            if spec_doctors:
                spec_name = spec_doctors[0].get("Specialization", concern_spec.title())
                intro = f"For health concerns related to {concern_phrase}, you may consult our {spec_name} specialist(s):"
                response = (
                    format_doctor_list_display(spec_doctors, intro=intro)
                    + "\n\n*(Note: This recommendation is informational based on our clinic specialties and not medical advice. Please consult our doctors for proper evaluation.)*"
                )
                return {
                    **state,
                    "doctor_choices": spec_doctors[:_MAX_BUTTON_DOCTORS],
                    "ui": "doctor_select",
                    "response": response,
                }
            else:
                all_active = self._doctors.get_active_doctors()
                intro = f"We do not currently have a specialist available for {concern_phrase}.\n\nOur available doctors are:"
                response = (
                    format_doctor_list_display(all_active, intro=intro)
                    + "\n\n*(Note: This is informational based on our clinic specialties and not medical advice.)*"
                )
                return {
                    **state,
                    "doctor_choices": all_active[:_MAX_BUTTON_DOCTORS],
                    "ui": "doctor_select",
                    "response": response,
                }

        # 3. Try to extract direct specialization from user text (deterministic)
        spec_canonical = resolve_specialization(text)
        if spec_canonical:
            doctors = self._doctors.get_doctors_by_specialization(spec_canonical)
            if doctors:
                spec_name = doctors[0].get("Specialization", spec_canonical.title())
                intro = f"Our available {spec_name} specialist(s):"
                response = format_doctor_list_display(doctors, intro=intro)
                if state.get("appointment_step") and state.get("appointment_step") != "complete":
                    if _is_hindi_or_hinglish(text):
                        response += "\n\n*(Aapka appointment booking chalu hai. Kripya upar diye gaye doctor ka naam select karein ya apna agla detail batayein.)*"
                    else:
                        response += "\n\n*(Your appointment booking is still active. Please select a doctor above or reply to continue.)*"
                return {
                    **state,
                    "doctor_choices": doctors[:_MAX_BUTTON_DOCTORS],
                    "ui": "doctor_select",
                    "response": response,
                }

        # 4. General doctor listing query (deterministic)
        doctors = self._doctors.get_active_doctors()
        if not doctors:
            return {**state, "response": "No doctors are currently available. Please contact the clinic team at " + self._support_phone + "."}

        response = format_doctor_list_display(doctors)
        if state.get("appointment_step") and state.get("appointment_step") != "complete":
            if _is_hindi_or_hinglish(text):
                response += "\n\n*(Aapka appointment booking chalu hai. Kripya upar diye gaye doctor ka naam select karein ya apna agla detail batayein.)*"
            else:
                response += "\n\n*(Your appointment booking is still active. Please select a doctor above or reply to continue.)*"
        return {
            **state,
            "doctor_choices": doctors[:_MAX_BUTTON_DOCTORS],
            "ui": "doctor_select",
            "response": response,
        }

    def _clinic_today(self) -> date:
        if self._today_provider is not None:
            return self._today_provider()
        try:
            return datetime.now(ZoneInfo(self._clinic_timezone)).date()
        except ZoneInfoNotFoundError:
            logger.warning("Unknown clinic timezone; falling back to UTC")
            return datetime.now(ZoneInfo("UTC")).date()

    @staticmethod
    def _is_availability_request(text: str) -> bool:
        lowered = text.casefold()
        return any(term in lowered for term in ("available", "availability", "free", "slot", "slots", "when", "kab", "aur kab", "date"))

    def _selected_doctor(self, state: GraphState) -> dict | None:
        if self._doctors is None or not state.get("doctor_name"):
            return None
        for doctor in self._doctors.get_active_doctors():
            if state.get("doctor_id") and doctor.get("Doctor ID") == state.get("doctor_id"):
                return doctor
            if doctor.get("Doctor Name", "").casefold() == state["doctor_name"].casefold():
                return doctor
        return None

    def _upcoming_slots(self, doctor: dict | None = None) -> list[dict]:
        if self._slots is None or not hasattr(self._slots, "get_upcoming_available_slots"):
            return []
        try:
            result = self._slots.get_upcoming_available_slots(
                doctor.get("Doctor Name", "") if doctor else "",
                doctor.get("Doctor ID", "") if doctor else "",
                self._clinic_today().isoformat(),
            )
        except Exception:
            logger.warning("Upcoming appointment availability lookup failed")
            return []
        if isinstance(result, dict):
            return result.get("slots", []) if result.get("success", False) else []
        return result if isinstance(result, list) else []

    @staticmethod
    def _format_time(value: str) -> str:
        for pattern in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I %p"):
            try:
                parsed = datetime.strptime(value.strip(), pattern)
                hour = parsed.hour % 12 or 12
                return f"{hour}:{parsed.minute:02d} {'AM' if parsed.hour < 12 else 'PM'}"
            except ValueError:
                continue
        return value

    def _format_availability(self, slots: list[dict], max_dates: int = 3, max_slots_per_date: int = 4) -> str:
        grouped: dict[str, list[dict]] = {}
        for slot in slots:
            grouped.setdefault(slot.get("Date", ""), []).append(slot)
        lines: list[str] = []
        for slot_date in sorted(grouped)[:max_dates]:
            try:
                label = date.fromisoformat(slot_date).strftime("%d %B")
            except ValueError:
                continue
            times = [self._format_time(slot.get("Start Time", "")) for slot in grouped[slot_date][:max_slots_per_date]]
            if len(grouped[slot_date]) > max_slots_per_date:
                times.append("more slots")
            lines.append(f"- {label}: {', '.join(time for time in times if time)}")
        return "\n".join(lines)

    def _show_doctor_availability(self, state: GraphState, doctor: dict, requested_date: str | None = None) -> GraphState:
        all_slots = self._upcoming_slots(doctor)
        details = self._doctor_details(doctor)
        name = doctor.get("Doctor Name", "this doctor")
        if requested_date:
            requested_slots = [slot for slot in all_slots if slot.get("Date") == requested_date]
            if requested_slots:
                label = date.fromisoformat(requested_date).strftime("%d %B")
                times = ", ".join(self._format_time(slot.get("Start Time", "")) for slot in requested_slots)
                is_booking = bool(state.get("appointment_step"))
                extra_step = {"ui": "slots", "appointment_step": "pre_patient_slot"} if is_booking else {}
                return {
                    **state,
                    **details,
                    **extra_step,
                    "appointment_date": requested_date,
                    "available_slots": requested_slots,
                    "response": f"{name} is available on {label}: {times}. Which time would you prefer?",
                }
            nearest = [slot for slot in all_slots if slot.get("Date", "") > requested_date]
            if nearest:
                return {
                    **state,
                    **details,
                    "response": f"{name} has no available slots on {date.fromisoformat(requested_date).strftime('%d %B')}. Nearest upcoming availability:\n{self._format_availability(nearest)}\n\nWhich date would you prefer?",
                }
            return {**state, **details, "response": f"{name} has no available slots on that date or in the upcoming schedule. I can check another doctor or date."}
        if not all_slots:
            return {**state, **details, "response": f"{name} has no upcoming available slots. I can check another doctor or date."}
        return {
            **state,
            **details,
            "available_slots": all_slots,
            "response": f"{name} is available on:\n{self._format_availability(all_slots)}\n\nWhich date would you prefer? Reply with a date to see more times.",
        }

    def _show_general_availability(self, state: GraphState, requested_date: str | None = None, specialization: str | None = None) -> GraphState:
        slots = self._upcoming_slots()
        if requested_date:
            slots = [slot for slot in slots if slot.get("Date") == requested_date]
        if not slots:
            if not requested_date and self._doctors:
                all_active = self._doctors.get_active_doctors()
                if specialization:
                    all_active = self._doctors.get_doctors_by_specialization(specialization)
                if all_active:
                    response = format_doctor_list_display(all_active)
                    return {
                        **state,
                        "doctor_choices": all_active[:_MAX_BUTTON_DOCTORS],
                        "ui": "doctor_select",
                        "response": response,
                    }
            detail = f" on {date.fromisoformat(requested_date).strftime('%d %B')}" if requested_date else ""
            return {**state, "response": f"No doctors have available appointment slots{detail}. Please try another date."}
        names = {slot.get("Doctor Name", "").casefold() for slot in slots}
        doctors = [
            doctor for doctor in self._doctors.get_active_doctors()
            if doctor.get("Doctor Name", "").casefold() in names
            and (not specialization or doctor in self._doctors.get_doctors_by_specialization(specialization))
        ]
        by_doctor: list[str] = []
        for doctor in doctors[:_MAX_BUTTON_DOCTORS]:
            doctor_slots = [slot for slot in slots if slot.get("Doctor Name", "").casefold() == doctor.get("Doctor Name", "").casefold()]
            by_doctor.append(f"- {doctor.get('Doctor Name', 'Doctor')}:\n{self._format_availability(doctor_slots, max_dates=1)}")
        heading = f"Doctors with available slots on {date.fromisoformat(requested_date).strftime('%d %B')}:" if requested_date else "Doctors with upcoming available appointments:"
        return {
            **state,
            "doctor_choices": doctors[:_MAX_BUTTON_DOCTORS],
            "ui": "doctor_select",
            "response": heading + "\n" + "\n".join(by_doctor) + "\n\nPlease select a doctor. Reply with a doctor name or a specific date to see more.",
        }

    @staticmethod
    def _doctor_details(doctor: dict) -> dict:
        return {
            "doctor_context": [doctor],
            "doctor_id": doctor.get("Doctor ID", ""),
            "doctor_name": doctor.get("Doctor Name", ""),
            "specialization": doctor.get("Specialization", ""),
            "amount": doctor.get("Consultation Fee", ""),
        }

    def _extract_slot_from_text(self, state: GraphState, text: str) -> dict | None:
        import re
        slots = state.get("available_slots", [])
        if not slots:
            return None
        lowered = text.casefold()
        if lowered.startswith("slot:"):
            sid = lowered.removeprefix("slot:").strip()
            return next((s for s in slots if s.get("Slot ID", "").casefold() == sid), None)
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)?\b", lowered)
        if time_match:
            hour_str, min_str, period = time_match.groups()
            hour = int(hour_str)
            minute = int(min_str) if min_str else 0
            if period == "pm" and hour < 12:
                hour += 12
            target_str = f"{hour:02d}:{minute:02d}"
            target_12 = f"{hour % 12 or 12}:{minute:02d}"
            for s in slots:
                st = s.get("Start Time", "")
                if target_str in st or target_12 in st:
                    return s
        return None

    # ------------------------------------------------------------------
    # appointment_start
    # ------------------------------------------------------------------

    def appointment_start(self, state: GraphState) -> GraphState:
        text = state.get("user_text", "")
        logger.info(">>> [AGENT NODE TRIGGERED] 'appointment_start' (Booking Initiated) | text=%r", text)

        from .router import _is_existing_appointment_query
        if _is_existing_appointment_query(text):
            logger.info("appointment_start redirected: query is for existing appointment/timing")
            return self.my_appointments_node(state)

        # 1. Parse date if provided in text (e.g. '15 tarikh oct', 'tomorrow', 'kal', '20 October')
        parsed_date_info = parse_date_from_text(text, self._clinic_today())
        extracted_date = parsed_date_info["date"] if parsed_date_info.get("success") else None

        # 2. Extract slot if explicitly mentioned
        slot_match = self._extract_slot_from_text(state, text)
        extra = {}
        if slot_match:
            extra = {"slot_id": slot_match.get("Slot ID", ""), "appointment_time": slot_match.get("Start Time", "")}
        if extracted_date:
            extra["appointment_date"] = extracted_date

        # 3. Deterministic doctor matching
        matched_doctor = None
        if self._doctors is not None:
            resolved = self._doctors.resolve_doctor(text)
            if resolved.get("status") == "matched":
                matched_doctor = resolved["doctor"]

        # 4. Check for specialization or health concern keyword if doctor not directly matched
        # Handles queries like "dr sufian se ya cardio wale se", "appointment with cardiologist", "skin doctor"
        spec_canonical = resolve_specialization(text)
        if not spec_canonical:
            _, spec_canonical = match_health_concern(text)

        if not matched_doctor and spec_canonical and self._doctors is not None:
            spec_doctors = self._doctors.get_doctors_by_specialization(spec_canonical)
            if spec_doctors:
                if len(spec_doctors) == 1:
                    matched_doctor = spec_doctors[0]
                else:
                    intro = f"Here are our available {spec_canonical.title()} specialists:"
                    if any(w in text.lower() for w in ("sufian", "sufiyan", "sufan")) and not any("sufian" in d.get("Doctor Name", "").lower() for d in spec_doctors):
                        intro = f"Dr. Sufian is not on our current panel, but here are our available {spec_canonical.title()} specialists:"
                    disp = format_doctor_list_display(spec_doctors, intro=intro)
                    return {
                        **state,
                        **extra,
                        "doctor_choices": spec_doctors[:_MAX_BUTTON_DOCTORS],
                        "appointment_step": "doctor",
                        "ui": "doctor_select",
                        "response": disp,
                    }

        # 5. If a doctor was matched (either directly or uniquely by specialty)
        draft = dict(state.get("appointment_draft") or {})
        draft["tenant_id"] = state.get("tenant_id", "default")
        if matched_doctor:
            if not matched_doctor.get("Consultation Fee", ""):
                return {**state, "response": "The consultation fee is unavailable, so I cannot continue this booking."}
            draft["doctor_id"] = matched_doctor.get("Doctor ID", "")
            draft["doctor_name"] = matched_doctor.get("Doctor Name", "")
            draft["specialization"] = matched_doctor.get("Specialization", "")
            draft["consultation_fee"] = matched_doctor.get("Consultation Fee", "500")
            selected = {
                **state,
                **self._doctor_details(matched_doctor),
                **extra,
                "active_flow": "appointment_booking",
                "appointment_draft": draft,
                "appointment_step": "pre_patient_date",
                "doctor_choices": [],
                "ui": "",
            }
            res = self._show_doctor_availability(selected, matched_doctor, requested_date=extracted_date)
            res["active_flow"] = "appointment_booking"
            res["appointment_draft"] = draft
            if any(w in text.lower() for w in ("sufian", "sufiyan", "sufan")) and "sufian" not in matched_doctor.get("Doctor Name", "").lower():
                res["response"] = f"Dr. Sufian is not on our panel, but we have {matched_doctor.get('Doctor Name')} ({matched_doctor.get('Specialization')}).\n\n{res['response']}"
            return res

        # 6. If doctor was already selected in prior state
        selected_doc = self._selected_doctor(state)
        if selected_doc:
            doc_name = selected_doc.get("Doctor Name", "")
            draft["doctor_id"] = selected_doc.get("Doctor ID", "")
            draft["doctor_name"] = doc_name
            return {
                **state,
                **extra,
                "active_flow": "appointment_booking",
                "appointment_draft": draft,
                "appointment_step": "name",
                "pending_field": "name",
                "ui": "",
                "response": f"Sure, booking an appointment with Dr. {doc_name}. May I know your name?",
            }

        return {
            **state,
            **extra,
            "active_flow": "appointment_booking",
            "appointment_draft": draft,
            "appointment_step": "name",
            "pending_field": "name",
            "ui": "",
            "response": "Sure. May I know your name?",
        }

    # ------------------------------------------------------------------
    # appointment_progress
    # ------------------------------------------------------------------

    def appointment_progress(self, state: GraphState) -> GraphState:  # noqa: C901
        step = state.get("appointment_step", "name")
        text = state.get("user_text", "").strip()
        logger.info(">>> [AGENT NODE TRIGGERED] 'appointment_progress' (Step: %s) | text=%r", step, text)

        from .router import _is_existing_appointment_query
        # Guard: If user is asking about their existing appointment or arrival timing
        if _is_existing_appointment_query(text) or any(phrase in text.casefold() for phrase in (
            "book kr chuka", "book kar chuka", "book kiya tha", "book kia tha", "already booked", "already book",
            "booking ho chuki", "booking ho gayi", "appointment ho gaya", "kitne bje aana", "kab aana",
        )):
            logger.info("Interrupting appointment_progress: user inquired about existing booking/timing")
            return self.my_appointments_node({**state, "appointment_step": "complete"})

        # Guard: If user wants to exit / cancel booking flow
        from .router import _is_draft_cancel_or_rejection
        if _is_draft_cancel_or_rejection(text):
            return self.appointment_draft_cancel(state)

        # Guard: If user provides or selects a doctor during active booking.
        # When asking for patient details (name, email, phone), NEVER intercept a bare name (like 'Habiba', 'Arjun', 'Sana')
        # as a doctor selection unless the user explicitly used a doctor indicator (e.g. 'Dr.', 'Doctor', 'DOC-').
        if self._doctors:
            has_doc_indicator = (
                any(prefix in text.lower() for prefix in ("dr.", "dr ", "doctor", "doc:", "doctor:"))
                or text.strip().upper().startswith(("DOC-", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"))
            )
            if step not in ("name", "email", "phone") or has_doc_indicator:
                doc_resolution = self._doctors.resolve_doctor(text)
                if doc_resolution.get("status") == "matched":
                    return self._accept_doctor(state, doc_resolution["doctor"])

        if step == "name":
            cleaned = text.strip()
            lowered = cleaned.casefold()
            is_question = "?" in cleaned or any(w in lowered.split() for w in ("kya", "kyu", "kyun", "why", "who", "which", "kaise", "what", "kab", "kitne", "batao", "btao"))
            is_greeting = lowered in {"hi", "hello", "hey", "hii", "namaste"}
            is_booking_phrase = any(w in lowered for w in ("book", "appointment", "appoinment", "doctor", "dr", "chahiye", "karo", "chuka"))
            if is_question:
                resume_ctx = {
                    "flow": "appointment_booking",
                    "pending_field": "name",
                    "interrupted_at_step": "name",
                }
                return self.answer({
                    **state,
                    "interruption_type": "side_question",
                    "resume_context": resume_ctx,
                    "active_flow": "appointment_booking",
                })
            if is_greeting or is_booking_phrase or len(cleaned) < 2:
                if _is_hindi_or_hinglish(cleaned):
                    return {**state, "ui": "", "response": "Kripya patient ka poora naam share karein (jaise 'Rahul Sharma') jinke liye appointment book karni hai."}
                return {**state, "ui": "", "response": "Please provide the patient's full name to continue with the appointment."}
            draft = dict(state.get("appointment_draft") or {})
            draft["patient_name"] = cleaned
            return {
                **state,
                "patient_name": cleaned,
                "appointment_draft": draft,
                "active_flow": "appointment_booking",
                "pending_field": "doctor" if not state.get("doctor_name") else "email",
                "appointment_step": "email",
                "ui": "",
                "response": "What email address should receive the invoice?",
            }

        if step == "email":
            lowered = text.casefold()
            if any(w in lowered for w in ("skip", "nahi", "no", "nahi hai", "no email", "dont have", "baad me", "later", "nhi hai", "pata nahi")):
                return {
                    **state,
                    "patient_email": "patient@clinic.local",
                    "appointment_step": "phone",
                    "ui": "",
                    "response": "Sure! What phone number should we use for your appointment updates?"
                }
            if "@" not in text or "." not in text:
                if _is_hindi_or_hinglish(text):
                    return {**state, "ui": "", "response": "Kripya ek valid email address share karein (jaise patient@example.com), ya 'skip' likhein."}
                return {**state, "ui": "", "response": "Please provide a valid email address, or type 'skip' if you don't have an email."}
            return {**state, "patient_email": text.strip(), "appointment_step": "phone", "ui": "", "response": "What phone number should we use?"}

        if step == "phone":
            import re
            digits = re.sub(r"\D", "", text)
            if len(digits) < 5 or len(digits) > 15:
                if _is_hindi_or_hinglish(text) or any(w in text.casefold() for w in ("number", "du", "kiska", "kyu", "kyun", "phone")):
                    return {
                        **state,
                        "ui": "",
                        "response": "Ji haan, kripya apna 10-digit mobile number share karein jisse hum aapki appointment confirm kar sakein.",
                    }
                return {
                    **state,
                    "ui": "",
                    "response": "Please provide a valid 10-digit phone number for appointment confirmation and notifications.",
                }

            clean_phone = text.strip() if len(digits) < 10 else (digits[-10:] if len(digits) > 10 and digits.startswith("91") else digits)
            if state.get("slot_id") and state.get("doctor_name"):
                summary = self._summary({**state, "patient_phone": clean_phone}, state.get("appointment_time", ""))
                return {**state, "patient_phone": clean_phone, "appointment_step": "confirmation", "ui": "confirm", "response": summary + "\n\nPlease confirm your appointment."}
            selected = self._selected_doctor(state)
            if selected:
                return {**state, "patient_phone": clean_phone, "appointment_step": "date", **self._show_doctor_availability(state, selected)}
            return {**state, "patient_phone": clean_phone, "appointment_step": "doctor", **self._show_doctor_selection(state)}

        if step == "doctor":
            return self._handle_doctor_step(state, text)

        if step == "doctor_confirm_fuzzy":
            return self._handle_fuzzy_confirmation(state, text)

        if step in {"date", "pre_patient_date"}:
            return self._handle_date_step(state, text)

        if step in {"slot", "pre_patient_slot"}:
            slot_id = text.removeprefix("slot:").strip()
            available = state.get("available_slots", [])
            # 1. Match by Slot ID
            slot = next((item for item in available if item.get("Slot ID", "").strip() == slot_id), None)
            # 2. Match by Start Time (e.g. '10:00 AM', '10:00', '10am', '10')
            if not slot:
                cleaned_text = text.lower().replace(" ", "").replace(":00", "")
                for s in available:
                    st = s.get("Start Time", "").lower().replace(" ", "")
                    st_simple = st.replace(":00", "")
                    if text.strip().lower() in st or cleaned_text in st_simple or st_simple in cleaned_text:
                        slot = s
                        slot_id = s.get("Slot ID", "")
                        break
            # 3. Match by 1-based index (e.g. '1', 'slot 1')
            if not slot and text.strip().isdigit():
                idx = int(text.strip()) - 1
                if 0 <= idx < len(available):
                    slot = available[idx]
                    slot_id = slot.get("Slot ID", "")

            if not slot:
                return {**state, "response": "That slot is no longer available. Please select another slot."}
            if step == "pre_patient_slot":
                return {
                    **state,
                    "slot_id": slot_id,
                    "appointment_time": slot.get("Start Time", ""),
                    "appointment_step": "name",
                    "ui": "",
                    "response": "Great. May I know your name?",
                }
            summary = self._summary(state, slot.get("Start Time", ""))
            return {**state, "slot_id": slot_id, "appointment_time": slot.get("Start Time", ""), "appointment_step": "confirmation", "ui": "confirm", "response": summary + "\n\nPlease confirm your appointment."}

        if step == "confirmation":
            if text.casefold() in {"change", "no", "cancel"}:
                return {**state, "appointment_step": "doctor", "ui": "", **self._show_doctor_selection(state)}
            if text.casefold() not in {"confirm", "yes", "book it"}:
                return {**state, "response": "Please select Confirm or Change."}
            if not self._slots or not self._patients:
                return {**state, "response": "Booking storage is not configured. Please contact the clinic team at " + self._support_phone + "."}
            try:
                patient_id = state.get("patient_id") or self._generate_patient_id()
                token_no = state.get("token_no") or self._generate_token()
                booking_result = self._slots.book_slot(state["slot_id"], patient_id, token_no)
            except Exception:
                logger.exception("Slot booking tool failed")
                return {**state, "response": "I couldn't reserve that slot right now. Please try again."}
            booked = booking_result.get("success", False) if isinstance(booking_result, dict) else booking_result
            if not booked:
                return {**state, "response": "That slot was just booked by someone else. Please choose another slot."}
            return {**state, "patient_id": patient_id, "token_no": token_no, "appointment_step": "payment", "ui": "payment", "response": "Your slot is reserved. Please choose a payment method."}

        if step == "payment":
            flags = state.get("feature_flags", {})
            from ..core.feature_flags import is_feature_enabled
            if text.casefold() in {"online", "payment_online"}:
                if not is_feature_enabled(flags, "online_payments"):
                    return {
                        **state,
                        "appointment_step": "payment",
                        "ui": "payment",
                        "response": "Online payment is currently disabled for this clinic. Please select 'Pay at Clinic' (Offline) to confirm your appointment.",
                    }
                return self._complete_online(state)

            offline_phrases = {"offline", "payment_offline", "pay at clinic", "clinic", "cash", "pay offline", "later"}
            if any(p in text.casefold() for p in offline_phrases):
                return self._complete_offline(state)
            return {**state, "response": "Please choose Online Payment or Offline Payment (Pay at Clinic)."}

        return {**state, "response": "Please continue with the appointment details."}

    # ------------------------------------------------------------------
    # Internal helpers — doctor selection
    # ------------------------------------------------------------------

    def _show_doctor_selection(self, state: GraphState) -> dict:
        """Return state fragment displaying available doctors in structured format with buttons."""
        if self._doctors is None:
            return {"response": "Doctor information is unavailable right now. Please contact the clinic team at " + self._support_phone + "."}
        doctors = self._doctors.get_active_doctors()
        if not doctors:
            return {"response": "No doctors are available right now. Please contact the clinic team at " + self._support_phone + "."}
        response = format_doctor_list_display(doctors)
        return {
            "doctor_choices": doctors[:_MAX_BUTTON_DOCTORS],
            "ui": "doctor_select",
            "response": response,
        }

    def _handle_doctor_step(self, state: GraphState, text: str) -> GraphState:
        """Process user input during the 'doctor' appointment step.

        Order of checks (all deterministic, zero LLM calls):
        1. Doctor ID callback (button click)
        2. Fuzzy name matching (handling typos, incomplete names, prefixes, extra words)
        3. Specialization keyword matching
        4. Health concern matching
        5. Ambiguous or unknown -> show matching or full doctor list
        """
        if self._doctors is None:
            return {**state, "response": "Doctor information is unavailable right now. Please contact the clinic team at " + self._support_phone + "."}

        all_active = self._doctors.get_active_doctors()

        # --- 1. Callback button: text is a Doctor ID ---
        by_id = [d for d in all_active if d.get("Doctor ID", "") == text]
        if by_id:
            return self._accept_doctor(state, by_id[0])

        # --- 2. Deterministic fuzzy name matching ---
        resolved = self._doctors.resolve_doctor(text)
        if resolved["status"] == "matched":
            return self._accept_doctor(state, resolved["doctor"])
        if resolved["status"] == "ambiguous":
            matches = resolved["matches"]
            intro = "Multiple doctors matched your request. Please choose one:"
            response = format_doctor_list_display(matches, intro=intro)
            return {
                **state,
                "doctor_fuzzy_candidate": matches[0],
                "appointment_step": "doctor_confirm_fuzzy",
                "doctor_choices": matches[:_MAX_BUTTON_DOCTORS],
                "ui": "doctor_select",
                "response": response,
            }

        # --- 3. Specialization keyword match ---
        spec_canonical = resolve_specialization(text)
        if spec_canonical:
            spec_doctors = self._doctors.get_doctors_by_specialization(spec_canonical)
            if len(spec_doctors) == 1:
                return self._accept_doctor(state, spec_doctors[0])
            if spec_doctors:
                intro = f"Our available {spec_canonical.title()} specialist(s):"
                response = format_doctor_list_display(spec_doctors, intro=intro)
                return {**state, "doctor_choices": spec_doctors[:_MAX_BUTTON_DOCTORS], "ui": "doctor_select", "response": response}

        # --- 4. Health concern keyword match ---
        concern_phrase, concern_spec = match_health_concern(text)
        if concern_spec:
            concern_doctors = self._doctors.get_doctors_by_specialization(concern_spec)
            if len(concern_doctors) == 1:
                return self._accept_doctor(state, concern_doctors[0])
            if concern_doctors:
                spec_name = concern_doctors[0].get("Specialization", concern_spec.title())
                intro = f"For health concerns related to {concern_phrase}, you may consult our {spec_name} specialist(s):"
                response = (
                    format_doctor_list_display(concern_doctors, intro=intro)
                    + "\n\n*(Note: This is informational based on our clinic specialties and not medical advice.)*"
                )
                return {**state, "doctor_choices": concern_doctors[:_MAX_BUTTON_DOCTORS], "ui": "doctor_select", "response": response}

        # --- 5. No reliable match — check if question or unknown doctor ---
        lowered = text.casefold().strip()
        is_question = "?" in text or any(w in lowered.split() for w in ("kahan", "kaha", "kidhar", "address", "timing", "kab", "fees", "fee", "kitna", "kitne", "pata", "location", "samay", "parking"))

        rag_answer = ""
        flags = state.get("feature_flags", {})
        from ..core.feature_flags import is_feature_enabled, FEATURE_AI_AGENT
        if is_feature_enabled(flags, FEATURE_AI_AGENT, default=True) and is_question:
            from ..tools.rag_tool import search_clinic_knowledge
            retrieved = search_clinic_knowledge(self._rag, text, tenant_id=state.get("tenant_id")) if self._rag else []
            if retrieved:
                rag_answer = retrieved[0] if isinstance(retrieved[0], str) else str(retrieved[0])

        support_phone = state.get("support_phone") or self._support_phone
        if all_active:
            if rag_answer:
                intro = f"{rag_answer}\n\n*(Aapka appointment booking chalu hai. Kripya niche diye gaye doctors me se chunein ya doctor ka naam batayein:)*"
            elif is_question:
                intro = f"Hamare clinic ki information:\nTimings: 9:00 AM - 8:00 PM | Helpline: {support_phone}\n\nAap kis doctor ke sath appointment schedule karna chahte hain? Available doctors:"
            else:
                intro = f"'{text}' naam se doctor match nahi hue.\nKya aap doctor ka poora naam bata sakte hain?\n\nOur available doctors are:"
            response = format_doctor_list_display(all_active, intro=intro)
            return {**state, "doctor_choices": all_active[:_MAX_BUTTON_DOCTORS], "ui": "doctor_select", "response": response}

        return {**state, "response": "No doctors are available right now. Please contact the clinic team at " + self._support_phone + "."}

    def _handle_fuzzy_confirmation(self, state: GraphState, text: str) -> GraphState:
        """Handle choice when ambiguous doctor candidates are presented."""
        lowered = text.casefold().strip()
        candidate = state.get("doctor_fuzzy_candidate", {})

        is_yes = lowered in {"yes", "yes, confirm", "confirm"} or text == candidate.get("Doctor ID", "__")
        if is_yes and candidate:
            return self._accept_doctor(state, candidate)

        # Check if user typed or tapped one of the active doctors
        all_active = self._doctors.get_active_doctors() if self._doctors else []
        by_id = [d for d in all_active if d.get("Doctor ID", "") == text]
        if by_id:
            return self._accept_doctor(state, by_id[0])

        resolved = self._doctors.resolve_doctor(text) if self._doctors else {"status": "not_found"}
        if resolved["status"] == "matched":
            return self._accept_doctor(state, resolved["doctor"])

        intro = "No problem. Our available doctors are:"
        response = format_doctor_list_display(all_active, intro=intro)
        return {
            **state,
            "doctor_fuzzy_candidate": {},
            "appointment_step": "doctor",
            "doctor_choices": all_active[:_MAX_BUTTON_DOCTORS],
            "ui": "doctor_select",
            "response": response,
        }

    def _accept_doctor(self, state: GraphState, doctor: dict) -> GraphState:
        """Commit doctor selection and show actual upcoming appointment slots."""
        amount = doctor.get("Consultation Fee", "")
        if not amount:
            return {**state, "response": "The consultation fee is unavailable, so I cannot continue this booking."}
        draft = dict(state.get("appointment_draft") or {})
        draft["doctor_id"] = doctor.get("Doctor ID", "")
        draft["doctor_name"] = doctor.get("Doctor Name", "")
        draft["doctor_specialization"] = doctor.get("Specialization", "")
        selected = {
            **state,
            **self._doctor_details(doctor),
            "active_flow": "appointment_booking",
            "appointment_draft": draft,
            "appointment_step": "date",
            "pending_field": "date",
            "doctor_choices": [],
            "doctor_fuzzy_candidate": {},
            "ui": "",
        }
        if hasattr(self._slots, "get_upcoming_available_slots"):
            res = self._show_doctor_availability(selected, doctor)
            res["active_flow"] = "appointment_booking"
            res["appointment_draft"] = draft
            res["doctor_name"] = doctor.get("Doctor Name", "")
            res["appointment_step"] = "date"
            res["pending_field"] = "date"
            return res
        # Compatibility for existing lightweight slot adapters. Production
        # uses AppointmentTools, which implements the availability query.
        return {**selected, "response": "What date would you prefer? Please use YYYY-MM-DD."}

    def _handle_date_step(self, state: GraphState, text: str) -> GraphState:
        if not self._slots or not state.get("doctor_name"):
            return {**state, "response": "Appointment slots are not configured yet. Please contact the clinic team at " + self._support_phone + "."}
        selected = self._selected_doctor(state)
        if self._is_availability_request(text) and selected:
            resolved = self._doctors.resolve_doctor(text) if self._doctors else {"status": "not_found"}
            doctor = resolved.get("doctor") if resolved.get("status") == "matched" else selected
            target = parse_date_from_text(text, self._clinic_today())
            return self._show_doctor_availability(state, doctor, target.get("date") if target.get("success") else None)

        # A named doctor at this point means the patient wants to change the
        # selected doctor, not that the date is invalid.
        if self._doctors is not None:
            resolved = self._doctors.resolve_doctor(text)
            if resolved.get("status") == "matched" and resolved["doctor"].get("Doctor ID") != state.get("doctor_id"):
                return self._accept_doctor(state, resolved["doctor"])

        date_result = parse_date(text, self._clinic_today())
        if not date_result["success"]:
            return {**state, "response": date_result["message"]}
        normalized_date = date_result["date"]
        available_result = self._slots.get_available_slots(state["doctor_name"], normalized_date)
        if isinstance(available_result, dict) and not available_result.get("success"):
            return {**state, "response": "I couldn't check availability right now. Please try again or contact clinic support at " + self._support_phone + "."}
        available = available_result.get("slots", []) if isinstance(available_result, dict) else available_result
        if not available:
            if selected and hasattr(self._slots, "get_upcoming_available_slots"):
                return self._show_doctor_availability(state, selected, normalized_date)
            return {**state, "response": "No available slots were found for that date. Please choose another date."}
        next_step = "pre_patient_slot" if state.get("appointment_step") == "pre_patient_date" else "slot"
        times = ", ".join(self._format_time(slot.get("Start Time", "")) for slot in available)
        return {
            **state,
            "appointment_date": normalized_date,
            "available_slots": available,
            "appointment_step": next_step,
            "ui": "slots",
            "response": f"Available slots on {date_result['display_date']}: {times}. Which time would you prefer?",
        }

    # ------------------------------------------------------------------
    # Summary / offline / helpers
    # ------------------------------------------------------------------

    def _summary(self, state: GraphState, appointment_time: str) -> str:
        return f"Appointment Summary\n\nPatient: {state.get('patient_name', '')}\nDoctor: {state.get('doctor_name', '')}\nDate: {state.get('appointment_date', '')}\nTime: {appointment_time}\nConsultation Fee: {state.get('amount', '')}"

    def _complete_offline(self, state: GraphState) -> GraphState:
        if state.get("token_no") and state.get("booking_status") == "Confirmed":
            return state
        try:
            token_no = state["token_no"]
            payment = self._payments.record_offline_payment(state["amount"]) if self._payments else {"success": True, "payment_method": "Offline", "payment_status": "Pending", "amount": state["amount"]}
            if not payment.get("success", False):
                raise RuntimeError("Offline payment state could not be recorded")
            record_result = self._patients.create_patient(PatientRecord(name=state["patient_name"], phone=state["patient_phone"], email=state["patient_email"], doctor=state["doctor_name"], appointment_date=state["appointment_date"], appointment_time=state["appointment_time"], token_no=token_no, amount=state["amount"], payment_method="Offline", payment_status="Pending", booking_status="Confirmed", status="Confirmed", patient_id=state["patient_id"]))
            record = record_result.get("patient") if isinstance(record_result, dict) else record_result
            if isinstance(record_result, dict) and not record_result.get("success"):
                raise RuntimeError(record_result.get("message", "Patient write failed"))
        except Exception:
            logger.exception("Offline appointment completion failed")
            if self._slots:
                self._slots.release_slot_if_needed(state.get("slot_id", ""), state.get("patient_id"))
            return {**state, "response": "I couldn't complete the booking right now. Please try again or contact clinic support at " + self._support_phone + "."}
        pat_name = record.get("name", record.get("Name", state.get("patient_name", ""))) if isinstance(record, dict) else getattr(record, "name", state.get("patient_name", ""))
        pat_email = record.get("email", record.get("Email", state.get("patient_email", ""))) if isinstance(record, dict) else getattr(record, "email", state.get("patient_email", ""))
        pat_phone = record.get("phone", record.get("Phone", state.get("patient_phone", ""))) if isinstance(record, dict) else getattr(record, "phone", state.get("patient_phone", ""))

        try:
            qr_path = ""
            upi_id = ""
            if self._payments:
                try:
                    qr_result = self._payments.generate_offline_upi_qr(state["amount"], self._clinic_name, token_no, Path("data/invoices"))
                    if qr_result.get("success"):
                        qr_path = qr_result.get("qr_path", "")
                        upi_id = qr_result.get("upi_id", "") or (getattr(self._payments, "upi_id", "") if self._payments else "")
                except Exception:
                    pass
            invoice_data = InvoiceData(
                self._clinic_name,
                self._support_phone,
                "",
                "",
                pat_name,
                pat_email,
                pat_phone,
                state["doctor_name"],
                state.get("specialization", ""),
                state["appointment_date"],
                state["appointment_time"],
                token_no,
                state["amount"],
                "Pay at Clinic / UPI",
                "Pending",
                qr_path,
                upi_id=upi_id,
            )
            invoice_result = self._invoices.generate_invoice(invoice_data, Path("data/invoices"))
            if not invoice_result.get("success"):
                raise RuntimeError("Invoice generation failed")
            invoice_number, invoice_path = invoice_result["invoice_number"], Path(invoice_result["file_path"])
        except Exception:
            logger.exception("Invoice generation failed after appointment confirmation")
            return {**state, "token_no": token_no, "payment_method": "Offline", "payment_status": "Pending", "booking_status": "Confirmed", "appointment_step": "complete", "ui": "main", "response": "Your appointment is confirmed, but I couldn't generate the invoice. Please contact clinic support at " + self._support_phone + "."}
        email_sent = False
        if self._gmail:
            try:
                email_result = self._gmail.send_invoice_email(pat_email, invoice_number, f"Appointment Confirmation & Invoice - {self._clinic_name}", "Your appointment is confirmed. Payment is pending and payable at the clinic.", str(invoice_path))
                email_sent = email_result.get("success", False)
            except Exception:
                logger.exception("Invoice email delivery failed after appointment confirmation")
        response = f"Appointment confirmed.\n\nToken: {token_no}\nDoctor: {state['doctor_name']}\nDate: {state['appointment_date']}\nTime: {state['appointment_time']}\nAmount: {state['amount']}\nPayment: Pay at Clinic\nInvoice: {'sent to your email' if email_sent else 'generated; email delivery failed'}"
        last_booked = {
            "token_no": token_no,
            "appointment_id": token_no,
            "doctor_name": state["doctor_name"],
            "doctor": state["doctor_name"],
            "appointment_date": state["appointment_date"],
            "date": state["appointment_date"],
            "appointment_time": state["appointment_time"],
            "time": state["appointment_time"],
            "patient_name": pat_name,
            "name": pat_name,
            "patient_phone": pat_phone,
            "phone": pat_phone,
            "patient_email": pat_email,
            "amount": state["amount"],
            "payment_method": "Offline (Pay at Clinic)",
            "payment_status": "Pending",
            "booking_status": "Confirmed",
            "status": "Confirmed",
        }
        return {
            **state,
            "token_no": token_no,
            "payment_method": "Offline",
            "payment_status": "Pending",
            "booking_status": "Confirmed",
            "invoice_number": invoice_number,
            "invoice_path": str(invoice_path),
            "email_sent": email_sent,
            "appointment_step": "complete",
            "last_booked_appointment": last_booked,
            "recent_context": {"last_action": "booking_confirmed", "appointment": last_booked},
            "ui": "main",
            "response": response,
        }

    def _complete_online(self, state: GraphState) -> GraphState:
        if state.get("token_no") and state.get("booking_status") == "Confirmed" and state.get("payment_url"):
            return state

        clinic_name = state.get("clinic_name") or self._clinic_name
        support_phone = state.get("support_phone") or self._support_phone
        token_no = state.get("token_no") or self._generate_token()
        patient_id = state.get("patient_id") or self._generate_patient_id()
        tenant_id = state.get("tenant_id") or "default"
        amt = state.get("amount") or state.get("fee") or "500"
        pat_name = state.get("patient_name") or state.get("user_name") or "Patient"
        pat_phone = state.get("patient_phone") or state.get("user_phone") or ""
        pat_email = state.get("patient_email") or state.get("user_email") or ""
        doc_name = state.get("doctor_name", "")
        appt_date = state.get("appointment_date") or state.get("date") or ""
        appt_time = state.get("appointment_time") or state.get("time") or ""

        try:
            payment = self._payments.create_online_payment(
                amount=amt,
                clinic_name=clinic_name,
                patient_name=pat_name,
                patient_phone=pat_phone,
                appointment_id=token_no,
                doctor_name=doc_name,
                tenant_id=tenant_id,
            ) if self._payments else {
                "success": True,
                "payment_id": f"PAY-{token_no}",
                "payment_url": f"https://rzp.io/i/{token_no.lower()}",
                "upi_id": "",
                "upi_uri": "",
            }

            if self._patients and hasattr(self._patients, "create_patient"):
                record_result = self._patients.create_patient(
                    PatientRecord(
                        name=pat_name,
                        phone=pat_phone,
                        email=pat_email,
                        doctor=doc_name,
                        appointment_date=appt_date,
                        appointment_time=appt_time,
                        token_no=token_no,
                        amount=amt,
                        payment_method="Razorpay / UPI",
                        payment_status="Pending",
                        booking_status="Confirmed",
                        status="Confirmed",
                        patient_id=patient_id,
                    )
                )
                if isinstance(record_result, dict) and not record_result.get("success"):
                    raise RuntimeError(record_result.get("message", "Patient write failed"))

        except Exception:
            logger.exception("Online appointment completion failed")
            if self._slots:
                self._slots.release_slot_if_needed(state.get("slot_id", ""), patient_id)
            fallback_msg = "I couldn't generate the online payment link right now. Please select 'Pay at Clinic' (Offline) or contact clinic support at " + support_phone + "."
            return {
                **state,
                "response": fallback_msg,
                "reply": fallback_msg,
            }

        pay_url = payment.get("payment_url") or payment.get("short_url") or f"https://rzp.io/i/{token_no.lower()}"
        upi_id = payment.get("upi_id") or ""
        upi_uri = payment.get("upi_uri") or (f"upi://pay?pa={upi_id}&pn={clinic_name}&am={amt}&cu=INR&tr={token_no}" if upi_id else "")
        upi_section = f"📱 *Direct UPI Payment:*\nUPI ID: `{upi_id}`\nUPI Deep Link: {upi_uri}\n\n" if upi_id else ""

        response_msg = (
            f"🎉 *Appointment Confirmed!*\n\n"
            f"🏥 *Facility:* {clinic_name}\n"
            f"🔖 *Token / Booking ID:* {token_no}\n"
            f"👨‍⚕️ *Doctor:* Dr. {doc_name}\n"
            f"📅 *Schedule:* {appt_date} at {appt_time}\n\n"
            f"💳 *Online Payment (Razorpay & UPI):*\n"
            f"💰 Consultation Fee: ₹{amt}\n\n"
            f"🔗 *Pay via Razorpay Link (Cards/NetBanking/UPI):*\n"
            f"{pay_url}\n\n"
            f"{upi_section}"


            f"_(Payment complete hone ke baad clinic verification auto-update ho jayega. Aap clinic par cash se bhi pay kar sakte hain.)*"
        )

        last_booked = {
            "token_no": token_no,
            "appointment_id": token_no,
            "doctor_name": doc_name,
            "doctor": doc_name,
            "appointment_date": appt_date,
            "date": appt_date,
            "appointment_time": appt_time,
            "time": appt_time,
            "patient_name": pat_name,
            "name": pat_name,
            "patient_phone": pat_phone,
            "phone": pat_phone,
            "patient_email": pat_email,
            "amount": amt,
            "payment_method": "Razorpay / UPI",
            "payment_status": "Pending",
            "booking_status": "Confirmed",
            "status": "Confirmed",
            "payment_url": pay_url,
            "upi_id": upi_id,
        }

        return {
            **state,
            "flow": "complete",
            "appointment_step": "complete",
            "ui": "main",
            "token_no": token_no,
            "patient_id": patient_id,
            "payment_id": payment.get("payment_id"),
            "payment_url": pay_url,
            "upi_id": upi_id,
            "upi_uri": upi_uri,
            "payment_method": "Razorpay / UPI",
            "payment_status": "Pending",
            "booking_status": "Confirmed",
            "last_booked_appointment": last_booked,
            "recent_context": {"last_action": "booking_confirmed", "appointment": last_booked},
            "response": response_msg,
            "reply": response_msg,
        }

    def _generate_patient_id(self) -> str:
        result = self._patients.generate_patient_id() if hasattr(self._patients, "generate_patient_id") else {"patient_id": self._patients.new_patient_id()}
        return result["patient_id"]

    def _generate_token(self) -> str:
        result = self._patients.generate_token() if hasattr(self._patients, "generate_token") else {"token_no": self._patients.next_token()}
        return result["token_no"]

    def _release_slot(self, slot_id: str, patient_id: str) -> None:
        if hasattr(self._slots, "release_slot"):
            self._slots.release_slot(slot_id, patient_id)
        else:
            self._slots.release_slot_if_needed(slot_id, patient_id)

    def greeting_node(self, state: GraphState) -> GraphState:
        logger.info(">>> [AGENT NODE TRIGGERED] 'greeting' | user_text=%r", state.get("user_text", ""))
        text = state.get("user_text", "")
        if _is_hindi_or_hinglish(text):
            welcome_text = (
                f"Namaste! 🙏 *{self._clinic_name}* me aapka swagat hai.\n\n"
                "Main aapka AI assistant hoon. Main aapki kya madad kar sakta hoon?\n\n"
                "Aap neeche diye gaye options me se chun sakte hain ya apna sawal sidhe pooch sakte hain:"
            )
        else:
            welcome_text = (
                f"Hello! 👋 Welcome to *{self._clinic_name}*.\n\n"
                "How may I help you today?\n\n"
                "Please select an option below or feel free to type your query directly:"
            )
        is_first_time = not state.get("welcome_menu_sent")
        return {
            **state,
            "response": welcome_text,
            "ui": "welcome_menu" if is_first_time else "",
        }

    def report_response(self, state: GraphState) -> GraphState:
        logger.info(">>> [AGENT NODE TRIGGERED] 'report_response' | user_text=%r", state.get("user_text", ""))
        patient_phone = state.get("patient_phone", "")
        found_reports = []
        if self._crm and patient_phone:
            try:
                pts = self._crm.patients.get_patients() if self._crm.patients else []
                matching_pts = [p for p in pts if p.get("Phone", "").strip() == str(patient_phone).strip()]
                for p in matching_pts:
                    pid = p.get("Patient ID", "")
                    rxs = self._crm.prescriptions.list_prescriptions(patient_id=pid) if hasattr(self._crm, "prescriptions") else []
                    found_reports.extend(rxs)
            except Exception:
                pass

        if found_reports:
            summary_lines = [f"- Prescription #{rx.get('id', '')} by Dr. {rx.get('doctor_name', 'Doctor')} on {str(rx.get('created_at', ''))[:10]}" for rx in found_reports[:3]]
            if _is_hindi_or_hinglish(state.get("user_text", "")):
                res = f"Aapke digital prescriptions mil gaye hain:\n\n" + "\n".join(summary_lines) + f"\n\nKisi bhi lab test report ke liye aap clinic help desk par call kar sakte hain: {self._support_phone}."
            else:
                res = f"Here are your latest digital prescriptions:\n\n" + "\n".join(summary_lines) + f"\n\nFor diagnostic lab test reports, please contact our laboratory reception at {self._support_phone}."
            return {**state, "response": res}

        clinic_name = state.get("clinic_name") or self._clinic_name
        support_phone = state.get("support_phone") or self._support_phone

        if _is_hindi_or_hinglish(state.get("user_text", "")):
            msg = (
                f"📄 *Lab Reports & Prescriptions:*\n\n"
                f"Aapke lab reports aur test results hamare clinic diagnostic record me surakshit hain. "
                f"Apna latest report WhatsApp par prapt karne ya sthiti janne ke liye, kripya clinic help desk par sampark karein:\n\n"
                f"📞 Helpdesk: {support_phone}\n"
                f"🏥 {clinic_name}"
            )
        else:
            msg = (
                f"📄 *Lab Reports & Prescriptions:*\n\n"
                f"Your diagnostic lab test reports and digital prescriptions are maintained at {clinic_name}. "
                f"To retrieve your latest official lab report or enquire about test status, please reach our helpdesk:\n\n"
                f"📞 Contact: {support_phone}\n"
                f"🏥 {clinic_name}"
            )
        return {**state, "response": msg}

    def human_support(self, state: GraphState) -> GraphState:
        clinic_name = state.get("clinic_name") or self._clinic_name
        support_phone = state.get("support_phone") or self._support_phone
        return {**state, "response": f"Please contact the {clinic_name} team at {support_phone}."}

    def answer(self, state: GraphState) -> GraphState:
        logger.info(">>> [AGENT NODE TRIGGERED] 'answer' (LLM/Gemini) | user_text=%r", state.get("user_text", ""))
        clinic_name = state.get("clinic_name") or self._clinic_name
        support_phone = state.get("support_phone") or self._support_phone
        if state.get("intent") == "doctor_information" and not state.get("doctor_context"):
            return {**state, "response": "I couldn't verify doctor information right now. Please contact the clinic team at " + support_phone + "."}
        context = list(state.get("clinic_context", []))
        context += ["Structured doctor record: " + ", ".join(f"{key}={value}" for key, value in doctor.items()) for doctor in state.get("doctor_context", [])]
        if state.get("conversation_summary"):
            context.append(f"Previous conversation summary:\n{state['conversation_summary']}")
        if state.get("patient_name"):
            context.append(f"Patient name: {state['patient_name']}")

        history = state.get("messages", [])
        user_msg = state.get("user_text", "")
        is_greeting = state.get("intent") == "greeting" or (
            user_msg.strip().lower() in ("hi", "hii", "hello", "hey", "namaste", "hola", "salam")
            and not state.get("appointment_step")
        )

        try:
            try:
                response = self._llm.answer(
                    load_system_prompt(clinic_name, support_phone),
                    user_msg,
                    context,
                    history=history,
                )
            except TypeError:
                response = self._llm.answer(
                    load_system_prompt(clinic_name, support_phone),
                    user_msg,
                    context,
                )
        except Exception:
            logger.exception("Gemini completion failed")
            if is_greeting:
                if _is_hindi_or_hinglish(user_msg):
                    response = f"Namaste! {clinic_name} mein aapka swagat hai. Main aapki kya sahayata kar sakta hoon?\n\nAap appointment book kar sakte hain, doctor timings dekh sakte hain, ya clinic services ke baare mein pooch sakte hain."
                else:
                    response = f"Hello! Welcome to {clinic_name}. How can I assist you today?\n\nYou can book an appointment, check doctor timings, or enquire about our clinic services."
            else:
                if _is_hindi_or_hinglish(user_msg):
                    response = f"{clinic_name} mein aapka swagat hai. Appointment book karne ke liye 'Book appointment' likhein ya clinic helpline par direct call karein: {support_phone}."
                else:
                    response = f"Welcome to {clinic_name}. To book an appointment, reply with 'Book appointment' or call our clinic helpline at {support_phone}."
        logger.info("Gemini response generated")

        # If user asked a side question mid-booking, add continuation reminder
        active_step = state.get("appointment_step")
        resume_ctx = state.get("resume_context")
        pending_target = (resume_ctx.get("pending_field") if resume_ctx else None) or active_step

        if active_step and active_step != "complete":
            doc_name = state.get("doctor_name", "")
            doc_hint = f" with Dr. {doc_name}" if doc_name else ""
            step_prompt_hi = "Kripya apna agla detail batayein."
            step_prompt_en = "Please continue whenever you are ready."
            if pending_target == "doctor":
                step_prompt_hi = "Aap kis doctor ke sath appointment book karna chahte hain?"
                step_prompt_en = "Which doctor would you like to consult?"
            elif pending_target == "phone":
                step_prompt_hi = "Kripya apna 10-digit mobile number share karein."
                step_prompt_en = "Please share your 10-digit mobile number."
            elif pending_target == "name":
                step_prompt_hi = "Kripya patient ka poora naam share karein."
                step_prompt_en = "Please share the patient's full name."
            elif pending_target in {"date", "pre_patient_date"}:
                step_prompt_hi = "Kripya apni preferred date batayein."
                step_prompt_en = "Please provide your preferred appointment date."
            elif pending_target in {"slot", "pre_patient_slot"}:
                step_prompt_hi = "Kripya apna preferred time slot select karein."
                step_prompt_en = "Please select your preferred time slot."
            elif pending_target == "email":
                step_prompt_hi = "Kripya confirmation ke liye apna email address share karein (ya 'skip' likhein)."
                step_prompt_en = "Please provide your email address, or type 'skip'."

            if _is_hindi_or_hinglish(state.get("user_text", "")):
                reminder = f"\n\n*(Aapka appointment booking{doc_hint} chalu hai. {step_prompt_hi})*"
            else:
                reminder = f"\n\n*(Your appointment booking{doc_hint} is still active. {step_prompt_en})*"
            response = response + reminder

        # If intent is greeting, attach welcome_menu for interactive quick buttons (1st time only)
        is_first_greeting = is_greeting and not state.get("welcome_menu_sent")
        extra_ui = {"ui": "welcome_menu"} if is_first_greeting else {"ui": ""}

        return {**state, **extra_ui, "response": response}

    # ------------------------------------------------------------------
    # Reschedule & Cancellation Flow
    # ------------------------------------------------------------------

    def _extract_identifier_from_text(self, text: str) -> str | None:
        """Extract appointment token, patient ID, or phone number from user text."""
        import re
        t = text.strip()
        if t.startswith("appt:"):
            return t.removeprefix("appt:").strip()

        # Match Token like TKN-0001
        m_token = re.search(r"\b(TKN[-_]?\d+)\b", t, re.IGNORECASE)
        if m_token:
            return m_token.group(1).upper().replace("_", "-")

        # Match PAT-1234
        m_pat = re.search(r"\b(PAT[-_]?\d+)\b", t, re.IGNORECASE)
        if m_pat:
            return m_pat.group(1).upper().replace("_", "-")

        # Strip non-digits to test phone number
        digits = "".join(ch for ch in t if ch.isdigit())
        if len(digits) == 10 and digits[0] in "6789":
            return digits
        if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
            return digits[2:]

        return None

    def _find_patient_appointments(self, state: GraphState, text: str = "") -> tuple[list[dict], str | None]:
        """Find upcoming appointments for patient by text, token, phone, name, or patient ID."""
        ident = self._extract_identifier_from_text(text) if text else None
        if not ident and text and state.get("reschedule_step") == "ask_identifier":
            ident = text.strip()
        if not ident:
            ident = (
                state.get("reschedule_appointment_id")
                or state.get("cancel_appointment_id")
                or state.get("token_no")
                or state.get("patient_phone")
                or state.get("phone")
                or state.get("patient_name")
                or state.get("patient_id")
            )
        if not ident:
            return [], None

        if self._crm is None:
            return [], ident

        appts = self._crm.get_patient_upcoming_appointments(
            phone_or_id=ident,
            today_str=self._clinic_today().isoformat(),
        )
        return appts, ident

    def reschedule_node(self, state: GraphState) -> GraphState:
        flags = state.get("feature_flags", {})
        clinic_name = state.get("clinic_name", self._clinic_name)
        support_phone = state.get("support_phone", self._support_phone)
        from ..core.feature_flags import is_feature_enabled, get_disabled_feature_message
        if not is_feature_enabled(flags, "rescheduling"):
            return {
                **state,
                "reschedule_step": "",
                "ui": "main",
                "response": get_disabled_feature_message("rescheduling", clinic_name, support_phone),
            }

        step = state.get("reschedule_step")
        text = state.get("user_text", "").strip()


        # STEP: Ask identifier
        if step == "ask_identifier":
            ident = self._extract_identifier_from_text(text)
            if not ident:
                clean_digits = "".join(filter(str.isdigit, text))
                if len(clean_digits) == 10:
                    ident = clean_digits
                elif text.upper().startswith("TKN"):
                    ident = text.upper()
                else:
                    return {
                        **state,
                        "response": "Please provide a valid 10-digit phone number or Appointment Token (e.g. TKN-0001).",
                    }

            appts = self._crm.get_patient_upcoming_appointments(ident, today_str=self._clinic_today().isoformat())
            if not appts:
                return {
                    **state,
                    "reschedule_step": "",
                    "ui": "main",
                    "response": f"I couldn't find any upcoming confirmed appointments for '{ident}'. If you would like to book a new appointment, please choose 'Book Appointment'.",
                }
            if len(appts) == 1:
                appt = appts[0]
                token = appt.get("token_no") or appt.get("appointment_id")
                return {
                    **state,
                    "reschedule_step": "select_date",
                    "reschedule_appointment_id": token,
                    "doctor_name": appt.get("doctor"),
                    "appointment_date": appt.get("date"),
                    "appointment_time": appt.get("time"),
                    "patient_id": appt.get("patient_id"),
                    "patient_phone": appt.get("phone", ""),
                    "token_no": token,
                    "ui": "",
                    "response": (
                        f"Found your appointment:\n\n"
                        f"👨‍⚕️ Doctor: {appt.get('doctor')}\n"
                        f"📅 Current Schedule: {appt.get('date')} at {appt.get('time')}\n"
                        f"🎫 Token: {token}\n\n"
                        f"What new date would you prefer? You can say 'tomorrow', 'next Monday', or reply with a date (YYYY-MM-DD)."
                    ),
                }
            return {
                **state,
                "reschedule_step": "select_appointment",
                "upcoming_appointments": appts,
                "ui": "select_appointment",
                "response": "You have multiple upcoming appointments. Please select the one you would like to reschedule:",
            }

        # STEP: Select appointment from multiple
        if step == "select_appointment":
            token = self._extract_identifier_from_text(text) or text
            appts = state.get("upcoming_appointments", [])
            chosen = next((a for a in appts if (a.get("token_no") == token or a.get("appointment_id") == token)), None)
            if not chosen:
                chosen = self._crm.get_appointment(token)
            if not chosen:
                return {
                    **state,
                    "response": "Please tap one of the appointments above to select it.",
                }
            chosen_token = chosen.get("token_no") or chosen.get("appointment_id")
            return {
                **state,
                "reschedule_step": "select_date",
                "reschedule_appointment_id": chosen_token,
                "doctor_name": chosen.get("doctor"),
                "appointment_date": chosen.get("date"),
                "appointment_time": chosen.get("time"),
                "patient_id": chosen.get("patient_id"),
                "token_no": chosen_token,
                "ui": "",
                "response": (
                    f"Selected appointment with Dr. {chosen.get('doctor')} on {chosen.get('date')} at {chosen.get('time')}.\n\n"
                    f"What new date would you like to move it to? (You can say 'tomorrow', 'next Monday', or a date like YYYY-MM-DD)."
                ),
            }

        # STEP: Select date
        if step == "select_date":
            date_res = parse_date_from_text(text, self._clinic_today())
            if not date_res["success"]:
                return {**state, "response": date_res["message"] + " Please tell me a date (e.g., 'tomorrow', 'Friday', or YYYY-MM-DD)."}
            target_date = date_res["date"]
            doc_name = state.get("doctor_name", "")
            if not doc_name and state.get("reschedule_appointment_id"):
                existing = self._crm.get_appointment(state["reschedule_appointment_id"])
                if existing:
                    doc_name = existing.get("doctor", "")

            slots_res = self._slots.get_available_slots(doc_name, target_date)
            open_slots = slots_res.get("slots", []) if isinstance(slots_res, dict) else slots_res
            if not open_slots:
                return {
                    **state,
                    "response": f"Dr. {doc_name} has no available slots on {date_res['display_date']}. Please choose another date.",
                }
            times_str = ", ".join(self._format_time(s.get("Start Time", "")) for s in open_slots)
            return {
                **state,
                "target_reschedule_date": target_date,
                "available_slots": open_slots,
                "reschedule_step": "select_slot",
                "ui": "slots",
                "response": (
                    f"Available slots for Dr. {doc_name} on {date_res['display_date']}:\n{times_str}\n\n"
                    f"Please tap or reply with your preferred time slot:"
                ),
            }

        # STEP: Select slot
        if step == "select_slot":
            slot_id = text.removeprefix("slot:").strip()
            slot = next((s for s in state.get("available_slots", []) if s.get("Slot ID") == slot_id), None)
            if not slot:
                slot = next((s for s in state.get("available_slots", []) if s.get("Start Time", "").strip().casefold() == text.strip().casefold()), None)
            if not slot:
                return {**state, "response": "That slot is not available. Please choose a slot from the buttons above."}

            curr_appt_id = state.get("reschedule_appointment_id") or state.get("token_no")
            old_date = state.get("appointment_date", "")
            old_time = state.get("appointment_time", "")
            new_date = slot.get("Date") or state.get("target_reschedule_date")
            new_time = slot.get("Start Time")
            doc = state.get("doctor_name", "")

            summary = (
                f"🔄 **Reschedule Confirmation**\n\n"
                f"**Current Schedule:**\n"
                f"• Doctor: {doc}\n"
                f"• Date & Time: {old_date} at {old_time}\n"
                f"• Token: {curr_appt_id}\n\n"
                f"**New Schedule:**\n"
                f"• Doctor: {doc}\n"
                f"• Date & Time: {new_date} at {new_time}\n\n"
                f"Would you like to confirm this reschedule?"
            )
            return {
                **state,
                "reschedule_target_slot": slot,
                "reschedule_step": "confirm",
                "ui": "reschedule_confirm",
                "response": summary,
            }

        # STEP: Confirmation
        if step == "confirm":
            if text.casefold() in {"cancel_reschedule", "no", "keep", "nahi", "change", "cancel"}:
                old_date = state.get("appointment_date", "")
                old_time = state.get("appointment_time", "")
                doc = state.get("doctor_name", "")
                return {
                    **state,
                    "reschedule_step": "",
                    "reschedule_target_slot": {},
                    "ui": "main",
                    "response": f"Understood. Your original appointment with Dr. {doc} on {old_date} at {old_time} remains unchanged and confirmed.",
                }
            if text.casefold() not in {"confirm_reschedule", "confirm", "yes", "haan", "theek hai"}:
                return {**state, "response": "Please confirm by tapping 'Confirm Reschedule' or 'Keep Current Booking'."}

            curr_appt_id = state.get("reschedule_appointment_id") or state.get("token_no")
            slot = state.get("reschedule_target_slot", {})
            new_slot_id = slot.get("Slot ID", "")
            new_date = slot.get("Date") or state.get("target_reschedule_date", "")
            new_time = slot.get("Start Time", "")
            doc = state.get("doctor_name", "")

            try:
                res = self._crm.reschedule_appointment(
                    identifier=curr_appt_id,
                    new_slot_id=new_slot_id,
                    new_date=new_date,
                    new_time=new_time,
                )
                success_msg = (
                    f"✅ **Appointment Rescheduled Successfully!**\n\n"
                    f"• Doctor: {doc}\n"
                    f"• New Date: {new_date}\n"
                    f"• New Time: {new_time}\n"
                    f"• Token: {curr_appt_id}\n\n"
                    f"Your appointment is confirmed. See you at the clinic!"
                )
                return {
                    **state,
                    "appointment_date": new_date,
                    "appointment_time": new_time,
                    "slot_id": new_slot_id,
                    "reschedule_step": "",
                    "reschedule_target_slot": {},
                    "ui": "main",
                    "response": success_msg,
                }
            except Exception as err:
                logger.exception("Chatbot appointment reschedule failed")
                return {
                    **state,
                    "reschedule_step": "",
                    "ui": "main",
                    "response": f"I couldn't reschedule the appointment: {err}. Please contact our clinic desk at {self._support_phone}.",
                }

        # INITIAL ENTRY: No step set yet
        appts, ident = self._find_patient_appointments(state, text)
        if not ident:
            return {
                **state,
                "reschedule_step": "ask_identifier",
                "ui": "",
                "response": "To reschedule your appointment, could you please provide your registered phone number or Token number (e.g. TKN-0001)?",
            }
        if not appts:
            return {
                **state,
                "reschedule_step": "",
                "ui": "main",
                "response": f"I couldn't find any upcoming confirmed appointments for '{ident}'. If you would like to book a new appointment, please choose 'Book Appointment'.",
            }
        if len(appts) == 1:
            appt = appts[0]
            token = appt.get("token_no") or appt.get("appointment_id")
            # If the user's initial message also included a new date:
            date_cand = parse_date_from_text(text, self._clinic_today())
            if date_cand["success"] and date_cand["date"] != appt.get("date"):
                slots_res = self._slots.get_available_slots(appt.get("doctor"), date_cand["date"])
                open_slots = slots_res.get("slots", []) if isinstance(slots_res, dict) else slots_res
                if open_slots:
                    times_str = ", ".join(self._format_time(s.get("Start Time", "")) for s in open_slots)
                    return {
                        **state,
                        "reschedule_step": "select_slot",
                        "reschedule_appointment_id": token,
                        "doctor_name": appt.get("doctor"),
                        "appointment_date": appt.get("date"),
                        "appointment_time": appt.get("time"),
                        "patient_id": appt.get("patient_id"),
                        "target_reschedule_date": date_cand["date"],
                        "available_slots": open_slots,
                        "ui": "slots",
                        "response": (
                            f"Rescheduling appointment for Dr. {appt.get('doctor')} (Current: {appt.get('date')} at {appt.get('time')}).\n\n"
                            f"Available slots on {date_cand['display_date']}:\n{times_str}\n\n"
                            f"Please choose your preferred time slot:"
                        ),
                    }

            return {
                **state,
                "reschedule_step": "select_date",
                "reschedule_appointment_id": token,
                "doctor_name": appt.get("doctor"),
                "appointment_date": appt.get("date"),
                "appointment_time": appt.get("time"),
                "patient_id": appt.get("patient_id"),
                "token_no": token,
                "ui": "",
                "response": (
                    f"Found your appointment:\n\n"
                    f"👨‍⚕️ Doctor: {appt.get('doctor')}\n"
                    f"📅 Scheduled: {appt.get('date')} at {appt.get('time')}\n"
                    f"🎫 Token: {token}\n\n"
                    f"What new date would you prefer? You can say 'tomorrow', 'next Monday', or reply with a date (YYYY-MM-DD)."
                ),
            }

        return {
            **state,
            "reschedule_step": "select_appointment",
            "upcoming_appointments": appts,
            "ui": "select_appointment",
            "response": "You have multiple upcoming appointments. Please select the one you wish to reschedule:",
        }

    def appointment_draft_cancel(self, state: GraphState) -> GraphState:
        """Cancel active in-progress appointment booking draft and clear workflow state."""
        logger.info("[APPOINTMENT DRAFT CANCEL] Clearing in-progress appointment draft.")
        is_hindi = _is_hindi_or_hinglish(state.get("user_text", ""))
        if is_hindi:
            msg = "Theek hai, maine aapki appointment booking request cancel kar di hai. Agar aapko clinic, doctors ya timings ke baare mein kuch poochna ho, to batayein! 😊"
        else:
            msg = "No problem! I have cancelled your appointment booking request. Feel free to ask about our clinic, doctors, or timings whenever you are ready! 😊"

        return {
            **state,
            "active_flow": None,
            "appointment_step": "",
            "pending_field": None,
            "appointment_draft": {},
            "resume_context": None,
            "doctor_id": "",
            "doctor_name": "",
            "appointment_date": "",
            "appointment_time": "",
            "slot_id": "",
            "response": msg,
            "ui": "",
        }

    def cancel_node(self, state: GraphState) -> GraphState:
        flags = state.get("feature_flags", {})
        clinic_name = state.get("clinic_name", self._clinic_name)
        support_phone = state.get("support_phone", self._support_phone)
        from ..core.feature_flags import is_feature_enabled, get_disabled_feature_message
        if not is_feature_enabled(flags, "cancellation"):
            return {
                **state,
                "cancel_step": "",
                "ui": "main",
                "response": get_disabled_feature_message("cancellation", clinic_name, support_phone),
            }

        step = state.get("cancel_step")
        text = state.get("user_text", "").strip()


        # STEP: Ask identifier
        if step == "ask_identifier":
            ident = self._extract_identifier_from_text(text)
            if not ident:
                clean_digits = "".join(filter(str.isdigit, text))
                if len(clean_digits) == 10:
                    ident = clean_digits
                elif text.upper().startswith("TKN"):
                    ident = text.upper()
                else:
                    return {
                        **state,
                        "response": "Please provide your registered 10-digit phone number or Appointment Token (e.g. TKN-0001).",
                    }
            appts = self._crm.get_patient_upcoming_appointments(ident, today_str=self._clinic_today().isoformat())
            if not appts:
                return {
                    **state,
                    "cancel_step": "",
                    "ui": "main",
                    "response": f"I couldn't find any active upcoming appointments for '{ident}'.",
                }
            if len(appts) == 1:
                appt = appts[0]
                token = appt.get("token_no") or appt.get("appointment_id")
                return {
                    **state,
                    "cancel_step": "confirm",
                    "cancel_appointment_id": token,
                    "doctor_name": appt.get("doctor"),
                    "appointment_date": appt.get("date"),
                    "appointment_time": appt.get("time"),
                    "patient_id": appt.get("patient_id"),
                    "token_no": token,
                    "ui": "cancel_confirm",
                    "response": (
                        f"⚠️ **Confirm Appointment Cancellation**\n\n"
                        f"Are you sure you want to cancel this booking?\n"
                        f"• Doctor: {appt.get('doctor')}\n"
                        f"• Date & Time: {appt.get('date')} at {appt.get('time')}\n"
                        f"• Token: {token}\n\n"
                        f"Your reserved slot will be released back to the clinic pool."
                    ),
                }
            return {
                **state,
                "cancel_step": "select_appointment",
                "upcoming_appointments": appts,
                "ui": "select_appointment",
                "response": "You have multiple upcoming appointments. Please select the one you wish to cancel:",
            }

        # STEP: Select appointment from multiple
        if step == "select_appointment":
            token = self._extract_identifier_from_text(text) or text
            appts = state.get("upcoming_appointments", [])
            chosen = next((a for a in appts if (a.get("token_no") == token or a.get("appointment_id") == token)), None)
            if not chosen:
                chosen = self._crm.get_appointment(token)
            if not chosen:
                return {**state, "response": "Please select one of the appointments listed above."}
            chosen_token = chosen.get("token_no") or chosen.get("appointment_id")
            return {
                **state,
                "cancel_step": "confirm",
                "cancel_appointment_id": chosen_token,
                "doctor_name": chosen.get("doctor"),
                "appointment_date": chosen.get("date"),
                "appointment_time": chosen.get("time"),
                "patient_id": chosen.get("patient_id"),
                "token_no": chosen_token,
                "ui": "cancel_confirm",
                "response": (
                    f"⚠️ **Confirm Appointment Cancellation**\n\n"
                    f"Are you sure you want to cancel this booking?\n"
                    f"• Doctor: {chosen.get('doctor')}\n"
                    f"• Date & Time: {chosen.get('date')} at {chosen.get('time')}\n"
                    f"• Token: {chosen_token}\n\n"
                    f"Your reserved slot will be released back to the clinic pool."
                ),
            }

        # STEP: Confirm
        if step == "confirm":
            if text.casefold() in {"keep_appointment", "no", "keep", "nahi", "rehne do"}:
                old_date = state.get("appointment_date", "")
                old_time = state.get("appointment_time", "")
                doc = state.get("doctor_name", "")
                return {
                    **state,
                    "cancel_step": "",
                    "ui": "main",
                    "response": f"Great! Your appointment with Dr. {doc} on {old_date} at {old_time} remains confirmed.",
                }
            if text.casefold() not in {"confirm_cancel", "confirm", "yes", "haan", "cancel", "radd karo"}:
                return {**state, "response": "Please confirm by tapping 'Yes, Cancel Appointment' or 'Keep My Appointment'."}

            curr_appt_id = state.get("cancel_appointment_id") or state.get("token_no")
            doc = state.get("doctor_name", "")
            d = state.get("appointment_date", "")
            t = state.get("appointment_time", "")

            try:
                channel_name = str(state.get("channel", "WhatsApp")).title()
                res = self._crm.cancel_appointment(
                    identifier=curr_appt_id,
                    reason=f"Patient requested cancellation via {channel_name}",
                )
                return {
                    **state,
                    "cancel_step": "",
                    "booking_status": "Cancelled",
                    "ui": "main",
                    "response": (
                        f"Your appointment ({curr_appt_id}) with Dr. {doc} on {d} at {t} has been successfully cancelled.\n\n"
                        f"The reserved slot has been released back to our schedule. If you need a consultation in the future, we'll be glad to help you!"
                    ),
                }
            except Exception as err:
                logger.exception("Chatbot appointment cancellation failed")
                return {
                    **state,
                    "cancel_step": "",
                    "ui": "main",
                    "response": f"I couldn't cancel the appointment: {err}. Please contact clinic support at {self._support_phone}.",
                }

        # INITIAL ENTRY: No step set yet
        appts, ident = self._find_patient_appointments(state, text)
        if not ident:
            return {
                **state,
                "cancel_step": "ask_identifier",
                "ui": "",
                "response": "To cancel your appointment, please provide your registered phone number or Token number (e.g., TKN-0001):",
            }
        if not appts:
            return {
                **state,
                "cancel_step": "",
                "ui": "main",
                "response": f"I couldn't find any active upcoming appointments for '{ident}'.",
            }
        if len(appts) == 1:
            appt = appts[0]
            token = appt.get("token_no") or appt.get("appointment_id")
            return {
                **state,
                "cancel_step": "confirm",
                "cancel_appointment_id": token,
                "doctor_name": appt.get("doctor"),
                "appointment_date": appt.get("date"),
                "appointment_time": appt.get("time"),
                "patient_id": appt.get("patient_id"),
                "token_no": token,
                "ui": "cancel_confirm",
                "response": (
                    f"⚠️ **Confirm Appointment Cancellation**\n\n"
                    f"Are you sure you want to cancel this booking?\n"
                    f"• Doctor: {appt.get('doctor')}\n"
                    f"• Date & Time: {appt.get('date')} at {appt.get('time')}\n"
                    f"• Token: {token}\n\n"
                    f"Your reserved slot will be released back to the clinic pool."
                ),
            }
        return {
            **state,
            "cancel_step": "select_appointment",
            "upcoming_appointments": appts,
            "ui": "select_appointment",
            "response": "You have multiple upcoming appointments. Please select the one you wish to cancel:",
        }

    def my_appointments_node(self, state: GraphState) -> GraphState:
        text = state.get("user_text", "").strip()
        last_booked = state.get("last_booked_appointment")

        # 1. If we have a recently booked appointment in state/memory
        # and user is asking timing or confirmation of their booking
        is_timing_query = any(w in text.casefold() for w in ("kitne bje", "kitne baje", "kab aana", "kis time", "time kya", "timing", "samay", "when should i come", "what time", "arrival", "pahunchna"))
        is_recent_booking_query = any(w in text.casefold() for w in ("book kia", "book kiya", "book kr chuka", "already booked", "booking ho chuki", "appointment book", "appointment liya", "booking already"))

        if last_booked and (is_timing_query or is_recent_booking_query or not text):
            doc = last_booked.get("doctor_name") or last_booked.get("doctor") or "Doctor"
            date_str = last_booked.get("appointment_date") or last_booked.get("date") or ""
            time_str = last_booked.get("appointment_time") or last_booked.get("time") or ""
            tok = last_booked.get("token_no") or last_booked.get("appointment_id") or ""
            pname = last_booked.get("patient_name") or last_booked.get("name") or "Patient"

            if is_timing_query:
                response = (
                    f"Ji! Aapka appointment Dr. {doc} ke saath scheduled hai:\n\n"
                    f"📅 *Date:* {date_str}\n"
                    f"⏰ *Time:* {time_str}\n"
                    f"🎫 *Token Number:* {tok}\n"
                    f"👤 *Patient Name:* {pname}\n\n"
                    f"ℹ️ *Reporting Time:* Kripya appointment time ({time_str}) se 10-15 minute pehle reception par report karein."
                )
            else:
                response = (
                    f"Ji haan, aapka appointment Dr. {doc} ke saath pehle se confirmed hai!\n\n"
                    f"📅 *Date:* {date_str}\n"
                    f"⏰ *Time:* {time_str}\n"
                    f"🎫 *Token Number:* {tok}\n"
                    f"👤 *Patient Name:* {pname}\n\n"
                    f"Aapko dubara booking karne ki zaroorat nahi hai. Kripya samay se 10-15 minute pehle clinic reception pahuchein."
                )
            return {
                **state,
                "appointment_step": "complete",
                "reschedule_step": "",
                "ui": "main",
                "response": response,
            }

        # 2. Check CRM for upcoming appointments by phone, token, or patient name
        appts, ident = self._find_patient_appointments(state, text)
        if not ident:
            return {
                **state,
                "appointment_step": "",
                "reschedule_step": "ask_identifier",
                "ui": "",
                "response": (
                    "Aapka appointment verify karne ke liye, kripya apna *Token Number* (jaise TKN-0001) "
                    "ya *Registered Patient Name* batayein, mai turant details check kar deta hu."
                ),
            }
        if not appts:
            return {
                **state,
                "appointment_step": "",
                "reschedule_step": "",
                "ui": "main",
                "response": f"Humein '{ident}' ke under koi upcoming appointment nahi mila. Agar aapko naya appointment book karna hai to 'Book Appointment' kahein.",
            }

        if len(appts) == 1:
            a = appts[0]
            tok = a.get("token_no") or a.get("appointment_id", "")
            doc = a.get("doctor", "Doctor")
            dt = a.get("date", "")
            tm = a.get("time", "")
            pname = a.get("patient_name", "")
            status = a.get("status", "Confirmed")
            response = (
                f"📋 *Your Upcoming Appointments:*\n\n"
                f"Ji haan! Aapka appointment Dr. {doc} ke saath scheduled hai:\n\n"
                f"📅 *Date:* {dt}\n"
                f"⏰ *Time:* {tm}\n"
                f"🎫 *Token Number:* {tok}\n"
                + (f"👤 *Patient Name:* {pname}\n" if pname else "")
                + f"🔖 *Status:* {status}\n\n"
                f"ℹ️ Kripya appointment time ({tm}) se 10-15 minute pehle clinic reception par report karein."
            )
            return {
                **state,
                "appointment_step": "complete",
                "reschedule_step": "",
                "upcoming_appointments": appts,
                "ui": "main",
                "response": response,
            }

        lines = ["📋 *Your Upcoming Appointments:*\n"]
        for idx, a in enumerate(appts, 1):
            tok = a.get("token_no") or a.get("appointment_id", "")
            lines.append(
                f"{idx}. *Dr. {a.get('doctor', 'Doctor')}*\n"
                f"   📅 Date: {a.get('date')} | ⏰ Time: {a.get('time')}\n"
                f"   🎫 Token: {tok} | Status: {a.get('status', 'Confirmed')}\n"
            )
        lines.append("\nTo reschedule or change a slot, say 'Reschedule'.\nTo cancel an appointment, say 'Cancel'.")

        return {
            **state,
            "appointment_step": "complete",
            "reschedule_step": "",
            "upcoming_appointments": appts,
            "ui": "select_appointment" if len(appts) > 1 else "main",
            "response": "\n".join(lines),
        }

