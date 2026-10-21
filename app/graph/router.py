"""Routing helpers for the conversational graph."""

import logging
from typing import Any, Optional
from ..tools.doctors import match_health_concern, resolve_specialization

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


def _is_draft_cancel_or_rejection(text: str) -> bool:
    """True if user wants to cancel, abandon, reject, or stop the current in-progress booking flow."""
    import re
    lowered = text.casefold().strip()
    if _is_cancel_query(lowered):
        return True

    # Negative rejections of booking flow: e.g. "appoinment ki batt ni kr rha mei", "nahi chahiye", "rehne do"
    rejection_phrases = (
        "rehne do", "rehne de", "nahi chahiye", "nahi karna", "nahi karni", "mat karo", "chhod do", "chhor do",
        "baat nahi kar raha", "batt ni kr rha", "baat nahi kar rahe", "baat nahi ho rahi", "baat nhi",
        "nahi mang raha", "nahi maang raha", "nahi bola", "nahi bol raha", "ni kr rha", "nahi kar raha",
        "appointment nahi", "appoinment nahi", "no appointment", "nahi chahiye appointment",
        "nahi karwana", "nahi book karna", "nahi book karni", "khatam karo", "band karo",
        "stop", "exit", "quit", "abort", "cancel kar", "cancel karo", "nahi lena", "nahi leni",
    )
    if any(p in lowered for p in rejection_phrases):
        return True

    if re.search(r"\b(appoinment|appointment|booking)\b.*\b(baat|batt|nahi|nhi|mat|rehne|cancel|ni)\b", lowered):
        return True
    if re.search(r"\b(baat|batt|nahi|nhi|mat|rehne|cancel)\b.*\b(appoinment|appointment|booking)\b", lowered):
        return True
    if lowered in {"cancel", "nahi", "no", "stop", "exit", "quit", "nhi"}:
        return True
    return False


def classify_intent(state: dict, llm: Optional[Any] = None) -> dict:
    text = state.get("user_text", "").lower()
    clean_text = text.strip()

    # 0. Interactive button quick action IDs (instant 0ms)
    if clean_text in ("btn_book_appointment", "📅 book appointment", "book appointment"):
        return {**state, "intent": "appointment_booking"}
    if clean_text in ("btn_clinic_info", "🏥 about hospital", "about hospital", "about clinic"):
        return {**state, "intent": "clinic_information"}
    if clean_text in ("btn_my_reports", "📄 my reports", "my reports", "my reports / rx"):
        return {**state, "intent": "report_enquiry"}

    # 1. Standalone greeting (only when not in an active booking/reschedule/cancel flow)
    if _is_greeting(clean_text) and not state.get("appointment_step") and not state.get("reschedule_step") and not state.get("cancel_step"):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'greeting'", text)
        return {**state, "intent": "greeting"}

    # 2. Universal Cancellation / Drop flow check (HIGHEST PRIORITY)
    if _is_draft_cancel_or_rejection(text):
        if state.get("appointment_step") or state.get("active_flow") == "appointment_booking":
            logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'appointment_draft_cancel'", text)
            return {
                **state,
                "intent": "appointment_draft_cancel",
                "interruption_type": "cancellation",
            }
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'appointment_cancel'", text)
        return {**state, "intent": "appointment_cancel"}

    # 3. Fast direct field validations (avoid unnecessary LLM calls for obvious answers)
    curr_step = state.get("appointment_step")
    import re
    if curr_step == "doctor":
        is_side_info = any(term in text for term in (
            "hours", "timing", "timings", "samay", "kab khulta", "khula", "band",
            "address", "where", "location", "kahan", "kaha", "kidhar", "pata", "jagah",
            "fee", "fees", "cost", "price", "charge", "charges", "kitna", "kitne", "rate", "paisa", "rupaye",
            "parking", "service", "services", "facility", "facilities", "qualification",
            "insurance", "mediclaim", "ayushman", "contact"
        )) or _is_clinic_hours_query(text)
        if not is_side_info and not _is_draft_cancel_or_rejection(text):
            return {**state, "intent": "appointment_flow", "active_flow": "appointment_booking", "pending_field": "doctor"}
    if curr_step == "phone" and len(re.sub(r"\D", "", clean_text)) >= 7:
        return {**state, "intent": "appointment_flow", "active_flow": "appointment_booking", "pending_field": "phone"}
    if curr_step == "email" and ("@" in clean_text or clean_text == "skip"):
        return {**state, "intent": "appointment_flow", "active_flow": "appointment_booking", "pending_field": "email"}
    if curr_step in ("slot", "pre_patient_slot") and (clean_text.startswith("slot:") or clean_text.isdigit()):
        return {**state, "intent": "appointment_flow", "active_flow": "appointment_booking", "pending_field": curr_step}
    if curr_step == "name":
        lowered_txt = text.strip()
        is_q = "?" in lowered_txt or any(w in lowered_txt.split() for w in ("kya", "kyu", "kyun", "why", "who", "which", "kaise", "what", "kab", "kitne", "kahan", "batao", "btao"))
        has_info = any(term in text for term in ("hours", "timing", "address", "fee", "fees", "cost", "parking"))
        if not is_q and not has_info and not _is_doctor_list_query(text) and not _is_draft_cancel_or_rejection(text):
            return {**state, "intent": "appointment_flow", "active_flow": "appointment_booking", "pending_field": "name"}

    # Deterministic 0ms queries when not in flow (saves LLM tokens and quota)
    if not curr_step and not state.get("reschedule_step") and not state.get("cancel_step"):
        if _is_booking_query(text) and not _is_doctor_list_query(text):
            logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'appointment_booking' (deterministic)", text)
            return {**state, "intent": "appointment_booking"}
        if (
            _is_doctor_list_query(text)
            or match_health_concern(text)[0] is not None
            or resolve_specialization(text) is not None
        ):
            logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'doctor_list' (deterministic)", text)
            return {**state, "intent": "doctor_list"}

    # 4. AI-First Semantic Intent Classifier (Gemini LLM)
    from ..core.feature_flags import is_feature_enabled, FEATURE_AI_AGENT
    if llm and is_feature_enabled(state.get("feature_flags", {}), FEATURE_AI_AGENT, default=True):
        from ..llm.classifier import classify_with_ai
        ai_res = classify_with_ai(
            llm=llm,
            user_text=state.get("user_text", ""),
            active_flow=state.get("active_flow") or ("appointment_booking" if curr_step else None),
            current_step=curr_step,
            history=state.get("messages", []),
        )
        if ai_res and ai_res.get("intent"):
            ai_intent = ai_res["intent"]
            is_canc = ai_res.get("is_cancellation", False)
            is_side_q = ai_res.get("is_side_question", False)

            if is_canc or ai_intent == "appointment_draft_cancel":
                if curr_step or state.get("active_flow") == "appointment_booking":
                    return {**state, "intent": "appointment_draft_cancel", "interruption_type": "cancellation"}
                return {**state, "intent": "appointment_cancel"}

            if is_side_q or (curr_step and ai_intent in ("doctor_list", "doctor_information", "clinic_information")):
                resume_ctx = {
                    "flow": "appointment_booking",
                    "pending_field": curr_step,
                    "interrupted_at_step": curr_step,
                }
                return {
                    **state,
                    "intent": ai_intent,
                    "interruption_type": "side_question",
                    "resume_context": resume_ctx,
                    "active_flow": "appointment_booking",
                }

            if ai_intent == "appointment_flow":
                return {
                    **state,
                    "intent": "appointment_flow",
                    "active_flow": "appointment_booking",
                    "pending_field": curr_step,
                }

            if ai_intent == "appointment_booking":
                if curr_step and curr_step != "complete":
                    return {
                        **state,
                        "intent": "appointment_flow",
                        "active_flow": "appointment_booking",
                        "pending_field": curr_step,
                    }
                return {**state, "intent": "appointment_booking"}

            if ai_intent in ("doctor_list", "doctor_information", "clinic_information", "patient_appointments", "report_enquiry", "human_support", "greeting", "appointment_reschedule", "appointment_cancel", "other_help"):
                return {**state, "intent": ai_intent}

    # 5. Deterministic Rule-Based Fallback (zero LLM token mode or offline fallback)
    # Human support request
    if any(term in text for term in ("human", "real person", "support", "contact someone", "talk to someone", "human agent", "customer care")):
        return {**state, "intent": "human_support"}

    # Lab / report enquiry
    if any(term in text for term in ("report", "test result", "lab result")) or "report ke baare mein" in text:
        if state.get("appointment_step"):
            return {
                **state,
                "intent": "report_enquiry",
                "interruption_type": "unrelated",
                "appointment_step": "complete",
                "active_flow": None,
            }
        return {**state, "intent": "report_enquiry"}

    # Check upcoming appointments or timing of booked visit
    if _is_my_appointments_query(text) or _is_existing_appointment_query(text):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'patient_appointments'", text)
        return {**state, "intent": "patient_appointments", "appointment_step": "complete"}

    # Reschedule intent
    if _is_reschedule_query(text):
        return {**state, "intent": "appointment_reschedule"}

    # 7. Active booking flow handling
    if state.get("appointment_step") and state.get("appointment_step") != "complete":
        step = state.get("appointment_step")

        # Check if user asked a side question about doctor list
        if _is_doctor_list_query(text) or (step == "name" and resolve_specialization(text) is not None):
            resume_ctx = {
                "flow": "appointment_booking",
                "pending_field": step,
                "interrupted_at_step": step,
            }
            return {
                **state,
                "intent": "doctor_list",
                "interruption_type": "side_question",
                "resume_context": resume_ctx,
                "active_flow": "appointment_booking",
            }

        # Check if user asked a clinic or doctor side question (hours, address, fees, etc.)
        is_clinic_info = any(term in text for term in (
            "hours", "timing", "timings", "samay", "kab khulta", "khula", "band",
            "address", "where", "location", "kahan", "kaha", "kidhar", "pata", "jagah",
            "fee", "fees", "cost", "price", "charge", "charges", "kitna", "kitne", "rate", "paisa", "rupaye",
            "parking", "service", "services", "facility", "facilities", "qualification",
            "insurance", "mediclaim", "ayushman", "contact", "kaun"
        )) or _is_clinic_hours_query(text)
        if is_clinic_info:
            resume_ctx = {
                "flow": "appointment_booking",
                "pending_field": step,
                "interrupted_at_step": step,
            }
            if _has_doctor_term(text):
                return {
                    **state,
                    "intent": "doctor_information",
                    "interruption_type": "side_question",
                    "resume_context": resume_ctx,
                    "active_flow": "appointment_booking",
                }
            return {
                **state,
                "intent": "clinic_information",
                "interruption_type": "side_question",
                "resume_context": resume_ctx,
                "active_flow": "appointment_booking",
            }

        # Check if user asked a general question during name step
        lowered_txt = text.strip()
        is_question = "?" in lowered_txt or any(w in lowered_txt.split() for w in ("kya", "kyu", "kyun", "why", "who", "which", "kaise", "what", "kab", "kitne", "kahan", "batao", "btao"))
        if is_question and step == "name":
            resume_ctx = {
                "flow": "appointment_booking",
                "pending_field": step,
                "interrupted_at_step": step,
            }
            return {
                **state,
                "intent": "other_help",
                "interruption_type": "side_question",
                "resume_context": resume_ctx,
                "active_flow": "appointment_booking",
            }

        # Otherwise, the user is advancing the booking flow
        return {
            **state,
            "intent": "appointment_flow",
            "active_flow": "appointment_booking",
            "pending_field": step,
        }

    if state.get("reschedule_step"):
        return {**state, "intent": "appointment_reschedule"}
    if state.get("cancel_step"):
        return {**state, "intent": "appointment_cancel"}

    # 8. Booking intent initiation (takes priority if user explicitly requests to book)
    if _is_booking_query(text) and not _is_doctor_list_query(text):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'appointment_booking'", text)
        return {**state, "intent": "appointment_booking"}

    # 9. Doctor list query or symptom concern
    if (
        _is_doctor_list_query(text)
        or match_health_concern(text)[0] is not None
        or resolve_specialization(text) is not None
        or _is_availability_query(state, text)
    ):
        return {**state, "intent": "doctor_list"}

    # 10. Booking fallback if _is_booking_query was true
    if _is_booking_query(text):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'appointment_booking'", text)
        return {**state, "intent": "appointment_booking"}

    # 11. Doctor information lookup
    if _has_doctor_term(text):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'doctor_information'", text)
        return {**state, "intent": "doctor_information"}

    # 12. General clinic information
    is_general_info = any(term in text for term in ("clinic", "hours", "timing", "address", "where", "location", "kahan", "service", "test", "price"))
    if is_general_info or _is_clinic_hours_query(text):
        logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'clinic_information'", text)
        return {**state, "intent": "clinic_information"}

    logger.info("[ROUTER] User text: '%s' -> Classified Intent: 'other_help'", text)
    return {**state, "intent": "other_help"}


def _is_booking_query(text: str) -> bool:
    """True if user wants to book an appointment, consult a doctor, or reserve a slot."""
    import re
    lowered = text.casefold()

    # Rule out queries that clearly belong to other intents
    if _is_reschedule_query(lowered) or _is_cancel_query(lowered) or _is_existing_appointment_query(lowered):
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


def _is_clinic_hours_query(text: str) -> bool:
    """True if user asks general clinic hours/timing rather than their personal appointment time."""
    import re
    lowered = text.casefold()
    if any(p in lowered for p in ("mera", "meri", "mujhe", "my", "appointment", "appoinment", "token", "tkn")):
        return False
    if re.search(r"\b(clinic|hospital|dispensary)\b.*\b(timing|timings|time|hours|samay|open|opening|close|closing|khul|band)\b", lowered):
        return True
    if any(w in lowered for w in ("clinic timing", "clinic timings", "hospital timing", "hospital timings", "kab khulta", "kab band", "opening time", "closing time", "clinic time", "hospital time", "clinic hours")):
        return True
    return False


def _is_existing_appointment_query(text: str) -> bool:
    """True if patient is asking about their already booked appointment or arrival timing."""
    import re
    lowered = text.casefold()

    # Rule out reschedule or cancel intents
    if _is_reschedule_query(lowered) or _is_cancel_query(lowered):
        return False
    if _is_clinic_hours_query(text):
        return False

    # 1. Arrival timing queries ("kitne bje aana hai mujhe ?", "kab aana hai", "time kya hai")
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

    # 2. Already booked / past tense booking statements
    # e.g., "maine appoinment book kia hai dr sufian se", "mai book kr chuka hu", "already booked"
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
    if _is_clinic_hours_query(text):
        return False
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
    - "kon kon se dr hai"
    - "kaun se doctor hain"
    """
    import re
    has_list_trigger = any(
        phrase in text for phrase in (
            "which doctor", "which dr", "available doctor", "list doctor",
            "list of doctor", "show doctor", "show me the doctor",
            "show me doctor", "who are the doctor", "who are your doctor",
            "what doctor", "any doctor", "which specialist", "which physician",
            "doctor list", "all doctor", "tell me your doctor",
            "doctor ki list", "doctors ki list", "list dikhao", "list batao",
            "doctors list", "doctor dikhao", "doctors dikhao",
            "kon kon se dr", "kon se dr", "kaun se doctor", "kaun kaun se doctor",
            "kaun se dr", "kaun kaun se dr", "kaun doctor", "kaun dr",
            "konsa dr", "konsa doctor", "koun se dr", "koun se doctor",
            "doctor batao", "doctors batao", "dr batao", "dr btao", "doctor btao",
            "doctors btao", "kon doctor", "kon dr", "kise dikhaye", "kis doctor",
        )
    )
    if has_list_trigger:
        return True

    if re.search(r"\b(kon|kaun|koun|konsa|which)\b.*\b(dr|doctor|specialist|physician)\b", text):
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

