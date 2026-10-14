"""Pydantic data schemas for Meta WhatsApp Cloud API webhooks and payloads."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WhatsAppMetadata(BaseModel):
    display_phone_number: Optional[str] = None
    phone_number_id: Optional[str] = ""


class WhatsAppProfile(BaseModel):
    name: Optional[str] = "Patient"


class WhatsAppContact(BaseModel):
    profile: Optional[WhatsAppProfile] = Field(default_factory=WhatsAppProfile)
    wa_id: Optional[str] = None


class WhatsAppText(BaseModel):
    body: str


class WhatsAppButtonReply(BaseModel):
    id: str
    title: str


class WhatsAppListReply(BaseModel):
    id: str
    title: str
    description: Optional[str] = None


class WhatsAppInteractive(BaseModel):
    type: str  # button_reply, list_reply
    button_reply: Optional[WhatsAppButtonReply] = None
    list_reply: Optional[WhatsAppListReply] = None


class WhatsAppMedia(BaseModel):
    id: Optional[str] = None
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    caption: Optional[str] = None


class WhatsAppLocation(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


class WhatsAppMessage(BaseModel):
    id: Optional[str] = None
    from_: str = Field(..., alias="from")
    timestamp: Optional[str] = None
    type: str = "text"  # text, interactive, image, document, audio, video, location, button, etc.
    text: Optional[WhatsAppText] = None
    interactive: Optional[WhatsAppInteractive] = None
    image: Optional[WhatsAppMedia] = None
    document: Optional[WhatsAppMedia] = None
    audio: Optional[WhatsAppMedia] = None
    voice: Optional[WhatsAppMedia] = None
    location: Optional[WhatsAppLocation] = None

    model_config = ConfigDict(populate_by_name=True)


class WhatsAppStatus(BaseModel):
    id: str
    status: str  # sent, delivered, read, failed
    timestamp: Optional[str] = None
    recipient_id: Optional[str] = None
    conversation: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None


class WhatsAppValue(BaseModel):
    messaging_product: Optional[str] = "whatsapp"
    metadata: Optional[WhatsAppMetadata] = None
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None
    statuses: Optional[List[WhatsAppStatus]] = None


class WhatsAppChange(BaseModel):
    value: Optional[WhatsAppValue] = None
    field: Optional[str] = "messages"


class WhatsAppEntry(BaseModel):
    id: Optional[str] = None
    changes: List[WhatsAppChange] = Field(default_factory=list)


class WhatsAppWebhookPayload(BaseModel):
    object: Optional[str] = "whatsapp_business_account"
    entry: List[WhatsAppEntry] = Field(default_factory=list)
