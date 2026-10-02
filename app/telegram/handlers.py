"""Translate Telegram updates into graph requests and optional voice replies."""

import asyncio
import hashlib
import logging
import tempfile
from pathlib import Path

from telegram import Update

from ..services.sarvam_service import SarvamConfigurationError, SarvamError
from .keyboards import (
    appointment_menu,
    cancel_confirmation_menu,
    confirmation_menu,
    doctor_menu,
    language_menu,
    main_menu,
    payment_menu,
    reschedule_confirmation_menu,
    slot_menu,
    voice_settings_menu,
)
from .sessions import SessionStore


logger = logging.getLogger(__name__)
sessions = SessionStore()

_SLOT_PREFIX = "slot:"
_DOCTOR_PREFIX = "doctor:"
_APPT_PREFIX = "appt:"
_BUTTON_TEXT = {
    "book": "I want to book an appointment",
    "my_appointments": "Show my upcoming appointments",
    "report": "I need my report",
    "clinic_info": "Tell me about the clinic",
    "other": "I need other help",
    "confirm": "confirm",
    "change": "change",
    "payment_online": "payment_online",
    "payment_offline": "payment_offline",
    "confirm_reschedule": "confirm_reschedule",
    "cancel_reschedule": "cancel_reschedule",
    "confirm_cancel": "confirm_cancel",
    "keep_appointment": "keep_appointment",
}


async def handle_update(update: Update, clinic_name: str, graph, bot, sarvam=None) -> None:
    """Use the same LangGraph invocation for typed and transcribed input."""
    logger.info("Telegram update received")
    chat, text, voice = _extract_input(update)
    if chat is None:
        return
    if update.callback_query:
        await update.callback_query.answer()
    safe_chat = hashlib.sha256(str(chat).encode()).hexdigest()[:10]

    if update.callback_query and await _handle_preference_callback(chat, text, bot, sarvam):
        return

    if voice is not None:
        logger.info("Telegram message type=voice chat=%s", safe_chat)
        text = await _transcribe_voice(chat, voice, bot, sarvam)
        if text is None:
            return
    elif text is None:
        return
    else:
        logger.info("Telegram message type=text chat=%s", safe_chat)

    if text == "/start":
        response = f"Hello! 👋\nI'm the AI assistant for {clinic_name}.\nHow can I help you today?"
        await bot.send_message(chat, response, main_menu())
        return

    state = sessions.get(chat)
    state["chat_id"] = chat
    state["user_text"] = _graph_text(text)
    history = list(state.get("messages", []))
    history.append({"role": "user", "content": state["user_text"]})
    state["messages"] = history[-12:]
    logger.info("LangGraph execution started")
    result = await asyncio.to_thread(graph.invoke, state)
    if result.get("response"):
        resp_history = list(result.get("messages", state["messages"]))
        resp_history.append({"role": "assistant", "content": result["response"]})
        result["messages"] = resp_history[-12:]
    sessions.save(chat, result)
    await _send_response(chat, result, bot, sarvam)
    logger.info("Telegram response sent")


def _extract_input(update: Update):
    if update.callback_query:
        message = update.callback_query.message
        if message is None:
            return None, None, None
        return message.chat_id, update.callback_query.data, None
    if update.message:
        return update.message.chat_id, update.message.text, update.message.voice
    return None, None, None


async def _handle_preference_callback(chat: int, text: str | None, bot, sarvam) -> bool:
    """Update transport preferences without entering or changing appointment flow."""
    if text == "voice_settings":
        state = sessions.get(chat)
        language = "Hindi" if state.get("preferred_language") == "hi" else "English"
        status = "ON" if state.get("voice_replies") else "OFF"
        await bot.send_message(chat, f"Voice replies: {status}\nVoice language: {language}", voice_settings_menu())
        return True
    if text == "voice_language":
        await bot.send_message(chat, "Choose a voice language.", language_menu())
        return True
    if text in {"language:hi", "language:en"}:
        state = sessions.get(chat)
        state["preferred_language"] = text.rsplit(":", 1)[1]
        sessions.save(chat, state)
        await bot.send_message(chat, f"Voice language set to {'Hindi' if state['preferred_language'] == 'hi' else 'English'}.", voice_settings_menu())
        return True
    if text in {"voice:on", "voice:off"}:
        if text == "voice:on" and not _voice_available(sarvam):
            await bot.send_message(chat, _voice_configuration_message(), voice_settings_menu())
            return True
        state = sessions.get(chat)
        state["voice_replies"] = text == "voice:on"
        sessions.save(chat, state)
        await bot.send_message(chat, f"Voice replies are now {'ON' if state['voice_replies'] else 'OFF'}.", voice_settings_menu())
        return True
    return False


async def _transcribe_voice(chat: int, voice, bot, sarvam) -> str | None:
    if not _voice_available(sarvam):
        await bot.send_message(chat, _voice_configuration_message())
        return None
    duration = getattr(voice, "duration", 0) or 0
    duration = duration.total_seconds() if hasattr(duration, "total_seconds") else duration
    if duration > sarvam.max_voice_duration_seconds:
        await bot.send_message(chat, "Please send a voice message of 30 seconds or less.")
        return None
    file_size = getattr(voice, "file_size", None)
    if file_size is not None and file_size > sarvam.max_voice_bytes:
        await bot.send_message(chat, "That voice message is too large. Please send a shorter recording.")
        return None

    # TemporaryDirectory ensures source audio is removed after every outcome.
    try:
        with tempfile.TemporaryDirectory(prefix="clinic-voice-") as directory:
            audio_path = Path(directory) / "telegram-voice.ogg"
            await bot.download_voice_file(voice.file_id, audio_path)
            return await asyncio.to_thread(sarvam.transcribe, audio_path)
    except SarvamConfigurationError:
        await bot.send_message(chat, _voice_configuration_message())
    except SarvamError as exc:
        await bot.send_message(chat, str(exc))
    except Exception:
        # File IDs, paths, transcripts, and audio bytes are deliberately not logged.
        logger.warning("Telegram voice download or transcription failed")
        await bot.send_message(chat, "I couldn't process that voice message. Please try recording it again.")
    return None


async def _send_response(chat: int, result: dict, bot, sarvam) -> None:
    text = result.get("response", "I'm sorry, I couldn't prepare a response. Please try again.")
    markup = _reply_markup(result)
    if not result.get("voice_replies"):
        await bot.send_message(chat, text, markup)
        return
    if not _voice_available(sarvam):
        await bot.send_message(chat, f"{_voice_configuration_message()}\n\n{text}", markup)
        return
    try:
        language = result.get("preferred_language", "en")
        audio = await asyncio.to_thread(sarvam.synthesize, text, language)
        await bot.send_voice(chat, audio, markup)
    except SarvamError:
        logger.warning("Voice reply failed; sending text fallback")
        await bot.send_message(chat, text, markup)
    except Exception:
        logger.warning("Telegram voice reply delivery failed; sending text fallback")
        await bot.send_message(chat, text, markup)


def _voice_available(sarvam) -> bool:
    return bool(sarvam and getattr(sarvam, "available", False))


def _voice_configuration_message() -> str:
    return "Voice features are not configured yet. Please ask the clinic to configure Sarvam AI."


def _graph_text(text: str) -> str:
    if text in _BUTTON_TEXT:
        return _BUTTON_TEXT[text]
    if text.startswith(_SLOT_PREFIX):
        return text
    if text.startswith(_DOCTOR_PREFIX):
        return text[len(_DOCTOR_PREFIX):]
    if text.startswith(_APPT_PREFIX):
        return text
    return text


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
    if ui == "select_appointment":
        appts = result.get("upcoming_appointments", [])
        if appts:
            return appointment_menu(appts)
        return None
    if ui == "reschedule_confirm":
        return reschedule_confirmation_menu()
    if ui == "cancel_confirm":
        return cancel_confirmation_menu()
    step = result.get("appointment_step", "")
    if step and step != "complete":
        return None
    if result.get("reschedule_step") or result.get("cancel_step"):
        return None
    return main_menu()
