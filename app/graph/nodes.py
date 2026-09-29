from __future__ import annotations

import logging
from pathlib import Path

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

# Maximum doctors to show as Telegram inline buttons (beyond this limit we use text)
_MAX_BUTTON_DOCTORS = 8


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

    # ------------------------------------------------------------------
    # classify
    # ------------------------------------------------------------------

    def classify(self, state: GraphState) -> GraphState:
        from .router import classify_intent
        return classify_intent(state)

    # ------------------------------------------------------------------
    # retrieve  (RAG)
    # ------------------------------------------------------------------

    def retrieve(self, state: GraphState) -> GraphState:
        logger.info("RAG tool invoked")
        context = search_clinic_knowledge(self._rag, state.get("user_text", ""))
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
        for doctor in matches:
            name = doctor.get("Doctor Name", "")
            if name and name.casefold() in text.casefold():
                matches = self._doctors.get_doctor_by_name(name)
                break
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

        # 1. Try to extract a date from user text (deterministic)
        date_result = parse_date_from_text(text)
        target_date: str | None = date_result["date"] if date_result.get("success") else None

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
        return {
            **state,
            "doctor_choices": doctors[:_MAX_BUTTON_DOCTORS],
            "ui": "doctor_select",
            "response": response,
        }

    # ------------------------------------------------------------------
    # appointment_start
    # ------------------------------------------------------------------

    def appointment_start(self, state: GraphState) -> GraphState:
        return {**state, "appointment_step": "name", "response": "Sure. May I know your name?"}

    # ------------------------------------------------------------------
    # appointment_progress
    # ------------------------------------------------------------------

    def appointment_progress(self, state: GraphState) -> GraphState:  # noqa: C901
        step = state.get("appointment_step", "name")
        text = state.get("user_text", "").strip()

        if step == "name":
            return {**state, "patient_name": text, "appointment_step": "email", "response": "What email address should receive the invoice?"}

        if step == "email":
            if "@" not in text or "." not in text:
                return {**state, "response": "Please provide a valid email address."}
            return {**state, "patient_email": text, "appointment_step": "phone", "response": "What phone number should we use?"}

        if step == "phone":
            return {**state, "patient_phone": text, "appointment_step": "doctor", **self._show_doctor_selection(state)}

        if step == "doctor":
            return self._handle_doctor_step(state, text)

        if step == "doctor_confirm_fuzzy":
            return self._handle_fuzzy_confirmation(state, text)

        if step == "date":
            return self._handle_date_step(state, text)

        if step == "slot":
            slot_id = text.removeprefix("slot:")
            slot = next((item for item in state.get("available_slots", []) if item.get("Slot ID") == slot_id), None)
            if not slot:
                return {**state, "response": "That slot is no longer available. Please select another slot."}
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
            if text.casefold() in {"online", "payment_online"}:
                payment = self._payments.create_online_payment(state.get("amount", "")) if self._payments else {"success": False, "status": "NOT_IMPLEMENTED", "message": "Online payment will be available soon."}
                if self._slots:
                    self._release_slot(state.get("slot_id", ""), state.get("patient_id"))
                return {**state, "appointment_step": "payment", "ui": "payment", "response": payment.get("message", "Online payment will be available soon. Please choose Offline Payment for now.")}
            if text.casefold() not in {"offline", "payment_offline"}:
                return {**state, "response": "Please choose Online Payment or Offline Payment."}
            return self._complete_offline(state)

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

        # --- 5. No reliable match — show available doctors list ---
        if all_active:
            intro = "I couldn't find a doctor matching that request. Our available doctors are:"
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
        """Commit doctor selection and advance to the date step."""
        amount = doctor.get("Consultation Fee", "")
        if not amount:
            return {**state, "response": "The consultation fee is unavailable, so I cannot continue this booking."}
        return {
            **state,
            "doctor_context": [doctor],
            "doctor_id": doctor.get("Doctor ID", ""),
            "doctor_name": doctor.get("Doctor Name", ""),
            "specialization": doctor.get("Specialization", ""),
            "amount": amount,
            "appointment_step": "date",
            "doctor_choices": [],
            "doctor_fuzzy_candidate": {},
            "ui": "",
            "response": "What date would you prefer? Please use YYYY-MM-DD.",
        }

    def _handle_date_step(self, state: GraphState, text: str) -> GraphState:
        if not self._slots or not state.get("doctor_name"):
            return {**state, "response": "Appointment slots are not configured yet. Please contact the clinic team at " + self._support_phone + "."}
        date_result = parse_date(text)
        if not date_result["success"]:
            return {**state, "response": date_result["message"]}
        normalized_date = date_result["date"]
        available_result = self._slots.get_available_slots(state["doctor_name"], normalized_date)
        if isinstance(available_result, dict) and not available_result.get("success"):
            return {**state, "response": "I couldn't check availability right now. Please try again or contact clinic support at " + self._support_phone + "."}
        available = available_result.get("slots", []) if isinstance(available_result, dict) else available_result
        if not available:
            return {**state, "response": "No available slots were found for that date. Please choose another date."}
        return {**state, "appointment_date": normalized_date, "available_slots": available, "appointment_step": "slot", "ui": "slots", "response": "Please select an available slot."}

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
        try:
            qr_result = self._payments.generate_offline_upi_qr(state["amount"], self._clinic_name, token_no, Path("data/invoices")) if self._payments else {"success": False, "error_code": "QR_TOOL_UNAVAILABLE"}
            if not qr_result.get("success"):
                raise RuntimeError("Offline payment QR generation failed")
            invoice_data = InvoiceData(self._clinic_name, self._support_phone, "", "", record.name, record.email, record.phone, state["doctor_name"], state.get("specialization", ""), state["appointment_date"], state["appointment_time"], token_no, state["amount"], "Pay at Clinic / UPI", "Pending", qr_result["qr_path"])
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
                email_result = self._gmail.send_invoice_email(record.email, invoice_number, f"Appointment Confirmation & Invoice - {self._clinic_name}", "Your appointment is confirmed. Payment is pending and payable at the clinic.", str(invoice_path))
                email_sent = email_result.get("success", False)
            except Exception:
                logger.exception("Invoice email delivery failed after appointment confirmation")
        response = f"Appointment confirmed.\n\nToken: {token_no}\nDoctor: {state['doctor_name']}\nDate: {state['appointment_date']}\nTime: {state['appointment_time']}\nAmount: {state['amount']}\nPayment: Pay at Clinic\nInvoice: {'sent to your email' if email_sent else 'generated; email delivery failed'}"
        return {**state, "token_no": token_no, "payment_method": "Offline", "payment_status": "Pending", "booking_status": "Confirmed", "invoice_number": invoice_number, "invoice_path": str(invoice_path), "email_sent": email_sent, "appointment_step": "complete", "ui": "main", "response": response}

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

    def report_response(self, state: GraphState) -> GraphState:
        return {**state, "response": "Report lookup is not connected yet. Please contact the clinic team at " + self._support_phone + "."}

    def human_support(self, state: GraphState) -> GraphState:
        return {**state, "response": "Please contact the clinic team at " + self._support_phone + "."}

    def answer(self, state: GraphState) -> GraphState:
        if state.get("intent") == "doctor_information" and not state.get("doctor_context"):
            return {**state, "response": "I couldn't verify doctor information right now. Please contact the clinic team at " + self._support_phone + "."}
        context = state.get("clinic_context", [])
        context += ["Structured doctor record: " + ", ".join(f"{key}={value}" for key, value in doctor.items()) for doctor in state.get("doctor_context", [])]
        try:
            response = self._llm.answer(load_system_prompt(self._clinic_name, self._support_phone), state.get("user_text", ""), context)
        except Exception:
            logger.exception("Gemini completion failed")
            response = "I'm sorry, I'm unable to answer right now. Please try again shortly."
        logger.info("Gemini response generated")
        return {**state, "response": response}