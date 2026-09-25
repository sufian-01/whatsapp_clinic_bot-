"""State passed between graph nodes."""

from typing import TypedDict


class GraphState(TypedDict, total=False):
    chat_id: int
    user_text: str
    intent: str
    clinic_context: list[str]
    doctor_context: list[dict[str, str]]
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
    ui: str
    response: str