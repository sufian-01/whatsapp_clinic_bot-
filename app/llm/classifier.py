"""AI-First Semantic Intent Classifier for Healthcare WhatsApp Conversations.

Leverages Gemini LLM to understand natural conversational language, Hinglish,
typos, sentiment, mid-flow disruptions, and negative intent.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

CLASSIFIER_SYSTEM_PROMPT = """You are an expert intent classifier for a multi-tenant healthcare clinic WhatsApp assistant.
The patient communicates in English, Hindi, or Hinglish (e.g. "pehle yeh btao kon kon se dr hai", "appoinment ki batt ni kr rha mei", "dr arjun ki fees kitni hai", "rehne do nahi chahiye").

You must determine the user's PRIMARY INTENT from these options:
- "appointment_draft_cancel": The user wants to cancel, abandon, reject, or exit the current in-progress booking flow (e.g. "cancel this appointment", "rehne do", "nahi chahiye", "appoinment ki batt ni kr rha mei", "stop", "chhod do", "mat karo", "mujhe nahi book karna", "baat nahi kar raha").
- "doctor_list": The user wants to see the list of available doctors, asks which doctors exist, or asks for a specialist / medical department (e.g. "kon kon se dr hai", "which doctors are available", "cardiologist se milna hai", "skin specialist", "eye doctor dikhao").
- "doctor_information": The user is asking specific factual info about a doctor such as fees, qualification, experience, or schedule (e.g. "dr arjun ki fees kitni hai", "doctor ka qualification kya hai").
- "clinic_information": The user is asking about clinic timings, location, address, facilities, parking, or contact (e.g. "clinic kab khulta hai", "kahan par hai", "address kya hai").
- "patient_appointments": The user is asking about their already booked upcoming appointment, token number, or reporting time (e.g. "mera koi appointment hai kya", "kab aana hai", "token kya hai").
- "appointment_booking": The user wants to start a new appointment booking (e.g. "book appointment", "new appointment", "doctor ko dikhana hai", "slot chahiye").
- "appointment_flow": The user is directly answering the currently asked question (e.g. providing their name when asked for name, email, phone number, choosing a date/slot, or confirming).
- "report_enquiry": The user is asking about diagnostic, blood test, or lab reports (e.g. "meri report kab aayegi", "test result").
- "appointment_cancel": The user wants to cancel an existing confirmed appointment in CRM.
- "appointment_reschedule": The user wants to change date/time of an existing confirmed appointment.
- "human_support": The user wants to talk to a human receptionist / staff.
- "greeting": A simple greeting with no question (e.g. "hi", "namaste", "hello").
- "other_help": Any other general question, query, or statement.

Respond ONLY with valid JSON in this exact structure:
{
  "intent": "<one of the intent names above>",
  "is_cancellation": <true if user wants to cancel/stop/reject current flow else false>,
  "is_side_question": <true if user asked an informational question during an active flow else false>,
  "specialization": "<specialization name like cardiology/gynecology or null>",
  "doctor_name": "<doctor name or null>"
}
"""


def _extract_json_payload(text: str) -> Optional[dict]:
    """Cleanly parse JSON from markdown code block or raw string."""
    if not text:
        return None
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    raw = match.group(1) if match else cleaned
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        # Try finding opening and closing braces
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except Exception:
                pass
    return None


def classify_with_ai(
    llm: Any,
    user_text: str,
    active_flow: Optional[str] = None,
    current_step: Optional[str] = None,
    history: Optional[list] = None,
) -> Optional[dict]:
    """Use Gemini LLM to classify user message intent with structured output.
    
    Returns parsed dictionary or None if LLM is unavailable or fails.
    """
    if not llm or not user_text:
        return None

    context = []
    if active_flow:
        context.append(f"Current active workflow: {active_flow}")
    if current_step:
        context.append(f"Pending step asked to patient: {current_step}")

    try:
        if hasattr(llm, "answer"):
            try:
                raw_response = llm.answer(
                    CLASSIFIER_SYSTEM_PROMPT,
                    user_text,
                    context,
                    history=history,
                )
            except TypeError:
                raw_response = llm.answer(CLASSIFIER_SYSTEM_PROMPT, user_text, context)
        elif hasattr(llm, "invoke"):
            from langchain_core.messages import HumanMessage, SystemMessage
            ctx_str = "\n".join(context) if context else "No active workflow."
            msgs = [
                SystemMessage(content=f"{CLASSIFIER_SYSTEM_PROMPT}\n\nState Context:\n{ctx_str}"),
                HumanMessage(content=user_text),
            ]
            resp = llm.invoke(msgs)
            raw_response = getattr(resp, "content", resp)
        else:
            return None

        from .gemini import extract_text_from_content
        text_payload = extract_text_from_content(raw_response)
        data = _extract_json_payload(text_payload)
        if isinstance(data, dict) and data.get("intent"):
            logger.info(
                "[AI INTENT CLASSIFIER] Text=%r -> Intent=%s (cancel=%s, side_q=%s, spec=%s)",
                user_text,
                data.get("intent"),
                data.get("is_cancellation"),
                data.get("is_side_question"),
                data.get("specialization"),
            )
            return data
        return None
    except Exception as exc:
        logger.warning("[AI INTENT CLASSIFIER] Failed to classify via LLM (%s), using rule fallback.", exc)
        return None

