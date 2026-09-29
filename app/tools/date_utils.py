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


def parse_date_from_text(value: str, today: date | None = None) -> dict:
    text = value.strip()
    direct = parse_date(text, today)
    if direct["success"]:
        return direct
    base = today or date.today()
    lowered = text.casefold()
    for phrase in ("day after tomorrow", "tomorrow", "next monday", "next tuesday", "next wednesday", "next thursday", "next friday", "next saturday", "next sunday"):
        if phrase in lowered:
            return parse_date(phrase, base)
    if not re.search(r"\d", text):
        return {"success": False, "error_code": "NO_DATE", "message": "No date was provided."}
    try:
        parsed = parser.parse(text, dayfirst=True, fuzzy=True, default=datetime(base.year, 1, 1)).date()
        return {"success": True, "date": parsed.isoformat(), "display_date": parsed.strftime("%d %B %Y")}
    except (TypeError, ValueError, OverflowError):
        return {"success": False, "error_code": "INVALID_DATE", "message": "I couldn't understand that date."}