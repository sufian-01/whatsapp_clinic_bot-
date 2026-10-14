"""Immutable audit logging service for Clinic Management System (CMS).

Records all administrative actions, data modifications, and sensitive operations.
Persists log entries to an append-only JSONL file and maintains a queryable in-memory cache.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Optional
from uuid import uuid4


@dataclass(frozen=True)
class AuditEntry:
    id: str
    timestamp: str
    user: str
    action: str
    entity_type: str
    entity_id: str
    details: dict


class AuditService:
    def __init__(self, log_file: Optional[Path] = None, max_memory_entries: int = 2000, session_factory=None) -> None:
        self._pg = None
        if session_factory is not None:
            from ..repositories.postgres_crm_repositories import PostgresAuditService
            self._pg = PostgresAuditService(session_factory, max_memory_entries=max_memory_entries)
        elif log_file is None:
            from ..db.session import is_db_configured, get_session_factory
            if is_db_configured():
                try:
                    from ..repositories.postgres_crm_repositories import PostgresAuditService
                    self._pg = PostgresAuditService(get_session_factory(), max_memory_entries=max_memory_entries)
                except Exception:
                    self._pg = None

        if self._pg is not None:
            self.log_file = log_file or Path("data/audit_logs.jsonl")
            self.max_memory_entries = self._pg.max_memory_entries
            self._lock = self._pg._lock
            self._entries = self._pg._entries
            return

        if log_file is None:
            # Default to data/audit_logs.jsonl relative to project root
            root_dir = Path(__file__).resolve().parents[2]
            self.log_file = root_dir / "data" / "audit_logs.jsonl"
        else:
            self.log_file = log_file

        self.max_memory_entries = max_memory_entries
        self._lock = Lock()
        self._entries: list[dict] = []
        self._load_existing_logs()

    def _load_existing_logs(self) -> None:
        """Load recent entries from disk if log file exists."""
        if not self.log_file.exists():
            return
        try:
            entries = []
            with self.log_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            # Keep newest in memory
            self._entries = entries[-self.max_memory_entries:]
        except Exception:
            self._entries = []

    def record(
        self,
        user: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[dict] = None,
    ) -> dict:
        """Record an immutable audit log entry."""
        if self._pg is not None:
            return self._pg.record(user=user, action=action, entity_type=entity_type, entity_id=entity_id, details=details)
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "id": f"AUD-{uuid4().hex[:12].upper()}",
            "timestamp": now,
            "user": user or "system",
            "action": action.upper().strip(),
            "entity_type": entity_type.lower().strip(),
            "entity_id": str(entity_id).strip(),
            "details": details or {},
        }

        with self._lock:
            # Append to in-memory list
            self._entries.append(entry)
            if len(self._entries) > self.max_memory_entries:
                self._entries.pop(0)

            # Persist immediately to disk (append-only)
            try:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                with self.log_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass

        return entry

    def get_logs(
        self,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Query audit logs with filtering and pagination (newest first)."""
        if self._pg is not None:
            return self._pg.get_logs(action=action, entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset)
        with self._lock:
            records = list(self._entries)

        # Apply filters
        if action:
            q_act = action.strip().upper()
            records = [r for r in records if r["action"] == q_act]
        if entity_type:
            q_ent = entity_type.strip().lower()
            records = [r for r in records if r["entity_type"] == q_ent]
        if entity_id:
            q_id = entity_id.strip()
            records = [r for r in records if r["entity_id"] == q_id]

        # Reverse to show newest first
        records.reverse()

        total = len(records)
        start = offset
        end = offset + limit
        paginated = records[start:end]

        return {
            "logs": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
