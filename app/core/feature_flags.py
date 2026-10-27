"""Subscription Plans, Feature Flags, and Dynamic Tenant Capability Resolution.

Controls which AI agent and platform features are enabled per clinic facility:
- Pre-defined subscription tiers: STARTER, PROFESSIONAL, ENTERPRISE
- Granular per-feature toggle overrides
- Graceful, patient-friendly fallback messages when features are disabled
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Canonical Feature Keys
FEATURE_VOICE_INBOUND = "voice_inbound"          # Voice notes transcription (Sarvam STT)
FEATURE_VOICE_OUTBOUND = "voice_outbound"        # Voice note spoken replies (Sarvam TTS)
FEATURE_INTERACTIVE_LISTS = "interactive_lists"  # WhatsApp interactive list & button menus
FEATURE_ONLINE_PAYMENTS = "online_payments"      # Online payment link generation / QR
FEATURE_CANCELLATION = "cancellation"            # Patient self-cancellation via AI
FEATURE_RESCHEDULING = "rescheduling"            # Patient self-rescheduling via AI
FEATURE_RAG_KNOWLEDGE = "rag_knowledge"          # Clinic FAQ, guidelines & doctor RAG retrieval
FEATURE_REPORT_ENQUIRY = "report_enquiry"        # Diagnostic report lookup & enquiry
FEATURE_AI_AGENT = "ai_agent"                    # AI-First conversational intelligence (default: True) vs lightweight rule-based mode
FEATURE_BOOKING_GUARD_V2 = "booking_guard_v2"    # Hardened booking guards, attempts limit, loop breaker, idle recovery
FEATURE_SMART_INTENT_V2 = "smart_intent_v2"      # Step-aware regex fast-paths, context-rich Gemini intent classification

# Subscription Tier Defaults
SUBSCRIPTION_PLANS: Dict[str, Dict[str, bool]] = {
    "STARTER": {
        FEATURE_AI_AGENT: True,
        FEATURE_BOOKING_GUARD_V2: False,
        FEATURE_SMART_INTENT_V2: False,
        FEATURE_VOICE_INBOUND: False,
        FEATURE_VOICE_OUTBOUND: False,
        FEATURE_INTERACTIVE_LISTS: True,
        FEATURE_ONLINE_PAYMENTS: False,
        FEATURE_CANCELLATION: True,
        FEATURE_RESCHEDULING: True,
        FEATURE_RAG_KNOWLEDGE: True,
        FEATURE_REPORT_ENQUIRY: True,
    },
    "PROFESSIONAL": {
        FEATURE_AI_AGENT: True,
        FEATURE_VOICE_INBOUND: True,
        FEATURE_VOICE_OUTBOUND: False,
        FEATURE_INTERACTIVE_LISTS: True,
        FEATURE_ONLINE_PAYMENTS: True,
        FEATURE_CANCELLATION: True,
        FEATURE_RESCHEDULING: True,
        FEATURE_RAG_KNOWLEDGE: True,
        FEATURE_REPORT_ENQUIRY: True,
        FEATURE_BOOKING_GUARD_V2: False,
        FEATURE_SMART_INTENT_V2: False,
    },
    "ENTERPRISE": {
        FEATURE_AI_AGENT: True,
        FEATURE_VOICE_INBOUND: True,
        FEATURE_VOICE_OUTBOUND: True,
        FEATURE_INTERACTIVE_LISTS: True,
        FEATURE_ONLINE_PAYMENTS: True,
        FEATURE_CANCELLATION: True,
        FEATURE_RESCHEDULING: True,
        FEATURE_RAG_KNOWLEDGE: True,
        FEATURE_REPORT_ENQUIRY: True,
        FEATURE_BOOKING_GUARD_V2: False,
        FEATURE_SMART_INTENT_V2: False,
    },
}


def get_plan_default_flags(plan_name: str) -> Dict[str, bool]:
    """Return default capability set for a given subscription tier plan."""
    norm_plan = (plan_name or "STARTER").strip().upper()
    return dict(SUBSCRIPTION_PLANS.get(norm_plan, SUBSCRIPTION_PLANS["STARTER"]))


def parse_feature_flags_json(flags_val: Any) -> Dict[str, bool]:
    """Safely parse feature flags from JSON string, dict, or None."""
    if isinstance(flags_val, dict):
        return {str(k): bool(v) for k, v in flags_val.items()}
    if isinstance(flags_val, str) and flags_val.strip():
        try:
            parsed = json.loads(flags_val)
            if isinstance(parsed, dict):
                return {str(k): bool(v) for k, v in parsed.items()}
        except Exception:
            logger.warning("Failed to parse feature_flags JSON: %r", flags_val)
    return {}


def resolve_effective_feature_flags(
    plan_name: str = "STARTER",
    overrides: Optional[Any] = None,
) -> Dict[str, bool]:
    """Merge subscription plan defaults with clinic-level granular toggle overrides."""
    effective = get_plan_default_flags(plan_name)
    override_dict = parse_feature_flags_json(overrides)
    effective.update(override_dict)
    return effective


def is_feature_enabled(
    flags: Dict[str, bool],
    feature_name: str,
    default: bool = True,
) -> bool:
    """Return True if specific feature capability is currently enabled."""
    return bool(flags.get(feature_name, default))


def get_disabled_feature_message(
    feature_name: str,
    clinic_name: str = "our clinic",
    support_phone: str = "",
) -> str:
    """Generate professional, polite fallback message when a patient tries to use a disabled feature."""
    phone_info = f" at {support_phone}" if support_phone else ""

    if feature_name in (FEATURE_VOICE_INBOUND, FEATURE_VOICE_OUTBOUND):
        return (
            f"Voice messaging is currently not enabled for {clinic_name}. "
            "Please send your message or appointment request as a text message."
        )

    if feature_name == FEATURE_CANCELLATION:
        return (
            f"Online appointment cancellation is currently disabled for {clinic_name}. "
            f"Please contact our clinic reception{phone_info} directly to cancel or modify your booking."
        )

    if feature_name == FEATURE_RESCHEDULING:
        return (
            f"Online appointment rescheduling is currently disabled for {clinic_name}. "
            f"Please contact our clinic reception{phone_info} directly to adjust your appointment timing."
        )

    if feature_name == FEATURE_ONLINE_PAYMENTS:
        return (
            f"Online payment is currently not available for {clinic_name}. "
            "Please select 'Pay at Clinic' to complete your appointment and pay in person."
        )

    if feature_name == FEATURE_REPORT_ENQUIRY:
        return (
            f"Online report enquiries are currently not active for {clinic_name}. "
            f"Please visit the clinic reception or call{phone_info} to collect your test reports."
        )

    return (
        f"This service is currently not available online for {clinic_name}. "
        f"Please contact our clinic team{phone_info} for assistance."
    )
