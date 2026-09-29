"""Routing helpers for the conversational graph."""

from ..tools.doctors import match_health_concern

# Specialization terms that can appear in a doctor-list query
_SPECIALIZATION_TERMS = (
    "cardiologist", "cardiology", "gynecologist", "gynecology",
    "physician", "specialist", "orthopedic", "orthopedics",
    "dermatologist", "dermatology", "pediatrician", "pediatrics",
    "neurologist", "neurology", "psychiatrist", "psychiatry",
    "oncologist", "oncology", "ent", "ophthalmologist", "ophthalmology",
)


def classify_intent(state: dict) -> dict:
    if state.get("appointment_step"):
        return {**state, "intent": "appointment_flow"}

    text = state.get("user_text", "").lower()

    if any(term in text for term in ("human", "person", "support", "contact someone", "talk to someone")):
        intent = "human_support"
    elif any(term in text for term in ("report", "test result", "lab result")):
        intent = "report_enquiry"
    elif _is_doctor_list_query(text) or match_health_concern(text)[0] is not None:
        # Route doctor listing and health concern queries deterministically
        intent = "doctor_list"
    elif any(term in text for term in ("book", "appointment", "schedule", "consult")):
        intent = "appointment_booking"
    elif any(term in text for term in ("doctor", "doctors", "dr.", "physician", "gynecologist", "specialist")):
        intent = "doctor_information"
    elif any(term in text for term in ("clinic", "service", "test", "price", "hours", "timing", "address", "where")):
        intent = "clinic_information"
    else:
        intent = "other_help"

    return {**state, "intent": intent}


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
        )
    )
    if has_list_trigger:
        return True

    # "which <specialization> is available?" or "which <specialization> do you have?"
    has_which = any(w in text for w in ("which", "what", "any", "who"))
    has_spec = any(spec in text for spec in _SPECIALIZATION_TERMS)
    has_available = any(w in text for w in ("available", "have", "consult", "see", "visit"))

    if (has_which and has_spec) or (has_spec and has_available):
        return True

    # "available doctors/dr today?" pattern
    has_doctor_term = any(term in text for term in ("doctor", "dr", "physician", "specialist"))
    if has_doctor_term and "available" in text:
        return True

    return False


def route_intent(state: dict) -> str:
    return state.get("intent", "other_help")