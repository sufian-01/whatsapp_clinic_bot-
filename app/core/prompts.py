"""Load prompts from files so each future tenant can provide its own prompt."""

from pathlib import Path


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "clinic_system.txt"


def load_system_prompt(clinic_name: str, support_phone: str = "6200126662") -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").format(
        clinic_name=clinic_name,
        support_phone=support_phone,
    )