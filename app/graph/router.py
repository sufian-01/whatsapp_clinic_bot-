"""Routing helpers for the conversational graph."""

import logging
from ..tools.doctors import match_health_concern

logger = logging.getLogger(__name__)

# Specialization terms that can appear in a doctor-list query
_SPECIALIZATION_TERMS = (
    "cardiologist", "cardiology", "gynecologist", "gynecology",
    "physician", "specialist", "orthopedic", "orthopedics",
    "dermatologist", "dermatology", "pediatrician", "pediatrics",
    "neurologist", "neurology", "psychiatrist", "psychiatry",
    "oncologist", "oncology", "ent", "ophthalmologist", "ophthalmology",
)


def _has_doctor_term(text: str) -> bool:
    """Return True only if a standalone doctor/physician/specialist term is present."""
    import re
    return bool(re.search(r"\b(doctor|doctors|dr|dr\.|physician|gynecologist|cardiologist|pediatrician|dermatologist|orthopedic|specialist)\b", text.lower()))


def classify_intent(state: dict) -> dict:
    text = state.get("user_text", "").lower()
    clean_text = text.strip()

    # 0. Interactive button quick action IDs
    if clean_text in ("btn_book_appointment", "📅 book appointment", "book appointment"):
        return {**state, "intent": "appointment_booking"}
    if clean_text in ("btn_clinic_info", "🏥 about hospital", "about hospital", "about clinic"):
        return {**state, "intent": "clinic_information"}
    if clean_text in ("btn_my_reports", "📄 my reports", "my reports", "my reports / rx"):
        return {**state, "intent": "report_enquiry"}

    # Standalone greeting (only when not in an active booking/reschedule/cancel flow)
    if _is_greeting(clean_text) and not state.get("appointment_step") and not state.get("reschedule_step") and not state.get("cancel_step"):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'greeting'", text)
        return {**state, "intent": "greeting"}

    # 1. Human support request
    if any(term in text for term in ("human", "real person", "support", "contact someone", "talk to someone", "human agent", "customer care")):
        return {**state, "intent": "human_support"}

    # 2. Lab / report enquiry
    if any(term in text for term in ("report", "test result", "lab result")):
        return {**state, "intent": "report_enquiry"}

    # 3. Active conversation steps
    if state.get("reschedule_step"):
        return {**state, "intent": "appointment_reschedule"}
    if state.get("cancel_step"):
        return {**state, "intent": "appointment_cancel"}
    if state.get("appointment_step") and state.get("appointment_step") != "complete":
        # Check if user explicitly switched to cancel, reschedule, or unrelated clinic/doctor info
        if _is_cancel_query(text) and any(w in text for w in ("booking", "appointment", "token", "tkn", "meri", "my")):
            return {**state, "intent": "appointment_cancel"}
        if _is_reschedule_query(text) and any(w in text for w in ("booking", "appointment", "token", "tkn", "meri", "my")):
            return {**state, "intent": "appointment_reschedule"}
        # If at email step and providing email address, stay in appointment_flow
        if state.get("appointment_step") == "email" and any(term in text for term in ("@", ".com", ".in", ".org")):
            return {**state, "intent": "appointment_flow"}

        # If at phone step and providing phone number with >= 5 digits, stay in appointment_flow
        import re
        if state.get("appointment_step") == "phone" and len(re.sub(r"\D", "", text)) >= 5:
            return {**state, "intent": "appointment_flow"}

        # Check if user is asking a clinic or doctor side-question during booking
        is_clinic_info = any(term in text for term in (
            "hours", "timing", "timings", "samay", "kab khulta", "khula", "band",
            "address", "where", "location", "kahan", "kaha", "kidhar", "pata", "jagah",
            "fee", "fees", "cost", "price", "charge", "charges", "kitna", "kitne", "rate", "paisa", "rupaye",
            "parking", "service", "services", "facility", "facilities", "qualification",
            "insurance", "mediclaim", "ayushman", "contact"
        ))
        if is_clinic_info:
            if _has_doctor_term(text):
                return {**state, "intent": "doctor_information"}
            return {**state, "intent": "clinic_information"}
        return {**state, "intent": "appointment_flow"}

    # 4. Reschedule intent
    if _is_reschedule_query(text):
        return {**state, "intent": "appointment_reschedule"}

    # 5. Cancellation intent
    if _is_cancel_query(text):
        return {**state, "intent": "appointment_cancel"}

    # 6. Check upcoming appointments
    if _is_my_appointments_query(text):
        return {**state, "intent": "patient_appointments"}

    # 7. Doctor list query or symptom concern
    if _is_doctor_list_query(text) or match_health_concern(text)[0] is not None:
        return {**state, "intent": "doctor_list"}

    # 8. Availability queries (including follow-ups like 'aur Friday ko?')
    if _is_availability_query(state, text):
        return {**state, "intent": "doctor_list"}

    # 9. Booking intent
    if _is_booking_query(text):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'appointment_booking'", text)
        return {**state, "intent": "appointment_booking"}

    # 10. Doctor information lookup
    if _has_doctor_term(text):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'doctor_information'", text)
        return {**state, "intent": "doctor_information"}

    # 11. General clinic information
    is_clinic_info = any(term in text for term in ("clinic", "hours", "timing", "address", "where", "location", "kahan", "service", "test", "price"))
    if is_clinic_info:
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'clinic_information'", text)
        return {**state, "intent": "clinic_information"}

    logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'other_help'", text)
    return {**state, "intent": "other_help"}


def _is_booking_query(text: str) -> bool:
    """True if user wants to book an appointment, consult a doctor, or reserve a slot."""
    import re
    lowered = text.casefold()

    # Rule out queries that clearly belong to other intents
    if _is_reschedule_query(lowered) or _is_cancel_query(lowered):
        return False
    if any(q in lowered for q in ("policy", "rules", "rule", "fee", "fees", "charge", "charges", "hours", "timing", "address", "location")):
        return False

    # 1. Direct booking / consultation keywords & common typos of appointment
    booking_terms = (
        "book", "booking", "schedule", "consult", "consultation",
        "appointment", "appoinment", "apointment", "appointmnt", "apointmnt",
        "apmnt", "appmnt", "apt",
    )
    if any(term in lowered for term in booking_terms):
        return True

    # 2. Hinglish & Hindi booking requests
    hinglish_booking_phrases = (
        "dikhana hai", "dikhana chahta", "dikhana chahti", "dikhao",
        "milna hai", "milna chahta", "milna chahti",
        "checkup karana", "checkup karani",
        "appointment lena", "appoinment lena", "booking lena",
        "appointment kar do", "appoinment kar do", "booking kar do",
        "slot chahiye", "appointment chahiye", "appoinment chahiye", "booking chahiye",
    )
    if any(phrase in lowered for phrase in hinglish_booking_phrases):
        return True

    # 3. Regex patterns: e.g. "doctor ko dikhana", "slot chahiye"
    if re.search(r"\b(doctor|dr|specialist)\b.*\b(dikhana|dikhao|milna|checkup)\b", lowered):
        return True
    if re.search(r"\b(slot|token|tkn)\b.*\b(chahiye|book|karna|karni|lena|leni|kar do)\b", lowered):
        return True
    if re.search(r"\b(chahiye|karna|karni|lena|leni)\b.*\b(slot|token|tkn)\b", lowered):
        return True

    return False


def _is_reschedule_query(text: str) -> bool:
    """True if text indicates intent to reschedule or change an appointment."""
    import re
    lowered = text.casefold()
    reschedule_terms = (
        "reschedule", "re-schedule", "postpone", "prepone",
        "change appointment", "change booking", "change date", "change time", "change slot",
        "change my appointment", "change my booking", "change my date", "change my time", "change my slot",
        "shift appointment", "move appointment", "shift my appointment", "move my appointment",
        "different date", "different time",
        "dusra time", "dusri date", "dusra din", "dusre din", "dusra slot",
        "badal do", "badalna", "badalni", "time change", "date change", "booking change",
        "aage badha", "aage shift", "kal nahi parso", "dusre time", "agla time",
        "appointment change", "appointment badal", "appointment reschedule", "reschedule appointment",
        "change karni", "change karna", "badalna hai", "badalni hai",
        "kal ke liye kar do", "parso ke liye kar do", "shift kar do", "move kar do",
    )
    if any(term in lowered for term in reschedule_terms):
        return True
    if re.search(r"\b(change|shift|move|badal|reschedule)\b.*\b(appointment|date|time|slot|booking)\b", lowered):
        return True
    if re.search(r"\b(appointment|booking|date|time|slot)\b.*\b(change|shift|move|badal|reschedule)\b", lowered):
        return True
    return False


def _is_cancel_query(text: str) -> bool:
    """True if text indicates intent to cancel an appointment."""
    import re
    lowered = text.casefold()
    # Avoid routing policy/inquiry questions
    if any(q in lowered for q in ("policy", "rule", "rules", "charge", "charges", "fee")):
        return False
    cancel_terms = (
        "cancel appointment", "cancel booking", "cancel my appointment", "cancel my booking",
        "drop my appointment", "drop appointment", "delete my booking", "delete booking",
        "cancel slot", "cancel karo", "cancel karni", "cancel karna", "cancel kar do",
        "radd karni", "radd karna", "radd kar do",
        "don't want appointment", "dont want appointment", "nahi aana", "nahi aa sakta",
        "nahi aa sakti", "hata do booking", "cancel my",
        "appointment cancel", "booking cancel", "meri booking cancel", "meri appointment cancel",
        "cancel kar dijiye",
    )
    if any(term in lowered for term in cancel_terms):
        return True
    if re.search(r"\b(cancel|drop|delete|remove|radd)\b.*\b(appointment|booking|slot|tkn|token)\b", lowered):
        return True
    if re.search(r"\b(appointment|booking|slot|tkn|token)\b.*\b(cancel|drop|delete|remove|radd)\b", lowered):
        return True
    words = lowered.split()
    if "cancel" in words and any(w in words for w in ("it", "appointment", "booking", "slot", "tkn", "token", "my")):
        return True
    if lowered.strip() in {"cancel", "cancel appointment", "appointment cancel"}:
        return True
    return False


def _is_my_appointments_query(text: str) -> bool:
    """True if patient is asking to view their upcoming appointments."""
    lowered = text.casefold()
    if _is_reschedule_query(lowered) or _is_cancel_query(lowered):
        return False
    check_terms = (
        "my appointment", "my appointments", "my booking", "my bookings",
        "check appointment", "check booking", "show appointment", "show booking",
        "view appointment", "view booking", "status of appointment",
        "when is my appointment", "mera appointment kab", "meri booking",
        "upcoming appointment", "upcoming appointments", "meri appointment",
    )
    return any(term in lowered for term in check_terms)


def _is_availability_query(state: dict, text: str) -> bool:
    """Recognize direct and Hinglish questions about factual appointment slots."""
    availability_terms = (
        "available", "availability", "free", "slot", "slots", "when", "kab", "aur kab",
        "timing", "timings", "schedule", "milenge", "milte", "dekh sakte",
    )
    if any(term in text for term in availability_terms):
        has_doctor_reference = any(term in text for term in ("doctor", "doctors", "dr", "physician", "specialist"))
        return has_doctor_reference or bool(state.get("doctor_name"))

    if "recommend" in text and any(term in text for term in ("doctor", "dr")):
        return True

    # Follow-up with selected doctor: e.g. "aur Friday ko?", "aur kal?", "kal free hain?"
    if state.get("doctor_name"):
        from ..tools.date_utils import parse_date_from_text
        if parse_date_from_text(text).get("success"):
            return True
        if any(term in text for term in ("aur", "what about", "how about", "next", "and")):
            return True

    return False


def _is_doctor_list_query(text: str) -> bool:
    """True when the user is asking to see the list of available doctors or specialists.

    Covers patterns like:
    - "Which doctors are available?"
    - "Who are your doctors?"
    - "Which doctor should I consult?"
    - "What doctors do you have?"
    - "Which dr are available on 29th?"
    - "Which cardiologist is available?"
    - "Show me the doctors"
    """
    has_list_trigger = any(
        phrase in text for phrase in (
            "which doctor", "which dr", "available doctor", "list doctor",
            "list of doctor", "show doctor", "show me the doctor",
            "show me doctor", "who are the doctor", "who are your doctor",
            "what doctor", "any doctor", "which specialist", "which physician",
            "doctor list", "all doctor", "tell me your doctor",
            "doctor ki list", "doctors ki list", "list dikhao", "list batao",
            "doctors list", "doctor dikhao", "doctors dikhao",
        )
    )
    if has_list_trigger:
        return True

    # "which <specialization> is available?" or "which <specialization> do you have?"
    has_which = any(w in text for w in ("which", "what", "any", "who"))
    has_spec = any(spec in text for spec in _SPECIALIZATION_TERMS)
    has_available = any(w in text for w in ("available", "have", "consult", "see", "visit"))

    if (has_which and has_spec) or (has_spec and has_available) or (has_spec and "need" in text):
        return True

    # "available doctors/dr today?" pattern
    has_doctor_term = any(term in text for term in ("doctor", "dr", "physician", "specialist"))
    if has_doctor_term and "available" in text:
        return True

    return False


def _is_greeting(text: str) -> bool:
    """True if user input is an initial greeting or conversation opener without a specific query."""
    import re
    lowered = text.casefold().strip()
    if not lowered:
        return False
    # If booking, reschedule, cancel, doctor, or info query, not a standalone greeting
    excluded = (
        "book", "booking", "appointment", "appoinment", "cancel", "reschedule",
        "doctor", "dr", "timing", "fee", "fees", "report", "slot", "token", "tkn",
        "pain", "fever", "ill", "sick", "problem", "dawa", "medicine"
    )
    if any(k in lowered for k in excluded):
        return False
    greeting_tokens = {
        "hi", "hii", "hiii", "hello", "helloo", "hey", "heyy", "namaste", "namaskar",
        "salam", "salaam", "pranam", "start", "menu", "options", "shuru", "halo",
    }
    words = set(re.findall(r"\b\w+\b", lowered))
    if words and words.issubset(greeting_tokens):
        return True
    return lowered in greeting_tokens


def route_intent(state: dict) -> str:
    return state.get("intent", "other_help")

