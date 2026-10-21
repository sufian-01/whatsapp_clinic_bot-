"""State passed between graph nodes with interruption handling and conversational memory."""

from typing import Any, Dict, List, Optional, TypedDict


class ResumeContext(TypedDict, total=False):
    flow: str                   # e.g., "appointment_booking", "appointment_reschedule", "appointment_cancel"
    pending_field: str          # e.g., "doctor", "appointment_date", "appointment_time", "patient_phone", "patient_name", "patient_email"
    interrupted_at_step: str    # step name
    last_prompt: str            # last question asked by bot
    interruption_count: int     # count of side questions handled


class AppointmentDraft(TypedDict, total=False):
    doctor_id: Optional[str]
    doctor_name: Optional[str]
    specialization: Optional[str]
    appointment_date: Optional[str]
    appointment_time: Optional[str]
    slot_id: Optional[str]
    patient_name: Optional[str]
    patient_phone: Optional[str]
    patient_email: Optional[str]
    consultation_fee: Optional[str]


class GraphState(TypedDict, total=False):
    # Multi-tenant & Thread Identity
    tenant_id: str
    clinic_id: str
    chat_id: int | str
    phone: str
    patient_phone: str
    user_text: str
    channel: str
    last_processed_message_id: str

    # Intent & Routing
    intent: str
    active_flow: Optional[str]          # "appointment_booking" | "appointment_reschedule" | "appointment_cancel" | None
    pending_field: Optional[str]        # "doctor" | "date" | "time" | "phone" | "name" | "email" | None
    interruption_type: Optional[str]    # "side_question" | "cancellation" | "unrelated" | None
    resume_context: Optional[ResumeContext]

    # Conversation Memory & Context
    messages: list[dict[str, str]]
    conversation_summary: str
    clinic_context: list[str]
    doctor_context: list[dict[str, str]]
    recent_context: dict

    # Structured Draft
    appointment_draft: AppointmentDraft

    # Legacy & Flow Execution Fields (Preserved 100% for compatibility with all existing nodes & tools)
    appointment_step: str
    doctor_choices: list[dict[str, str]]   # doctors shown as buttons during selection
    doctor_fuzzy_candidate: dict[str, str] # candidate when fuzzy match is ambiguous
    patient_id: str
    patient_name: str
    patient_email: str
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

    # UI and transport settings
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
