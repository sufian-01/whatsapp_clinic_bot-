"""Deterministic natural-language date normalization."""

from datetime import date, datetime, timedelta
import re

from dateutil import parser


def parse_date(value: str, today: date | None = None) -> dict:
    text = value.strip()
    base = today or date.today()
    lowered = text.casefold()
    if lowered == "tomorrow":
        parsed = base + timedelta(days=1)
    elif lowered == "day after tomorrow":
        parsed = base + timedelta(days=2)
    elif lowered.startswith("next ") and lowered[5:] in {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}:
        target = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(lowered[5:])
        days = (target - base.weekday()) % 7 or 7
        parsed = base + timedelta(days=days)
    else:
        if not re.search(r"\d", text):
            return {"success": False, "error_code": "INVALID_DATE", "message": "I couldn't understand that date."}
        try:
            parsed = parser.parse(text, dayfirst=True, fuzzy=False).date()
        except (TypeError, ValueError, OverflowError):
            return {"success": False, "error_code": "INVALID_DATE", "message": "I couldn't understand that date."}
    return {"success": True, "date": parsed.isoformat(), "display_date": parsed.strftime("%d %B %Y")}