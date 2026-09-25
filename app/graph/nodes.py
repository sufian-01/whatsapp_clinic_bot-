"""Pure graph nodes with injected collaborators."""

from ..core.prompts import load_system_prompt
from ..llm.gemini import GeminiClient
from ..rag.service import RagService
from ..tools.invoice import InvoiceData
from ..tools.invoices import InvoiceTools
from ..tools.patients import PatientRecord
from ..tools.rag_tool import search_clinic_knowledge
from .state import GraphState
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class GraphNodes:
    def __init__(self, clinic_name: str, llm: GeminiClient, rag: RagService, doctors=None, support_phone: str = "6200126662", patients=None, slots=None, email_sender=None, payments=None, invoices=None, gmail=None) -> None:
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

    def classify(self, state: GraphState) -> GraphState:
        from .router import classify_intent

        return classify_intent(state)

    def retrieve(self, state: GraphState) -> GraphState:
        logger.info("RAG tool invoked")
        context = search_clinic_knowledge(self._rag, state.get("user_text", ""))
        logger.info("Retrieved %d chunks", len(context))
        return {**state, "clinic_context": context}

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

    def appointment_start(self, state: GraphState) -> GraphState:
        return {**state, "appointment_step": "name", "response": "Sure. May I know your name?"}

    def appointment_progress(self, state: GraphState) -> GraphState:
        step = state.get("appointment_step", "name")
        text = state.get("user_text", "").strip()
        if step == "name":
            return {**state, "patient_name": text, "appointment_step": "email", "response": "What email address should receive the invoice?"}
        if step == "email":
            if "@" not in text or "." not in text:
                return {**state, "response": "Please provide a valid email address."}
            return {**state, "patient_email": text, "appointment_step": "phone", "response": "What phone number should we use?"}
        if step == "phone":
            return {**state, "patient_phone": text, "appointment_step": "doctor", "response": "Which doctor or specialization would you like?"}
        if step == "doctor":
            if self._doctors is None:
                return {**state, "response": "Doctor information is unavailable right now. Please contact the clinic team at " + self._support_phone + "."}
            matches = self._doctors.get_doctors()
            lowered = text.casefold()
            named = [doctor for doctor in matches if doctor.get("Doctor Name", "").casefold() in lowered]
            specialization = next((value for value in ("gynecologist", "physician", "specialist") if value in lowered), "")
            if named:
                matches = named
            elif specialization:
                matches = self._doctors.get_doctors_by_specialization(specialization)
            else:
                matches = []
            if len(matches) != 1:
                options = "\n".join(f"{doctor.get('Doctor Name', 'Unknown')} - {doctor.get('Specialization', 'Unknown')}" for doctor in matches)
                return {**state, "doctor_context": matches, "response": options or "I couldn't find that doctor. Please provide a doctor name or specialization."}
            doctor = matches[0]
            amount = doctor.get("Consultation Fee", "")
            if not amount:
                return {**state, "response": "The consultation fee is unavailable, so I cannot continue this booking."}
            return {**state, "doctor_context": matches, "doctor_id": doctor.get("Doctor ID", ""), "doctor_name": doctor.get("Doctor Name", ""), "specialization": doctor.get("Specialization", ""), "amount": amount, "appointment_step": "date", "response": "What date would you prefer? Please use YYYY-MM-DD."}
        if step == "date":
            if not self._slots or not state.get("doctor_name"):
                return {**state, "response": "Appointment slots are not configured yet. Please contact the clinic team at " + self._support_phone + "."}
            available_result = self._slots.get_available_slots(state["doctor_name"], text)
            if isinstance(available_result, dict) and not available_result.get("success"):
                return {**state, "response": "I couldn't check availability right now. Please try again or contact clinic support at " + self._support_phone + "."}
            available = available_result.get("slots", []) if isinstance(available_result, dict) else available_result
            if not available:
                return {**state, "response": "No available slots were found for that date. Please choose another date."}
            return {**state, "appointment_date": text, "available_slots": available, "appointment_step": "slot", "ui": "slots", "response": "Please select an available slot."}
        if step == "slot":
            slot_id = text.removeprefix("slot:")
            slot = next((item for item in state.get("available_slots", []) if item.get("Slot ID") == slot_id), None)
            if not slot:
                return {**state, "response": "That slot is no longer available. Please select another slot."}
            summary = self._summary(state, slot.get("Start Time", ""))
            return {**state, "slot_id": slot_id, "appointment_time": slot.get("Start Time", ""), "appointment_step": "confirmation", "ui": "confirm", "response": summary + "\n\nPlease confirm your appointment."}
        if step == "confirmation":
            if text.casefold() in {"change", "no", "cancel"}:
                return {**state, "appointment_step": "doctor", "ui": "", "response": "What doctor or specialization would you like instead?"}
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
            invoice_data = InvoiceData(self._clinic_name, self._support_phone, "", "", record.name, record.email, record.phone, state["doctor_name"], state.get("specialization", ""), state["appointment_date"], state["appointment_time"], token_no, state["amount"], "Pay at Clinic", "Pending")
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
            response = "I’m sorry, I’m unable to answer right now. Please try again shortly."
        logger.info("Gemini response generated")
        return {**state, "response": response}