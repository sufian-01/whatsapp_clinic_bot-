"""State passed between graph nodes."""

from typing import TypedDict


class GraphState(TypedDict, total=False):
    chat_id: int
    user_text: str
    clinic_context: list[str]
    response: str