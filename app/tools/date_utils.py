"""Deterministic natural-language date normalization for clinic booking."""

from datetime import date, datetime, timedelta
import re

from dateutil import parser


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

_HINDI_WEEKDAYS = {
    "somvar": "monday",
    "somwar": "monday",
    "mangalvar": "tuesday",
    "mangalwar": "tuesday",
    "budhvar": "wednesday",
    "budhwar": "wednesday",
    "guruvar": "thursday",
    "guruwar": "thursday",
    "veervar": "thursday",
    "veerwar": "thursday",
    "shukravar": "friday",
    "shukrawar": "friday",
    "shanivar": "saturday",
    "shaniwar": "saturday",
    "ravivar": "sunday",
    "raviwar": "sunday",
    "itvar": "sunday",
    "itwar": "sunday",
}

_HINDI_RELATIVE = {
    "aaj": "today",
    "kal": "tomorrow",
    "kal subah": "tomorrow",
    "kal shaam": "tomorrow",
    "kal sham": "tomorrow",
    "kal dopahar": "tomorrow",
    "parso": "day after tomorrow",
    "parson": "day after tomorrow",
}


def _normalize_hindi_date_phrase(text: str) -> str:
    """Normalize Hindi/Hinglish date words to standard English tokens."""
    lowered = " ".join(text.casefold().split())

    # Direct relative phrases
    if lowered in _HINDI_RELATIVE:
        return _HINDI_RELATIVE[lowered]

    # Clean out time-of-day words if accompanied by kal/parso
    clean = re.sub(r"\b(subah|shaam|sham|dopahar|raat|ko)\b", " ", lowered)
    clean = " ".join(clean.split())
    if clean in _HINDI_RELATIVE:
        return _HINDI_RELATIVE[clean]

    # Map Hindi weekday names
    for hindi_day, eng_day in _HINDI_WEEKDAYS.items():
        clean = re.sub(rf"\b{hindi_day}\b", eng_day, clean)

    # Map prefixes: 'agle' -> 'next', 'is' / 'iss' -> 'this'
    clean = re.sub(r"\bagle\b", "next", clean)
    clean = re.sub(r"\b(is|iss)\b", "this", clean)

    return " ".join(clean.split())


def parse_date(value: str, today: date | None = None) -> dict:
    """Parse a patient date without accepting past appointments.

    ``today`` is injectable because callers supply the clinic's local date,
    rather than relying on the server timezone.
    """
    text = value.strip()
    base = today or date.today()
    enforce_future = today is not None

    # First normalize any Hindi/Hinglish terms
    normalized = _normalize_hindi_date_phrase(text)
    if not normalized:
        return _invalid()

    if normalized == "today":
        parsed = base
    elif normalized == "tomorrow":
        parsed = base + timedelta(days=1)
    elif normalized == "day after tomorrow":
        parsed = base + timedelta(days=2)
    else:
        weekday_match = re.fullmatch(r"(?:(this|next)\s+)?(" + "|".join(_WEEKDAYS) + r")", normalized)
        if weekday_match:
            qualifier, weekday = weekday_match.groups()
            target = _WEEKDAYS.index(weekday)
            days = (target - base.weekday()) % 7
            if qualifier == "next" and days == 0:
                days = 7
            parsed = base + timedelta(days=days)
        elif re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", normalized.strip()):
            day_match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", normalized.strip())
            day = int(day_match.group(1))
            if 1 <= day <= 31:
                try:
                    target_date = date(base.year, base.month, day)
                    if enforce_future and target_date < base:
                        m = base.month + 1
                        y = base.year
                        if m > 12:
                            m = 1
                            y += 1
                        target_date = date(y, m, day)
                    parsed = target_date
                except ValueError:
                    return _invalid()
            else:
                return _invalid()
        else:
            if not re.search(r"\d", text):
                return _invalid()
            iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text.strip())
            if iso_match:
                try:
                    parsed = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
                except ValueError:
                    return _invalid()
            else:
                try:
                    parsed = parser.parse(text, dayfirst=True, fuzzy=False, default=datetime(base.year, 1, 1)).date()
                except (TypeError, ValueError, OverflowError):
                    return _invalid()
            if parsed < base and not re.search(r"\b\d{4}\b", text):
                try:
                    parsed = parsed.replace(year=base.year + 1)
                except ValueError:
                    return _invalid("Please include a year for that date.")

    if enforce_future and parsed < base:
        return {"success": False, "error_code": "PAST_DATE", "message": "Please choose today or a future date."}
    return {"success": True, "date": parsed.isoformat(), "display_date": parsed.strftime("%d %B %Y")}


def parse_date_from_text(value: str, today: date | None = None) -> dict:
    """Extract one date from a complete patient sentence."""
    text = value.strip()
    direct = parse_date(text, today)
    if direct["success"]:
        return direct
    base = today or date.today()
    lowered = " ".join(text.casefold().split())

    # Phrases sorted by descending length to match "day after tomorrow" / "kal subah" before "kal"
    phrases = [
        "day after tomorrow", "parson", "parso",
        "kal subah", "kal shaam", "kal sham", "kal dopahar",
        "tomorrow", "today", "aaj", "kal",
        *(f"next {weekday}" for weekday in _WEEKDAYS),
        *(f"this {weekday}" for weekday in _WEEKDAYS),
        *(f"agle {weekday}" for weekday in _WEEKDAYS),
        *(f"is {weekday}" for weekday in _WEEKDAYS),
        *(f"agle {hday}" for hday in _HINDI_WEEKDAYS),
        *(f"is {hday}" for hday in _HINDI_WEEKDAYS),
        *list(_WEEKDAYS),
        *list(_HINDI_WEEKDAYS.keys()),
    ]
    for phrase in phrases:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            parsed = parse_date(phrase, base)
            if parsed["success"]:
                return parsed

    candidate = _extract_date_candidate(text)
    if candidate:
        return parse_date(candidate, base)
    if not re.search(r"\d", text):
        return {"success": False, "error_code": "NO_DATE", "message": "No date was provided."}
    try:
        parsed = parser.parse(text, dayfirst=True, fuzzy=True, default=datetime(base.year, 1, 1)).date()
    except (TypeError, ValueError, OverflowError):
        return _invalid()
    return parse_date(parsed.isoformat(), base)


_INVALID_DATE_MESSAGE = "Maaf kijiye, aap kis date ki baat kar rahe hain?\nAap date jaise 30 September bhi bata sakte hain."


def _invalid(message: str | None = None) -> dict:
    return {"success": False, "error_code": "INVALID_DATE", "message": message or _INVALID_DATE_MESSAGE}


def _extract_date_candidate(text: str) -> str | None:
    """Find common date fragments inside a longer patient sentence."""
    month_names = "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    patterns = (
        rf"\b\d{{4}}-\d{{1,2}}-\d{{1,2}}\b",
        rf"\b\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}\b",
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{month_names})(?:\s+\d{{4}})?\b",
        rf"\b(?:{month_names})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b",
        rf"\b\d{{1,2}}(?:st|nd|rd|th)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", match.group(0), flags=re.IGNORECASE)
    return None
