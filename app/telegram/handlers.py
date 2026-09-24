"""Translate Telegram updates into graph requests."""

import asyncio
import hashlib
import logging

from telegram import Update

from ..graph.graph import build_graph
from .keyboards import main_menu


logger = logging.getLogger(__name__)


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
    if text in {"/start", "book", "report", "other"}:
        button_text = {
            "book": "Appointment booking will be available in the next phase.",
            "report": "Please describe your report or test question.",
            "other": "Please tell me how I can help.",
        }
        if text == "/start":
            response = f"Hello! 👋\nI'm the AI assistant for {clinic_name}.\nHow can I help you today?"
            await bot.send_message(chat, response, main_menu())
        else:
            await bot.send_message(chat, button_text[text])
        return
    logger.info("LangGraph execution started")
    result = await asyncio.to_thread(graph.invoke, {"chat_id": chat, "user_text": text})
    await bot.send_message(chat, result["response"], main_menu())
    logger.info("Telegram response sent")