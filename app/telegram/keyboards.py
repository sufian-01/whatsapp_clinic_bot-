"""Telegram keyboard definitions."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Book Appointment", callback_data="book")],
        [InlineKeyboardButton("My Appointments / Reschedule", callback_data="my_appointments")],
        [InlineKeyboardButton("Get/Check Report", callback_data="report")],
        [InlineKeyboardButton("Clinic Information", callback_data="clinic_info")],
        [InlineKeyboardButton("Other Help", callback_data="other")],
        [InlineKeyboardButton("Voice Settings", callback_data="voice_settings")],
    ])


def voice_settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Language", callback_data="voice_language")],
        [InlineKeyboardButton("Voice replies ON", callback_data="voice:on")],
        [InlineKeyboardButton("Voice replies OFF", callback_data="voice:off")],
    ])


def language_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Hindi", callback_data="language:hi")],
        [InlineKeyboardButton("English", callback_data="language:en")],
    ])


def slot_menu(slots: list[dict[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{slot.get('Start Time', '')} - {slot.get('End Time', '')}", callback_data=f"slot:{slot.get('Slot ID', '')}")]
        for slot in slots
    ])


def doctor_menu(doctors: list[dict[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(doctor.get("Doctor Name", "Doctor"), callback_data=f"doctor:{doctor.get('Doctor ID', '')}")]
        for doctor in doctors
    ])


def confirmation_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Confirm", callback_data="confirm"), InlineKeyboardButton("Change", callback_data="change")]])


def payment_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Online Payment", callback_data="payment_online")], [InlineKeyboardButton("Offline Payment", callback_data="payment_offline")]])


def appointment_menu(appointments: list[dict]) -> InlineKeyboardMarkup:
    """Buttons for selecting an appointment from a list."""
    buttons = []
    for appt in appointments:
        token = appt.get("token_no") or appt.get("appointment_id", "")
        doc = appt.get("doctor", "Doctor")
        d = appt.get("date", "")
        t = appt.get("time", "")
        label = f"{doc} | {d} {t} ({token})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"appt:{token}")])
    return InlineKeyboardMarkup(buttons)


def reschedule_confirmation_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Reschedule", callback_data="confirm_reschedule")],
        [InlineKeyboardButton("❌ Keep Current Booking", callback_data="cancel_reschedule")],
    ])


def cancel_confirmation_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Yes, Cancel Appointment", callback_data="confirm_cancel")],
        [InlineKeyboardButton("Keep My Appointment", callback_data="keep_appointment")],
    ])
