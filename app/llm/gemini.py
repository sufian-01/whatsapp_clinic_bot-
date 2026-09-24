"""Gemini adapter with a small interface for testing and future providers."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
        self._model = ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0)

    def answer(self, system_prompt: str, user_text: str, context: list[str]) -> str:
        context_text = "\n\n".join(context) or "No clinic-specific context was found."
        response = self._model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Clinic context:\n{context_text}\n\nUser: {user_text}"),
        ])
        return str(response.content)