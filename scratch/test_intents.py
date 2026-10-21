import re

def _is_reschedule_query(t): 
    return "reschedule" in t

def _is_cancel_query(t): 
    return "cancel" in t

def _is_clinic_hours_query(text: str) -> bool:
    lowered = text.casefold()
    if any(p in lowered for p in ("mera", "meri", "mujhe", "my", "appointment", "appoinment", "token", "tkn")):
        return False
    if any(w in lowered for w in ("clinic timing", "hospital timing", "kab khulta", "kab band", "opening time", "closing time", "clinic time", "hospital time")):
        return True
    return False

def _is_existing_appointment_query(text: str) -> bool:
    lowered = text.casefold()
    if _is_reschedule_query(lowered) or _is_cancel_query(lowered):
        return False
    if _is_clinic_hours_query(text):
        return False

    timing_arrival_phrases = (
        "kitne bje aana", "kitne baje aana", "kab aana hai", "kab aana", "kab pahunchna",
        "kis time aana", "mera time kya hai", "time kya hai", "timing kya hai",
        "samay kya hai", "kya time h", "kya time hai", "kitne bje hai", "kitne baje hai",
        "kab hai mera", "kab h mera", "what time should i come", "when should i come",
        "what time is my appointment", "what is my appointment time", "when is my appointment",
        "arrival time", "reporting time", "reach time", "clinic kab aana",
        "mera time", "mujhe kab aana", "mujhe kitne bje", "mujhe kitne baje",
    )
    if any(p in lowered for p in timing_arrival_phrases):
        return True
    already_booked_phrases = (
        "book kia hai", "book kiya hai", "book kia tha", "book kiya tha", "book kiya hu", "book kia hu",
        "book kr chuka", "book kar chuka", "book ho chuka", "book ho gaya", "booking ho gayi", "booking ho chuki",
        "already book", "already booked", "pehle se book", "already have an appointment",
        "i already booked", "i have booked", "i booked", "appointment ho gaya",
        "appointment ho chuka", "mera appointment hai", "meri booking hai",
        "mera appointment ho chuka", "booking already", "token number kya", "mera token number",
        "mera token kya hai", "token no kya",
    )
    if any(p in lowered for p in already_booked_phrases):
        return True
    if re.search(r"\b(maine|humne|mera|meri|mai|mein)\b.*\b(book|booking|appointment|appoinment)\b.*\b(hai|tha|thi|chuka|chuki|gaya|gayi)\b", lowered):
        return True
    if re.search(r"\b(already|pehle se)\b.*\b(booked|booking|appointment|appoinment)\b", lowered):
        return True
    if re.search(r"\b(kitne|kis|kya|kab)\b.*\b(bje|baje|time|samay)\b.*\b(aana|pahunchna|reach|mujhe|mera|appointment)\b", lowered):
        return True
    return False

test_cases = [
    ("kitne bje aana hai mujhe ?", True),
    ("kab pahunchna hai mujhe", True),
    ("mujhe kab aana hai", True),
    ("clinic timing kya hai", False),
    ("hospital kab khulta hai", False),
    ("maine appoinment book kia hai dr sufian se", True),
    ("arey mei appoinment book kr chuka hu", True),
    ("already booked", True),
    ("mera appointment kab hai", True),
    ("kab aana hai mujhe", True),
    ("kya time hai mere appointment ka", True),
    ("mera token number kya tha", True),
    ("mujhe appoinment chahiye 15 tarikh oct ka dr sufian se ya cardio wale se", False),
    ("I want to book an appointment with dr vivek", False),
    ("cancel my appointment", False),
    ("reschedule my appointment", False),
]

for query, expected in test_cases:
    actual = _is_existing_appointment_query(query)
    assert actual == expected, f"Failed for {query}: expected {expected}, got {actual}"
print("All test cases passed successfully!")

