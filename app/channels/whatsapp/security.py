"""Security utilities for Meta WhatsApp Cloud API webhooks."""

import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_meta_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    app_secret: str,
) -> bool:
    """Verify X-Hub-Signature-256 header against raw request body using HMAC-SHA256."""
    if not app_secret:
        # If no secret configured, reject for security
        logger.warning("WhatsApp app secret is not configured; rejecting signed webhook.")
        return False

    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header on WhatsApp webhook.")
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        logger.warning("Malformed X-Hub-Signature-256 header format: %s", signature_header)
        return False

    expected_hash = signature_header[len(prefix):].strip().casefold()

    # Compute expected signature
    mac = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    )
    computed_hash = mac.hexdigest().casefold()

    is_valid = hmac.compare_digest(computed_hash, expected_hash)
    if not is_valid:
        logger.warning("Invalid WhatsApp webhook signature verification.")
    return is_valid


def verify_webhook_challenge(
    mode: Optional[str],
    token: Optional[str],
    challenge: Optional[str],
    expected_token: str,
) -> Optional[str]:
    """Validate Meta webhook subscription challenge handshake."""
    if not mode or not token or not challenge:
        return None

    if mode == "subscribe" and expected_token and hmac.compare_digest(token, expected_token):
        return challenge
    return None

