"""In-process conversation sessions for the temporary Sheets-backed flow."""

from threading import RLock


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[int, dict] = {}
        self._lock = RLock()

    def get(self, chat_id: int) -> dict:
        with self._lock:
            return dict(self._sessions.get(chat_id, {"chat_id": chat_id}))

    def save(self, chat_id: int, state: dict) -> None:
        with self._lock:
            self._sessions[chat_id] = dict(state)