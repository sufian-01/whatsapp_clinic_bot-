"""Telegram keyboard definitions."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Book Appointment", callback_data="book")],
        [InlineKeyboardButton("Get/Check Report", callback_data="report")],
        [InlineKeyboardButton("Other Help", callback_data="other")],
    ])