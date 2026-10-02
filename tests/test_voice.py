import asyncio
import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from telegram import Bot, Update

from app.services.sarvam_service import SarvamError, SarvamService
from app.telegram import handlers
from app.telegram.sessions import SessionStore


class FakeBot:
    def __init__(self, download_error=False):
        self.messages = []
        self.voices = []
        self.download_error = download_error

    async def send_message(self, chat_id, text, reply_markup=None):
        self.messages.append((chat_id, text, reply_markup))

    async def send_voice(self, chat_id, audio, reply_markup=None):
        self.voices.append((chat_id, audio, reply_markup))

    async def download_voice_file(self, file_id, destination):
        if self.download_error:
            raise RuntimeError("download unavailable")
        Path(destination).write_bytes(b"OggSvoice")


class FakeSarvam:
    available = True
    max_voice_bytes = 1024 * 1024
    max_voice_duration_seconds = 30

    def __init__(self, transcript="book an appointment", tts_error=False):
        self.transcript = transcript
        self.tts_error = tts_error
        self.transcribed_paths = []
        self.tts_calls = []

    def transcribe(self, path):
        self.transcribed_paths.append(Path(path))
        return self.transcript

    def synthesize(self, text, language):
        self.tts_calls.append((text, language))
        if self.tts_error:
            raise SarvamError("TTS unavailable")
        return b"opus-audio"


class CaptureGraph:
    def __init__(self):
        self.states = []

    def invoke(self, state):
        self.states.append(dict(state))
        return {**state, "response": f"reply:{state['user_text']}", "ui": "main"}


def voice_update(chat_id=77, duration=2, file_size=100):
    return Update.de_json(
        {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 1,
                "chat": {"id": chat_id, "type": "private"},
                "voice": {"file_id": "voice-file", "file_unique_id": "unique", "duration": duration, "file_size": file_size},
            },
        },
        Bot("123456:TEST"),
    )


def text_update(text="Hello", chat_id=77):
    return Update.de_json(
        {"update_id": 2, "message": {"message_id": 2, "date": 1, "chat": {"id": chat_id, "type": "private"}, "text": text}},
        Bot("123456:TEST"),
    )


class VoiceHandlerTests(unittest.TestCase):
    def setUp(self):
        handlers.sessions = SessionStore()

    def test_telegram_voice_is_detected_transcribed_and_sent_to_graph(self):
        bot, sarvam, graph = FakeBot(), FakeSarvam("need a doctor"), CaptureGraph()
        asyncio.run(handlers.handle_update(voice_update(), "Clinic", graph, bot, sarvam))
        self.assertEqual(graph.states[0]["user_text"], "need a doctor")
        self.assertIn("reply:need a doctor", bot.messages[0][1])
        self.assertFalse(sarvam.transcribed_paths[0].exists(), "temporary patient audio must be removed")

    def test_audio_download_failure_returns_retry_message(self):
        bot, graph = FakeBot(download_error=True), CaptureGraph()
        asyncio.run(handlers.handle_update(voice_update(), "Clinic", graph, bot, FakeSarvam()))
        self.assertFalse(graph.states)
        self.assertIn("couldn't process", bot.messages[0][1])

    def test_missing_key_returns_configuration_message_and_text_still_works(self):
        bot, graph = FakeBot(), CaptureGraph()
        asyncio.run(handlers.handle_update(voice_update(), "Clinic", graph, bot, SarvamService()))
        self.assertIn("not configured", bot.messages[0][1])
        asyncio.run(handlers.handle_update(text_update("Hello"), "Clinic", graph, bot, SarvamService()))
        self.assertEqual(graph.states[-1]["user_text"], "Hello")

    def test_voice_duration_limit_blocks_oversized_recording(self):
        bot, graph = FakeBot(), CaptureGraph()
        asyncio.run(handlers.handle_update(voice_update(duration=31), "Clinic", graph, bot, FakeSarvam()))
        self.assertFalse(graph.states)
        self.assertIn("30 seconds", bot.messages[0][1])

    def test_voice_preference_on_uses_tts_and_off_uses_text(self):
        bot, sarvam = FakeBot(), FakeSarvam()
        asyncio.run(handlers._send_response(1, {"response": "hello", "voice_replies": True, "preferred_language": "hi"}, bot, sarvam))
        self.assertEqual(sarvam.tts_calls, [("hello", "hi")])
        self.assertEqual(len(bot.voices), 1)
        self.assertFalse(bot.messages)
        asyncio.run(handlers._send_response(1, {"response": "hello", "voice_replies": False}, bot, sarvam))
        self.assertEqual(len(bot.messages), 1)

    def test_tts_failure_falls_back_to_original_text(self):
        bot = FakeBot()
        asyncio.run(handlers._send_response(1, {"response": "medical response", "voice_replies": True}, bot, FakeSarvam(tts_error=True)))
        self.assertEqual(bot.messages[0][1], "medical response")
        self.assertFalse(bot.voices)

    def test_hindi_and_english_preferences_are_saved_without_touching_booking_state(self):
        bot = FakeBot()
        available = FakeSarvam()
        state = {"appointment_step": "doctor", "patient_name": "Asha"}
        handlers.sessions.save(1, state)
        asyncio.run(handlers._handle_preference_callback(1, "language:hi", bot, available))
        asyncio.run(handlers._handle_preference_callback(1, "voice:on", bot, available))
        saved = handlers.sessions.get(1)
        self.assertEqual(saved["preferred_language"], "hi")
        self.assertTrue(saved["voice_replies"])
        self.assertEqual(saved["appointment_step"], "doctor")
        asyncio.run(handlers._handle_preference_callback(1, "language:en", bot, available))
        self.assertEqual(handlers.sessions.get(1)["preferred_language"], "en")


class SarvamServiceTests(unittest.TestCase):
    def test_stt_success_uses_multipart_request(self):
        response = Mock(is_success=True)
        response.json.return_value = {"transcript": "नमस्ते doctor"}
        with tempfile.TemporaryDirectory() as directory, patch("app.services.sarvam_service.httpx.post", return_value=response) as post:
            audio = Path(directory) / "voice.ogg"
            audio.write_bytes(b"OggSvoice")
            transcript = SarvamService(api_key="test-key").transcribe(audio)
        self.assertEqual(transcript, "नमस्ते doctor")
        self.assertEqual(post.call_args.kwargs["data"]["mode"], "codemix")

    def test_stt_api_failure_and_empty_transcript_are_safe_errors(self):
        failed = Mock(is_success=False, status_code=429)
        with tempfile.TemporaryDirectory() as directory, patch("app.services.sarvam_service.httpx.post", return_value=failed):
            audio = Path(directory) / "voice.ogg"
            audio.write_bytes(b"OggSvoice")
            with self.assertRaises(SarvamError):
                SarvamService(api_key="test-key").transcribe(audio)
        empty = Mock(is_success=True)
        empty.json.return_value = {"transcript": " "}
        with tempfile.TemporaryDirectory() as directory, patch("app.services.sarvam_service.httpx.post", return_value=empty):
            audio = Path(directory) / "voice.ogg"
            audio.write_bytes(b"OggSvoice")
            with self.assertRaises(SarvamError):
                SarvamService(api_key="test-key").transcribe(audio)

    def test_tts_success_and_missing_key(self):
        response = Mock(is_success=True)
        response.json.return_value = {"audios": [base64.b64encode(b"opus").decode()]}
        with patch("app.services.sarvam_service.httpx.post", return_value=response) as post:
            self.assertEqual(SarvamService(api_key="test-key").synthesize("hello", "en"), b"opus")
        self.assertEqual(post.call_args.kwargs["json"]["language_code"], "en-IN")
        with self.assertRaises(SarvamError):
            SarvamService().synthesize("hello", "en")


if __name__ == "__main__":
    unittest.main()
