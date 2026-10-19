"""Outbound Meta WhatsApp Cloud API Client.

Handles:
- Text messages
- Interactive button messages (up to 3 action buttons)
- Interactive list messages
- Approved notification templates
- Document and media attachments
- Exponential backoff retries and rate limiting
- Safe logging (credentials strictly redacted)
"""

import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


def normalize_phone_number(phone: str, default_country_code: str = "91") -> str:
    """Normalize phone number to international E.164-compatible digits without plus."""
    digits = re.sub(r"\D", "", str(phone or ""))
    if not digits:
        return ""
    # If 10 digits (standard Indian mobile), prepend default country code
    if len(digits) == 10 and default_country_code:
        return f"{default_country_code}{digits}"
    return digits


class MetaWhatsAppClient:
    """Production client for Meta WhatsApp Cloud API."""

    def __init__(
        self,
        access_token: str = "",
        api_version: str = "v21.0",
        phone_number_id: str = "",
        default_country_code: str = "91",
        timeout: float = 15.0,
        max_retries: int = 3,
        http_client: Optional[httpx.Client] = None,
    ):
        self.access_token = access_token.strip()
        self.api_version = api_version.strip() or "v21.0"
        self.phone_number_id = phone_number_id.strip()
        self.default_country_code = default_country_code
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = http_client or httpx.Client(timeout=timeout)

    def is_configured(self) -> bool:
        """Return True if credentials and phone number ID are present."""
        return bool(self.access_token and self.phone_number_id)

    def _get_url(self, phone_id: Optional[str] = None) -> str:
        pid = (phone_id or self.phone_number_id).strip()
        return f"https://graph.facebook.com/{self.api_version}/{pid}/messages"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _post_with_retry(self, payload: Dict[str, Any], phone_id: Optional[str] = None) -> Dict[str, Any]:
        """Post payload to Meta Graph API with exponential backoff on transient errors."""
        url = self._get_url(phone_id)
        headers = self._get_headers()

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        "WhatsApp message sent successfully: to=%s, message_id=%s",
                        payload.get("to"),
                        data.get("messages", [{}])[0].get("id"),
                    )
                    return {
                        "success": True,
                        "status_code": 200,
                        "data": data,
                        "raw_response": response.text,
                        "error": None,
                    }

                # Handle rate limiting or server errors
                if response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    sleep_sec = 0.5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Meta API transient error (HTTP %s). Retrying in %.1fs (attempt %d/%d)",
                        response.status_code, sleep_sec, attempt, self.max_retries
                    )
                    time.sleep(sleep_sec)
                    continue

                # Permanent failure
                err_detail = response.text
                try:
                    err_json = response.json()
                    err_detail = err_json.get("error", {}).get("message", response.text)
                except Exception:
                    pass
                logger.error("Meta API error (HTTP %s): %s", response.status_code, err_detail)
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "data": None,
                    "raw_response": response.text,
                    "error": err_detail,
                }

            except httpx.RequestError as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue

        return {
            "success": False,
            "status_code": 0,
            "data": None,
            "raw_response": last_error or "Network request failed after retries.",
            "error": last_error or "Network request failed after retries.",
        }

    def send_text(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
        phone_number_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a standard text message."""
        recipient = normalize_phone_number(to, self.default_country_code)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }
        return self._post_with_retry(payload, phone_number_id)

    def send_interactive_buttons(
        self,
        to: str,
        body: str,
        buttons: List[Dict[str, str]],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send interactive reply buttons (Meta supports maximum 3 buttons)."""
        recipient = normalize_phone_number(to, self.default_country_code)
        action_buttons = []
        for b in buttons[:3]:  # Meta limitation
            action_buttons.append({
                "type": "reply",
                "reply": {
                    "id": b.get("id", "")[:256],
                    "title": b.get("title", "")[:20],  # Meta max 20 chars
                },
            })

        interactive: Dict[str, Any] = {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": action_buttons},
        }
        if header:
            interactive["header"] = {"type": "text", "text": header[:60]}
        if footer:
            interactive["footer"] = {"text": footer[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": interactive,
        }
        return self._post_with_retry(payload, phone_number_id)

    def send_interactive_list(
        self,
        to: str,
        body: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive list message."""
        recipient = normalize_phone_number(to, self.default_country_code)
        interactive: Dict[str, Any] = {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_text[:20],
                "sections": sections,
            },
        }
        if header:
            interactive["header"] = {"type": "text", "text": header[:60]}
        if footer:
            interactive["footer"] = {"text": footer[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": interactive,
        }
        return self._post_with_retry(payload, phone_number_id)

    def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None,
        phone_number_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a pre-approved template message."""
        recipient = normalize_phone_number(to, self.default_country_code)
        template_obj: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template_obj["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": template_obj,
        }
        return self._post_with_retry(payload, phone_number_id)

    def send_document(
        self,
        to: str,
        document_url: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        media_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send PDF or document attachment via URL link or uploaded media ID."""
        recipient = normalize_phone_number(to, self.default_country_code)
        doc_obj: Dict[str, Any] = {}
        if media_id:
            doc_obj["id"] = media_id.strip()
        elif document_url:
            doc_obj["link"] = document_url.strip()
        else:
            doc_obj["link"] = ""

        if caption:
            doc_obj["caption"] = caption
        if filename:
            doc_obj["filename"] = filename

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "document",
            "document": doc_obj,
        }
        return self._post_with_retry(payload, phone_number_id)

    def mark_as_read(
        self,
        message_id: str,
        phone_number_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark incoming message as read."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return self._post_with_retry(payload, phone_number_id)

    def download_media(self, media_id: str) -> Optional[bytes]:
        """Download raw binary media content (e.g. voice/audio notes) from Meta Cloud API."""
        if not self.access_token or not media_id:
            return None
        meta_url = f"https://graph.facebook.com/{self.api_version}/{media_id.strip()}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            # 1. Query Meta Graph API for media download URL
            res = self._client.get(meta_url, headers=headers)
            if res.status_code != 200:
                logger.error("Failed to query Meta media metadata (HTTP %s): %s", res.status_code, res.text)
                return None
            media_info = res.json()
            download_url = media_info.get("url")
            if not download_url:
                logger.error("Meta media info did not contain 'url': %s", media_info)
                return None

            # 2. Download the binary media content using Bearer auth
            dl_res = self._client.get(download_url, headers=headers)
            if dl_res.status_code != 200:
                logger.error("Failed to download media content from Meta CDN (HTTP %s)", dl_res.status_code)
                return None
            return dl_res.content
        except Exception:
            logger.exception("Exception downloading WhatsApp media %s", media_id)
            return None

    def upload_media(
        self,
        media_bytes: bytes,
        mime_type: str = "audio/ogg",
        filename: str = "voice_reply.ogg",
        phone_number_id: Optional[str] = None,
    ) -> Optional[str]:
        """Upload media bytes to Meta WhatsApp Cloud API and return the media ID."""
        if not self.access_token or not media_bytes:
            return None
        pid = (phone_number_id or self.phone_number_id).strip()
        url = f"https://graph.facebook.com/{self.api_version}/{pid}/media"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {"messaging_product": "whatsapp"}
        files = {"file": (filename, media_bytes, mime_type)}
        try:
            res = self._client.post(url, headers=headers, data=data, files=files)
            if res.status_code == 200:
                media_id = res.json().get("id")
                logger.info("WhatsApp media uploaded successfully: id=%s", media_id)
                return media_id
            logger.error("Meta media upload failed (HTTP %s): %s", res.status_code, res.text)
            return None
        except Exception:
            logger.exception("Exception uploading WhatsApp media")
            return None

    def send_audio(
        self,
        to: str,
        media_id: str,
        phone_number_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an audio/voice note message by media ID."""
        recipient = normalize_phone_number(to, self.default_country_code)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "audio",
            "audio": {
                "id": media_id,
            },
        }
        return self._post_with_retry(payload, phone_number_id)

    def verify_phone_number(self, phone_number_id: Optional[str] = None) -> Dict[str, Any]:
        """Query Meta Graph API to verify WhatsApp phone number connection & health status."""
        pid = (phone_number_id or self.phone_number_id).strip()
        if not self.access_token:
            return {
                "success": False,
                "status_code": 0,
                "data": None,
                "error": "WhatsApp Access Token is not configured in platform settings.",
            }
        if not pid:
            return {
                "success": False,
                "status_code": 0,
                "data": None,
                "error": "WhatsApp Phone Number ID is missing or empty.",
            }
        url = f"https://graph.facebook.com/{self.api_version}/{pid}"
        headers = self._get_headers()
        try:
            res = self._client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                return {
                    "success": True,
                    "status_code": 200,
                    "data": {
                        "verified_name": data.get("verified_name") or data.get("name") or "Verified WhatsApp Business Account",
                        "display_phone_number": data.get("display_phone_number") or "",
                        "quality_rating": data.get("quality_rating") or "UNKNOWN",
                        "code_verification_status": data.get("code_verification_status") or "VERIFIED",
                        "id": data.get("id") or pid,
                    },
                    "error": None,
                }
            err_msg = res.text
            try:
                err_data = res.json()
                err_msg = err_data.get("error", {}).get("message", res.text)
            except Exception:
                pass
            return {
                "success": False,
                "status_code": res.status_code,
                "data": None,
                "error": f"Meta Graph API Error ({res.status_code}): {err_msg}",
            }
        except Exception as exc:
            return {
                "success": False,
                "status_code": 0,
                "data": None,
                "error": f"Network connection error: {str(exc)}",
            }

