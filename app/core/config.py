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