"""Thread-safe in-process conversation session store.

Used by WhatsApp channel and LangGraph agent flows for multi-turn state retention.
"""

from threading import RLock
from typing import Any, Dict


class SessionStore:
    """Thread-safe session dictionary mapping session keys to state dicts."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    def get(self, chat_id: Any) -> Dict[str, Any]:
        """Fetch existing session or return a new baseline state with chat_id."""
        key = str(chat_id)
        with self._lock:
            return dict(self._sessions.get(key, {"chat_id": chat_id}))

    def save(self, chat_id: Any, state: Dict[str, Any]) -> None:
        """Atomically persist session state."""
        key = str(chat_id)
        with self._lock:
            self._sessions[key] = dict(state)

    def clear(self, chat_id: Any) -> None:
        """Remove a specific session."""
        key = str(chat_id)
        with self._lock:
            self._sessions.pop(key, None)

    def reset_all(self) -> None:
        """Clear all active sessions (e.g. for testing)."""
        with self._lock:
            self._sessions.clear()

