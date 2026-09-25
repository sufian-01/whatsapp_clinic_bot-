"""Routing helpers for the conversational graph."""


def classify_intent(state: dict) -> dict:
    if state.get("appointment_step"):
        return {**state, "intent": "appointment_flow"}
    text = state.get("user_text", "").lower()
    if any(term in text for term in ("human", "person", "support", "contact someone", "talk to someone")):
        intent = "human_support"
    elif any(term in text for term in ("report", "test result", "lab result")):
        intent = "report_enquiry"
    elif any(term in text for term in ("book", "appointment", "schedule", "consult")):
        intent = "appointment_booking"
    elif any(term in text for term in ("doctor", "doctors", "dr.", "physician", "gynecologist", "specialist")):
        intent = "doctor_information"
    elif any(term in text for term in ("clinic", "service", "test", "price", "hours", "timing", "address", "where")):
        intent = "clinic_information"
    else:
        intent = "other_help"
    return {**state, "intent": intent}


def route_intent(state: dict) -> str:
    return state.get("intent", "other_help")