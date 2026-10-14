"""Meta WhatsApp Cloud API connectivity and message dispatch test tool.

Usage:
  # Check configuration & verify credentials against Meta Graph API
  python -m app.scripts.test_whatsapp_meta --mode check

  # Send default Meta test template (jaspers_market_order_confirmation_v1)
  python -m app.scripts.test_whatsapp_meta --mode template --to 919876543210

  # Send test text message
  python -m app.scripts.test_whatsapp_meta --mode text --to 919876543210 --message "Hello from Clinic Assistant!"
"""

import argparse
import json
import os
import sys
from typing import Optional

from dotenv import load_dotenv
import httpx

from ..channels.whatsapp.client import MetaWhatsAppClient, normalize_phone_number
from ..core.config import get_settings


def redact(val: Optional[str], show_last: int = 4) -> str:
    """Safely redact secret tokens."""
    if not val:
        return "<NOT SET>"
    s = str(val).strip()
    if len(s) <= show_last:
        return "***"
    return f"***...{s[-show_last:]}"


def check_meta_connectivity(
    access_token: str,
    phone_number_id: str,
    api_version: str = "v21.0",
) -> bool:
    """Verify Meta Cloud API credentials by inspecting phone number ID."""
    print("=" * 60)
    print("Verifying Meta WhatsApp Cloud API credentials...")
    print(f"API Version:     {api_version}")
    print(f"Phone Number ID: {phone_number_id or '<EMPTY>'}")
    print(f"Access Token:    {redact(access_token)}")
    print("=" * 60)

    if not access_token or not phone_number_id:
        print("[ERROR] WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID must both be set in .env")
        return False

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                print("[SUCCESS] Connected to Meta Graph API!")
                print(f"  Verified Name:       {data.get('verified_name', 'N/A')}")
                print(f"  Display Phone:       {data.get('display_phone_number', 'N/A')}")
                print(f"  Quality Rating:      {data.get('quality_rating', 'N/A')}")
                print(f"  Code Verification:   {data.get('code_verification_status', 'N/A')}")
                return True
            else:
                err_data = {}
                try:
                    err_data = resp.json().get("error", {})
                except Exception:
                    pass
                print(f"[FAIL] Meta Graph API returned HTTP {resp.status_code}")
                print(f"  Error Type:    {err_data.get('type', 'N/A')}")
                print(f"  Error Code:    {err_data.get('code', 'N/A')}")
                print(f"  Error Message: {err_data.get('message', resp.text)}")
                return False
    except Exception as exc:
        print(f"[ERROR] Network error connecting to Meta Graph API: {exc}")
        return False


def subscribe_waba_to_app(
    access_token: str,
    waba_id: str,
    api_version: str = "v21.0",
) -> bool:
    """Subscribe WhatsApp Business Account (WABA) to app so webhooks are delivered."""
    print("=" * 60)
    print("Subscribing WhatsApp Business Account (WABA) to App Webhook...")
    print(f"API Version:     {api_version}")
    print(f"WABA ID:         {waba_id or '<EMPTY>'}")
    print(f"Access Token:    {redact(access_token)}")
    print("=" * 60)

    if not access_token or not waba_id:
        print("[ERROR] WHATSAPP_ACCESS_TOKEN and WHATSAPP_BUSINESS_ACCOUNT_ID must both be set in .env")
        return False

    url = f"https://graph.facebook.com/{api_version}/{waba_id}/subscribed_apps"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                print("[SUCCESS] WhatsApp Business Account subscribed to App Webhook!")
                print(f"  Response: {data}")
                return True
            else:
                err_data = {}
                try:
                    err_data = resp.json().get("error", {})
                except Exception:
                    pass
                print(f"[FAIL] Meta Graph API returned HTTP {resp.status_code}")
                print(f"  Error Message: {err_data.get('message', resp.text)}")
                return False
    except Exception as exc:
        print(f"[ERROR] Network error subscribing WABA to app: {exc}")
        return False


def send_test_template(
    client: MetaWhatsAppClient,
    recipient: str,
    template_name: str,
    language_code: str,
) -> bool:
    """Send test template message."""
    print(f"Dispatching template '{template_name}' ({language_code}) to {recipient}...")
    result = client.send_template(
        to=recipient,
        template_name=template_name,
        language_code=language_code,
    )
    if result.get("success"):
        data = result.get("data", {})
        msg_id = data.get("messages", [{}])[0].get("id", "unknown")
        print("[SUCCESS] Template sent successfully!")
        print(f"  Meta Message ID: {msg_id}")
        return True
    else:
        print(f"[FAIL] Template dispatch failed: {result.get('error')}")
        if result.get("status_code"):
            print(f"  HTTP Status Code: {result.get('status_code')}")
        return False


def send_test_text(
    client: MetaWhatsAppClient,
    recipient: str,
    message: str,
) -> bool:
    """Send standard text message."""
    print(f"Dispatching text message to {recipient}...")
    result = client.send_text(to=recipient, text=message)
    if result.get("success"):
        data = result.get("data", {})
        msg_id = data.get("messages", [{}])[0].get("id", "unknown")
        print("[SUCCESS] Text message sent successfully!")
        print(f"  Meta Message ID: {msg_id}")
        return True
    else:
        print(f"[FAIL] Text dispatch failed: {result.get('error')}")
        if result.get("status_code"):
            print(f"  HTTP Status Code: {result.get('status_code')}")
        return False


def main():
    load_dotenv()
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Test Meta WhatsApp Cloud API integration.")
    parser.add_argument(
        "--mode",
        choices=["check", "template", "text", "subscribe"],
        default="check",
        help="Action to perform: check connectivity, send template, send text, or subscribe WABA to app",
    )
    parser.add_argument(
        "--to",
        type=str,
        default=os.getenv("WHATSAPP_TEST_RECIPIENT_PHONE", ""),
        help="Recipient phone number (e.g. 919876543210)",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=os.getenv("WHATSAPP_TEST_TEMPLATE_NAME", "jaspers_market_order_confirmation_v1"),
        help="Template name (default: jaspers_market_order_confirmation_v1)",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=os.getenv("WHATSAPP_TEST_TEMPLATE_LANGUAGE", "en_US"),
        help="Template language code (default: en_US)",
    )
    parser.add_argument(
        "--message",
        type=str,
        default="Hello! This is a test message from your Clinic WhatsApp Assistant.",
        help="Message content for text mode",
    )
    args = parser.parse_args()

    token = settings.whatsapp_access_token
    phone_id = settings.whatsapp_phone_number_id
    api_version = settings.whatsapp_api_version or "v21.0"

    if args.mode == "check":
        ok = check_meta_connectivity(token, phone_id, api_version)
        sys.exit(0 if ok else 1)
    elif args.mode == "subscribe":
        ok = subscribe_waba_to_app(token, settings.whatsapp_business_account_id, api_version)
        sys.exit(0 if ok else 1)

    recipient = normalize_phone_number(args.to, settings.whatsapp_default_country_code)
    if not recipient:
        print("[ERROR] Recipient phone number is required. Provide via --to <number> or WHATSAPP_TEST_RECIPIENT_PHONE.")
        sys.exit(1)

    client = MetaWhatsAppClient(
        access_token=token,
        api_version=api_version,
        phone_number_id=phone_id,
        default_country_code=settings.whatsapp_default_country_code,
    )

    if args.mode == "template":
        ok = send_test_template(client, recipient, args.template, args.lang)
        sys.exit(0 if ok else 1)
    elif args.mode == "text":
        ok = send_test_text(client, recipient, args.message)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

