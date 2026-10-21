"""State passed between graph nodes."""

from typing import TypedDict


class GraphState(TypedDict, total=False):
    chat_id: int | str
    user_text: str
    intent: str
    messages: list[dict[str, str]]
    clinic_context: list[str]
    doctor_context: list[dict[str, str]]
    # Doctor-selection UX
    doctor_choices: list[dict[str, str]]   # doctors shown as buttons during selection
    doctor_fuzzy_candidate: dict[str, str] # candidate when fuzzy match is ambiguous
    appointment_step: str
    patient_id: str
    patient_name: str
    patient_email: str
    patient_phone: str
    patient_age: str
    patient_gender: str
    doctor_id: str
    doctor_name: str
    specialization: str
    appointment_date: str
    appointment_time: str
    slot_id: str
    available_slots: list[dict[str, str]]
    token_no: str
    amount: str
    payment_method: str
    payment_status: str
    booking_status: str
    invoice_number: str
    invoice_path: str
    email_sent: bool
    # Transport preferences intentionally live beside the existing in-process
    # conversation state and never affect appointment fields.
    preferred_language: str
    voice_replies: bool
    ui: str
    welcome_menu_sent: bool
    response: str
    # Reschedule and Cancel states
    reschedule_step: str
    reschedule_appointment_id: str
    reschedule_target_slot: dict[str, str]
    target_reschedule_date: str
    cancel_step: str
    cancel_appointment_id: str
    cancellation_reason: str
    upcoming_appointments: list[dict]
    # Memory and checkpointer context
    last_booked_appointment: dict
    recent_context: dict
    phone: str
