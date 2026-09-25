"""Telegram keyboard definitions."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Book Appointment", callback_data="book")],
        [InlineKeyboardButton("Get/Check Report", callback_data="report")],
        [InlineKeyboardButton("Clinic Information", callback_data="clinic_info")],
        [InlineKeyboardButton("Other Help", callback_data="other")],
    ])


def slot_menu(slots: list[dict[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{slot.get('Start Time', '')} - {slot.get('End Time', '')}", callback_data=f"slot:{slot.get('Slot ID', '')}")]
        for slot in slots
    ])


def confirmation_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Confirm", callback_data="confirm"), InlineKeyboardButton("Change", callback_data="change")]])


def payment_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Online Payment", callback_data="payment_online")], [InlineKeyboardButton("Offline Payment", callback_data="payment_offline")]])