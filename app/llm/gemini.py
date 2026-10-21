"""Gemini adapter with model fallback and resilient interface."""

import logging
from typing import Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# Fallback sequence of modern, stable Gemini models
DEFAULT_MODEL_FALLBACKS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]


def extract_text_from_content(content: Any) -> str:
    """Safely extract plain text from string or structured content parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            elif hasattr(part, "text"):
                parts.append(str(part.text))
        return "".join(parts)
    return str(content) if content is not None else ""


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
        self._api_key = api_key
        # Default to high-quota flash-lite if no model specified or old 1.5 specified
        requested = (model or "").strip()
        if not requested or requested in ("gemini-1.5-flash", "gemini-2.0-flash"):
            requested = "gemini-flash-lite-latest"
        self._model_name = requested
        self._model = self._create_model(self._model_name)

    def _create_model(self, model_name: str) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self._api_key,
            temperature=0,
            max_retries=1,
            request_timeout=15.0,
        )

    def _invoke_with_fallback(self, messages: list) -> str:
        candidates = [self._model_name] + [m for m in DEFAULT_MODEL_FALLBACKS if m != self._model_name]
        last_error = None

        for candidate in candidates:
            try:
                if candidate != self._model_name:
                    logger.info("[GEMINI CLIENT] Attempting candidate model: %s", candidate)
                    model_instance = self._create_model(candidate)
                else:
                    model_instance = self._model

                response = model_instance.invoke(messages)
                text = extract_text_from_content(getattr(response, "content", response))

                # Cache the successfully responding model
                if candidate != self._model_name:
                    logger.info("[GEMINI CLIENT] Switched active model to: %s", candidate)
                    self._model_name = candidate
                    self._model = model_instance

                return text
            except Exception as exc:
                err_str = str(exc).lower()
                is_recoverable = (
                    "429" in err_str
                    or "resource_exhausted" in err_str
                    or "quota" in err_str
                    or "503" in err_str
                    or "unavailable" in err_str
                    or "high demand" in err_str
                    or "not_found" in err_str
                    or "404" in err_str
                )
                logger.warning(
                    "[GEMINI CLIENT] Model %s failed (recoverable=%s): %s",
                    candidate,
                    is_recoverable,
                    exc,
                )
                last_error = exc
                if not is_recoverable:
                    # Non-quota/non-availability error (e.g. invalid API key format), re-raise immediately
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("No candidate Gemini model succeeded.")

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
        return self._invoke_with_fallback(messages)
