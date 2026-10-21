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
    # Super Admin / Platform configuration
    super_admin_username: str = "superadmin"
    super_admin_password: str = "superadmin123"
    super_admin_password_hash: str = ""
    # CRM Admin Dashboard configuration
    crm_admin_username: str = "admin"
    crm_admin_password: str = "admin123"
    crm_admin_password_hash: str = ""
    crm_secret_key: str = "clinic-crm-secret-key-change-in-production"
    crm_token_expire_hours: int = 24
    # Phase 1A security hardening
    clinic_upi_id: str = ""
    allow_demo_password: bool = False
    app_env: str = "development"
    # Phase 1B database foundation
    database_url: str = ""
    # Meta WhatsApp Cloud API channel
    whatsapp_enabled: bool = False
    whatsapp_api_version: str = "v21.0"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_webhook_url: str = ""
    whatsapp_default_country_code: str = "91"
    whatsapp_tenant_phone_map: str = "{}"
    whatsapp_default_clinic_id: str = "default"

    @property
    def whatsapp_webhook_path(self) -> str:
        return "/webhook/whatsapp"

    def get_whatsapp_tenant_mapping(self) -> dict[str, str]:
        """Return phone_number_id -> tenant_id mapping (supports JSON or key:value,key:value)."""
        import json
        mapping = {}
        raw = (self.whatsapp_tenant_phone_map or "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    mapping = {str(k).strip(): str(v).strip() for k, v in parsed.items()}
            except Exception:
                for pair in raw.split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        if k.strip() and v.strip():
                            mapping[k.strip()] = v.strip()
        # Support explicit default clinic ID if configured for the primary test phone number
        if self.whatsapp_phone_number_id and self.whatsapp_phone_number_id not in mapping:
            if self.whatsapp_default_clinic_id:
                mapping[self.whatsapp_phone_number_id] = self.whatsapp_default_clinic_id.strip()
        return mapping


def get_settings() -> Settings:
    return Settings(
        clinic_name=os.getenv("CLINIC_NAME", "XYZ Clinic"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BOT_TOKEN", "")),
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
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
        super_admin_username=os.getenv("SUPER_ADMIN_USERNAME", "superadmin"),
        super_admin_password=os.getenv("SUPER_ADMIN_PASSWORD") or "AdminSecret2026!",
        super_admin_password_hash=os.getenv("SUPER_ADMIN_PASSWORD_HASH", ""),
        crm_admin_username=os.getenv("CRM_ADMIN_USERNAME", "admin"),
        crm_admin_password=os.getenv("CRM_ADMIN_PASSWORD", "admin123"),
        crm_admin_password_hash=os.getenv("CRM_ADMIN_PASSWORD_HASH", ""),
        crm_secret_key=os.getenv("CRM_SECRET_KEY", "clinic-crm-secret-key-change-in-production"),
        crm_token_expire_hours=int(os.getenv("CRM_TOKEN_EXPIRE_HOURS", "24")),
        clinic_upi_id=os.getenv("CLINIC_UPI_ID", ""),
        allow_demo_password=os.getenv("ALLOW_DEMO_PASSWORD", "").casefold() in ("true", "1", "yes"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", ""),
        whatsapp_enabled=os.getenv("WHATSAPP_ENABLED", "").casefold() in ("true", "1", "yes"),
        whatsapp_api_version=os.getenv("WHATSAPP_GRAPH_API_VERSION", os.getenv("WHATSAPP_API_VERSION", "v21.0")),
        whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        whatsapp_business_account_id=os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
        whatsapp_app_secret=os.getenv("WHATSAPP_APP_SECRET", ""),
        whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "kodnexus_verify_2026")),
        whatsapp_webhook_url=os.getenv("WHATSAPP_WEBHOOK_URL", ""),
        whatsapp_default_country_code=os.getenv("WHATSAPP_DEFAULT_COUNTRY_CODE", "91"),
        whatsapp_tenant_phone_map=os.getenv("WHATSAPP_TENANT_PHONE_MAP", "{}"),
        whatsapp_default_clinic_id=os.getenv("WHATSAPP_DEFAULT_CLINIC_ID", "default"),
    )


def validate_settings(settings: Settings) -> None:
    missing = []
    for name, value in (
        ("GEMINI_API_KEY", settings.gemini_api_key),
    ):
        if not value:
            missing.append(name)
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")

    # Phase 1A: reject insecure default or weak secret key in production
    if settings.app_env.casefold() == "production":
        if (
            not settings.crm_secret_key
            or settings.crm_secret_key == "clinic-crm-secret-key-change-in-production"
            or len(settings.crm_secret_key) < 16
        ):
            raise RuntimeError(
                "CRM_SECRET_KEY must be changed from its default value and be at least 16 characters before running in production. "
                "Set a strong, unique CRM_SECRET_KEY environment variable."
            )

    # Phase 1B: validate DATABASE_URL format if provided
    if settings.database_url:
        valid_prefixes = (
            "postgresql://",
            "postgresql+",
            "postgres://",
            "sqlite://",
        )
        if not any(settings.database_url.startswith(p) for p in valid_prefixes):
            raise RuntimeError(
                "Invalid DATABASE_URL format. Expected a PostgreSQL connection URL "
                "(e.g., postgresql+psycopg://user:password@localhost:5432/clinic_crm)."
            )
