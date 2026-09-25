"""Translate Telegram updates into graph requests."""

import asyncio
import hashlib
import logging

from telegram import Update

from ..graph.graph import build_graph
from .keyboards import main_menu
from .keyboards import confirmation_menu, payment_menu, slot_menu
from .sessions import SessionStore


logger = logging.getLogger(__name__)
sessions = SessionStore()


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
    if text in {"/start", "book", "report", "clinic_info", "other", "confirm", "change", "payment_online", "payment_offline"} or text.startswith("slot:"):
        if text == "/start":
            response = f"Hello! 👋\nI'm the AI assistant for {clinic_name}.\nHow can I help you today?"
            await bot.send_message(chat, response, main_menu())
        else:
            button_text = {
                "book": "I want to book an appointment",
                "report": "I need my report",
                "clinic_info": "Tell me about the clinic",
                "other": "I need other help",
                "confirm": "confirm",
                "change": "change",
                "payment_online": "payment_online",
                "payment_offline": "payment_offline",
            }
            logger.info("LangGraph execution started")
            state = sessions.get(chat)
            state["user_text"] = text.removeprefix("slot:") if text.startswith("slot:") else button_text[text]
            result = await asyncio.to_thread(graph.invoke, state)
            sessions.save(chat, result)
            await bot.send_message(chat, result["response"], _reply_markup(result))
            logger.info("Telegram response sent")
        return
    logger.info("LangGraph execution started")
    state = sessions.get(chat)
    state["user_text"] = text
    result = await asyncio.to_thread(graph.invoke, state)
    sessions.save(chat, result)
    await bot.send_message(chat, result["response"], _reply_markup(result))
    logger.info("Telegram response sent")


def _reply_markup(result):
    if result.get("ui") == "slots":
        return slot_menu(result.get("available_slots", []))
    if result.get("ui") == "confirm":
        return confirmation_menu()
    if result.get("ui") == "payment":
        return payment_menu()
    return main_menu()