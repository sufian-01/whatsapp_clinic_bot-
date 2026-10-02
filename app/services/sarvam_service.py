"""Small, synchronous Sarvam REST adapter.

The Telegram handler runs this adapter in a worker thread, keeping network and
audio concerns outside both Telegram transport and LangGraph business logic.
"""

from __future__ import annotations

import base64
import binascii
import logging
import mimetypes
from pathlib import Path

import httpx

from ..core.config import Settings


logger = logging.getLogger(__name__)


class SarvamError(RuntimeError):
    """A patient-safe voice-service failure."""


class SarvamConfigurationError(SarvamError):
    """Raised only when optional voice features have not been configured."""


class SarvamService:
    """Sarvam STT/TTS client with bounded input and no sensitive logging."""

    MAX_TTS_CHARACTERS = 2500

    def __init__(
        self,
        api_key: str = "",
        stt_model: str = "saaras:v3",
        tts_model: str = "bulbul:v3",
        tts_speaker: str = "shubh",
        stt_url: str = "https://api.sarvam.ai/speech-to-text",
        tts_url: str = "https://api.sarvam.ai/text-to-speech",
        timeout_seconds: float = 20.0,
        max_voice_bytes: int = 10 * 1024 * 1024,
        max_voice_duration_seconds: int = 30,
    ) -> None:
        self._api_key = api_key
        self._stt_model = stt_model
        self._tts_model = tts_model
        self._tts_speaker = tts_speaker
        self._stt_url = stt_url
        self._tts_url = tts_url
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 5.0))
        self.max_voice_bytes = max_voice_bytes
        self.max_voice_duration_seconds = max_voice_duration_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "SarvamService":
        return cls(
            api_key=settings.sarvam_api_key,
            stt_model=settings.sarvam_stt_model,
            tts_model=settings.sarvam_tts_model,
            tts_speaker=settings.sarvam_tts_speaker,
            stt_url=settings.sarvam_stt_url,
            tts_url=settings.sarvam_tts_url,
            timeout_seconds=settings.sarvam_request_timeout_seconds,
            max_voice_bytes=settings.sarvam_max_voice_bytes,
            max_voice_duration_seconds=settings.sarvam_max_voice_duration_seconds,
        )

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def transcribe(self, audio_path: Path) -> str:
        """Return a code-mixed transcription for a valid local audio file."""
        self._require_configuration()
        try:
            size = audio_path.stat().st_size
        except OSError as exc:
            raise SarvamError("I couldn't read that voice message. Please record it again.") from exc
        if not size:
            raise SarvamError("That voice message was empty. Please record it again.")
        if size > self.max_voice_bytes:
            raise SarvamError("That voice message is too large. Please send a shorter recording.")

        content_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
        try:
            with audio_path.open("rb") as audio_file:
                response = httpx.post(
                    self._stt_url,
                    headers=self._headers(),
                    data={"model": self._stt_model, "mode": "codemix"},
                    files={"file": (audio_path.name, audio_file, content_type)},
                    timeout=self._timeout,
                )
            self._raise_for_status(response, "speech transcription")
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise SarvamError("Voice transcription timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise SarvamError("Voice transcription is temporarily unavailable. Please try again.") from exc
        except OSError as exc:
            raise SarvamError("I couldn't read that voice message. Please record it again.") from exc
        except (ValueError, TypeError) as exc:
            raise SarvamError("Voice transcription returned an invalid response. Please try again.") from exc

        transcript = payload.get("transcript") if isinstance(payload, dict) else None
        if not isinstance(transcript, str) or not transcript.strip():
            raise SarvamError("I couldn't understand that voice message. Please try again clearly.")
        return transcript.strip()

    def synthesize(self, text: str, language: str) -> bytes:
        """Create Telegram-compatible Opus audio for an existing text response."""
        self._require_configuration()
        if not text.strip():
            raise SarvamError("The response was empty.")
        if len(text) > self.MAX_TTS_CHARACTERS:
            raise SarvamError("The response is too long for voice playback.")
        language_code = {"hi": "hi-IN", "en": "en-IN"}.get(language, "en-IN")
        try:
            response = httpx.post(
                self._tts_url,
                headers=self._headers(),
                json={
                    "text": text,
                    "language_code": language_code,
                    "model": self._tts_model,
                    "speaker": self._tts_speaker,
                    # Sarvam supports Opus output, which Telegram accepts as a
                    # voice message; requesting it avoids a converter dependency.
                    "output_audio_codec": "opus",
                },
                timeout=self._timeout,
            )
            self._raise_for_status(response, "voice reply")
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise SarvamError("Voice reply generation timed out.") from exc
        except httpx.RequestError as exc:
            raise SarvamError("Voice reply generation is temporarily unavailable.") from exc
        except (ValueError, TypeError) as exc:
            raise SarvamError("Voice reply generation returned an invalid response.") from exc

        audios = payload.get("audios") if isinstance(payload, dict) else None
        if not isinstance(audios, list) or not audios or not all(isinstance(item, str) for item in audios):
            raise SarvamError("Voice reply generation returned no audio.")
        try:
            audio = b"".join(base64.b64decode(item, validate=True) for item in audios)
        except (ValueError, binascii.Error) as exc:
            raise SarvamError("Voice reply generation returned invalid audio.") from exc
        if not audio:
            raise SarvamError("Voice reply generation returned no audio.")
        return audio

    def _headers(self) -> dict[str, str]:
        return {"api-subscription-key": self._api_key}

    def _require_configuration(self) -> None:
        if not self.available:
            raise SarvamConfigurationError(
                "Voice features are not configured yet. Please ask the clinic to configure Sarvam AI."
            )

    @staticmethod
    def _raise_for_status(response: httpx.Response, operation: str) -> None:
        if response.is_success:
            return
        # Do not log response bodies: they can include provider diagnostics and
        # request-related details. Status is enough for operational debugging.
        logger.warning("Sarvam %s failed with HTTP %s", operation, response.status_code)
        if response.status_code == 429:
            raise SarvamError("Voice service is busy right now. Please try again shortly.")
        raise SarvamError(f"{operation.capitalize()} is temporarily unavailable. Please try again.")
