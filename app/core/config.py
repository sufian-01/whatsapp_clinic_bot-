"""Environment-backed application settings."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    clinic_name: str
    telegram_bot_token: str
    telegram_webhook_secret: str
    gemini_api_key: str
    gemini_model: str
    telegram_webhook_url: str
    knowledge_dir: Path
    vectorstore_dir: Path
    webhook_path: str = "/webhook/telegram"
    support_phone: str = "6200126662"
    clinic_sheet_id: str = ""
    clinic_sheet_range: str = "Sheet1!A1:Z1000"
    patient_sheet_range: str = "patient!A1:Z1000"
    appointment_slot_sheet_range: str = "appointment_slots!A1:Z5000"
    clinic_timezone: str = "Asia/Kolkata"
    # Voice is optional.  Keeping these defaults here lets text chat start even
    # when Sarvam has not yet been configured.
    sarvam_api_key: str = ""
    sarvam_stt_model: str = "saaras:v3"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"
    sarvam_stt_url: str = "https://api.sarvam.ai/speech-to-text"
    sarvam_tts_url: str = "https://api.sarvam.ai/text-to-speech"
    sarvam_request_timeout_seconds: float = 20.0
    sarvam_max_voice_bytes: int = 10 * 1024 * 1024
    sarvam_max_voice_duration_seconds: int = 30
    # CRM Admin Dashboard configuration
    crm_admin_username: str = "admin"
    crm_admin_password: str = "admin123"
    crm_admin_password_hash: str = ""
    crm_secret_key: str = "clinic-crm-secret-key-change-in-production"
    crm_token_expire_hours: int = 24


def get_settings() -> Settings:
    return Settings(
        clinic_name=os.getenv("CLINIC_NAME", "XYZ Clinic"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BOT_TOKEN", "")),
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        telegram_webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL", ""),
        knowledge_dir=ROOT_DIR / "data" / "knowledge",
        vectorstore_dir=ROOT_DIR / "data" / "vectorstore",
        support_phone=os.getenv("CLINIC_SUPPORT_PHONE", "6200126662"),
        clinic_sheet_id=os.getenv("CLINIC_SHEET_ID", ""),
        clinic_sheet_range=os.getenv("CLINIC_SHEET_RANGE", "Sheet1!A1:Z1000"),
        patient_sheet_range=os.getenv("PATIENT_SHEET_RANGE", "patient!A1:Z1000"),
        appointment_slot_sheet_range=os.getenv("APPOINTMENT_SLOT_SHEET_RANGE", "appointment_slots!A1:Z5000"),
        clinic_timezone=os.getenv("CLINIC_TIMEZONE", "Asia/Kolkata"),
        sarvam_api_key=os.getenv("SARVAM_API_KEY", ""),
        sarvam_stt_model=os.getenv("SARVAM_STT_MODEL", "saaras:v3"),
        sarvam_tts_model=os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"),
        sarvam_tts_speaker=os.getenv("SARVAM_TTS_SPEAKER", "shubh"),
        sarvam_stt_url=os.getenv("SARVAM_STT_URL", "https://api.sarvam.ai/speech-to-text"),
        sarvam_tts_url=os.getenv("SARVAM_TTS_URL", "https://api.sarvam.ai/text-to-speech"),
        sarvam_request_timeout_seconds=float(os.getenv("SARVAM_REQUEST_TIMEOUT_SECONDS", "20")),
        sarvam_max_voice_bytes=int(os.getenv("SARVAM_MAX_VOICE_BYTES", str(10 * 1024 * 1024))),
        sarvam_max_voice_duration_seconds=int(os.getenv("SARVAM_MAX_VOICE_DURATION_SECONDS", "30")),
        crm_admin_username=os.getenv("CRM_ADMIN_USERNAME", "admin"),
        crm_admin_password=os.getenv("CRM_ADMIN_PASSWORD", "admin123"),
        crm_admin_password_hash=os.getenv("CRM_ADMIN_PASSWORD_HASH", ""),
        crm_secret_key=os.getenv("CRM_SECRET_KEY", "clinic-crm-secret-key-change-in-production"),
        crm_token_expire_hours=int(os.getenv("CRM_TOKEN_EXPIRE_HOURS", "24")),
    )


def validate_settings(settings: Settings) -> None:
    missing = []
    for name, value in (
        ("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token),
        ("GEMINI_API_KEY", settings.gemini_api_key),
    ):
        if not value:
            missing.append(name)
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")
