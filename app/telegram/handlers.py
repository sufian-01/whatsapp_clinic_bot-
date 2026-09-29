"""Translate Telegram updates into graph requests."""

import asyncio
import hashlib
import logging

from telegram import Update

from ..graph.graph import build_graph
from .keyboards import main_menu
from .keyboards import confirmation_menu, doctor_menu, payment_menu, slot_menu
from .sessions import SessionStore


logger = logging.getLogger(__name__)
sessions = SessionStore()

# Callback data prefixes handled specially
_SLOT_PREFIX = "slot:"
_DOCTOR_PREFIX = "doctor:"

# Simple callback_data → user_text mapping for button taps
_BUTTON_TEXT = {
    "book": "I want to book an appointment",
    "report": "I need my report",
    "clinic_info": "Tell me about the clinic",
    "other": "I need other help",
    "confirm": "confirm",
    "change": "change",
    "payment_online": "payment_online",
    "payment_offline": "payment_offline",
}


async def handle_update(update: Update, clinic_name: str, graph, bot) -> None:
    logger.info("Telegram update received")
    if update.callback_query:
        await update.callback_query.answer()
        chat = update.callback_query.message.chat_id
        text = update.callback_query.data
    elif update.message and update.message.text:
        chat = update.message.chat_id
        text = update.message.text
    else:
        return

    safe_chat = hashlib.sha256(str(chat).encode()).hexdigest()[:10]
    logger.info("Telegram message type=text chat=%s", safe_chat)

    if text == "/start":
        response = f"Hello! 👋\nI'm the AI assistant for {clinic_name}.\nHow can I help you today?"
        await bot.send_message(chat, response, main_menu())
        return

    state = sessions.get(chat)

    if text in _BUTTON_TEXT:
        # Known button callback — translate to natural-language text for the graph
        state["user_text"] = _BUTTON_TEXT[text]
    elif text.startswith(_SLOT_PREFIX):
        # Slot selection button: pass the slot ID (without prefix) as user_text
        state["user_text"] = text  # nodes strip "slot:" prefix themselves
    elif text.startswith(_DOCTOR_PREFIX):
        # Doctor selection button: pass the Doctor ID as user_text so the doctor step resolves it
        state["user_text"] = text[len(_DOCTOR_PREFIX):]
    else:
        state["user_text"] = text

    logger.info("LangGraph execution started")
    result = await asyncio.to_thread(graph.invoke, state)
    sessions.save(chat, result)
    await bot.send_message(chat, result["response"], _reply_markup(result))
    logger.info("Telegram response sent")


def _reply_markup(result):
    ui = result.get("ui", "")
    if ui == "slots":
        return slot_menu(result.get("available_slots", []))
    if ui == "doctor_select":
        choices = result.get("doctor_choices", [])
        if choices:
            return doctor_menu(choices)
        return None
    if ui == "confirm":
        return confirmation_menu()
    if ui == "payment":
        return payment_menu()
    # During an active appointment flow (any step except complete), show no global menu
    step = result.get("appointment_step", "")
    if step and step != "complete":
        return None
    return main_menu()