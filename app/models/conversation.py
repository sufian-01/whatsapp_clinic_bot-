"""Transport-neutral conversation models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IncomingMessage:
    chat_id: int
    text: str
    user_id: int | None = None


@dataclass(frozen=True)
class ConversationReply:
    text: str