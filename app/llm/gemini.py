"""Gemini adapter with a small interface for testing and future providers."""

from typing import Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
        target_model = model or "gemini-2.5-flash"
        if target_model in ("gemini-2.0-flash", "gemini-1.5-flash"):
            target_model = "gemini-2.5-flash"
        self._api_key = api_key
        self._model_name = target_model
        self._model = ChatGoogleGenerativeAI(model=self._model_name, google_api_key=api_key, temperature=0)

    def answer(
        self,
        system_prompt: str,
        user_text: str,
        context: list[str],
        history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        context_text = "\n\n".join(context) or "No clinic-specific context was found."
        messages = [
            SystemMessage(content=f"{system_prompt}\n\nClinic context:\n{context_text}"),
        ]
        if history:
            for turn in history[-6:]:
                role = (turn.get("role") or "").strip().lower()
                content = turn.get("content") or ""
                if not content:
                    continue
                if role in ("assistant", "bot", "model"):
                    messages.append(AIMessage(content=content))
                elif role in ("user", "human"):
                    messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=user_text))

        try:
            response = self._model.invoke(messages)
            return str(response.content)
        except Exception as e:
            if "NOT_FOUND" in str(e) and self._model_name != "gemini-2.5-flash":
                self._model_name = "gemini-2.5-flash"
                self._model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=self._api_key, temperature=0)
                response = self._model.invoke(messages)
                return str(response.content)
            raise
