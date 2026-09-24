"""Routing helpers for the conversational graph."""


def should_retrieve(state: dict) -> str:
    text = state.get("user_text", "").lower()
    clinic_terms = ("clinic", "doctor", "service", "test", "price", "hours", "report", "address")
    return "retrieve" if any(term in text for term in clinic_terms) else "answer"