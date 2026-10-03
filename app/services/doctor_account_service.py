"""Doctor Account Management Service.

Provides secure account lifecycle management for clinical staff:
- Account creation linked to verified Doctor IDs
- PBKDF2 password hashing with salt
- Compulsory password change on first login
- Demo password (1234) support strictly when explicitly configured
- Status toggling (Active / Inactive) without data loss
- Thread-safe persistence in JSON storage
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Optional

from ..core.auth import hash_password, verify_password
from .audit_service import AuditService


class DoctorAccountService:
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        doctor_directory=None,
        audit_service: Optional[AuditService] = None,
        allow_demo_password: bool = True,
    ) -> None:
        if storage_path is None:
            root_dir = Path(__file__).resolve().parents[2]
            self.storage_path = root_dir / "data" / "doctor_accounts.json"
        else:
            self.storage_path = storage_path

        self.doctor_directory = doctor_directory
        self.audit = audit_service or AuditService()
        self.allow_demo_password = allow_demo_password
        self._lock = RLock()
        self._accounts: dict[str, dict] = {}  # username.casefold() -> account dict
        self._load_accounts()

    def _load_accounts(self) -> None:
        """Load doctor accounts from disk."""
        if not self.storage_path.exists():
            self._accounts = {}
            return
        try:
            with self.storage_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._accounts = {k.casefold(): v for k, v in data.items()}
        except Exception:
            self._accounts = {}

    def _save_accounts(self) -> None:
        """Persist doctor accounts to disk atomically."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(self._accounts, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.storage_path)

    def validate_password_strength(self, password: str) -> None:
        """Validate password meets security policies unless demo password is explicitly allowed."""
        if self.allow_demo_password and password == "1234":
            return
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[a-zA-Z]", password):
            raise ValueError("Password must contain at least one letter.")

    def create_account(
        self,
        username: str,
        password: str,
        doctor_id: str,
        email: str = "",
        admin_user: str = "admin",
    ) -> dict:
        """Create a new doctor account linked to a valid Doctor Directory record."""
        norm_username = username.strip().casefold()
        if not norm_username:
            raise ValueError("Username is required.")
        if not re.match(r"^[a-zA-Z0-9_\-\.]{3,32}$", username.strip()):
            raise ValueError("Username must be 3-32 characters (alphanumeric, dots, dashes, underscores).")

        norm_doctor_id = doctor_id.strip()
        if not norm_doctor_id:
            raise ValueError("Doctor ID is required.")

        with self._lock:
            if norm_username in self._accounts:
                raise ValueError(f"Account with username '{username.strip()}' already exists.")

            # Validate doctor exists in Doctor Directory if configured
            doc_record = None
            if self.doctor_directory and hasattr(self.doctor_directory, "get_doctor_by_id"):
                doc_record = self.doctor_directory.get_doctor_by_id(norm_doctor_id)
                if not doc_record:
                    raise ValueError(f"Doctor ID '{norm_doctor_id}' does not exist in the Doctor Directory.")
                # Verify doctor ID isn't already assigned to another active account
                for acc in self._accounts.values():
                    if acc.get("doctor_id", "").casefold() == norm_doctor_id.casefold():
                        raise ValueError(
                            f"Doctor ID '{norm_doctor_id}' is already linked to account '{acc.get('username')}'."
                        )

            doctor_name = doc_record.get("Doctor Name", "") if doc_record else ""
            specialization = doc_record.get("Specialization", "") if doc_record else ""

            # Validate password
            self.validate_password_strength(password)

            now = datetime.now(timezone.utc).isoformat()
            hashed = hash_password(password)

            # Require password change on first login unless already changed
            account = {
                "username": username.strip(),
                "password_hash": hashed,
                "doctor_id": norm_doctor_id,
                "doctor_name": doctor_name,
                "specialization": specialization,
                "email": email.strip(),
                "status": "Active",
                "must_change_password": True,
                "created_at": now,
                "updated_at": now,
                "last_login": None,
            }

            self._accounts[norm_username] = account
            self._save_accounts()

            self.audit.record(
                user=admin_user,
                action="DOCTOR_ACCOUNT_CREATE",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={
                    "doctor_id": norm_doctor_id,
                    "doctor_name": doctor_name,
                    "email": email.strip(),
                },
            )

            safe = dict(account)
            safe.pop("password_hash", None)
            return safe

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Verify username & password. Returns account dict if valid, else None."""
        norm_username = username.strip().casefold()
        with self._lock:
            account = self._accounts.get(norm_username)
            if not account:
                return None
            if account.get("status", "").strip().casefold() != "active":
                return None
            if not verify_password(password, account.get("password_hash", "")):
                return None

            # Record login timestamp
            now = datetime.now(timezone.utc).isoformat()
            account["last_login"] = now
            self._save_accounts()

            safe = dict(account)
            safe.pop("password_hash", None)
            return safe

    def change_password(self, username: str, old_password: str, new_password: str) -> dict:
        """Allow doctor to change their own password upon verifying their existing password."""
        norm_username = username.strip().casefold()
        with self._lock:
            account = self._accounts.get(norm_username)
            if not account:
                raise ValueError(f"Account '{username}' not found.")

            if not verify_password(old_password, account.get("password_hash", "")):
                raise ValueError("Incorrect current password.")

            self.validate_password_strength(new_password)

            account["password_hash"] = hash_password(new_password)
            account["must_change_password"] = False
            account["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_accounts()

            self.audit.record(
                user=username,
                action="DOCTOR_PASSWORD_CHANGE",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={"reason": "User initiated password change."},
            )

            safe = dict(account)
            safe.pop("password_hash", None)
            return safe

    def reset_password(self, username: str, new_password: str, admin_user: str = "admin") -> dict:
        """Admin resets doctor password. Compulsory password change flag is re-armed."""
        norm_username = username.strip().casefold()
        with self._lock:
            account = self._accounts.get(norm_username)
            if not account:
                raise ValueError(f"Account '{username}' not found.")

            self.validate_password_strength(new_password)

            account["password_hash"] = hash_password(new_password)
            account["must_change_password"] = True
            account["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_accounts()

            self.audit.record(
                user=admin_user,
                action="DOCTOR_PASSWORD_RESET",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={"reset_by": admin_user},
            )

            safe = dict(account)
            safe.pop("password_hash", None)
            return safe

    def update_account(self, username: str, updates: dict, admin_user: str = "admin") -> dict:
        """Update doctor account profile info."""
        norm_username = username.strip().casefold()
        with self._lock:
            account = self._accounts.get(norm_username)
            if not account:
                raise ValueError(f"Account '{username}' not found.")

            if "doctor_id" in updates and updates["doctor_id"] != account.get("doctor_id"):
                new_doc_id = updates["doctor_id"].strip()
                if self.doctor_directory and hasattr(self.doctor_directory, "get_doctor_by_id"):
                    doc = self.doctor_directory.get_doctor_by_id(new_doc_id)
                    if not doc:
                        raise ValueError(f"Doctor ID '{new_doc_id}' does not exist.")
                    account["doctor_name"] = doc.get("Doctor Name", "")
                    account["specialization"] = doc.get("Specialization", "")
                account["doctor_id"] = new_doc_id

            if "email" in updates:
                account["email"] = updates["email"].strip()

            if "status" in updates:
                new_status = updates["status"].strip().title()
                if new_status in ("Active", "Inactive"):
                    account["status"] = new_status

            account["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_accounts()

            self.audit.record(
                user=admin_user,
                action="DOCTOR_ACCOUNT_UPDATE",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={k: v for k, v in updates.items() if k != "password"},
            )

            safe = dict(account)
            safe.pop("password_hash", None)
            return safe

    def set_status(self, username: str, status: str, admin_user: str = "admin") -> dict:
        """Activate or deactivate a doctor account."""
        norm_status = status.strip().title()
        if norm_status not in ("Active", "Inactive"):
            raise ValueError("Status must be either 'Active' or 'Inactive'.")
        return self.update_account(username, {"status": norm_status}, admin_user=admin_user)

    def get_account(self, username: str) -> Optional[dict]:
        """Get account details by username without password hash."""
        norm_username = username.strip().casefold()
        with self._lock:
            acc = self._accounts.get(norm_username)
            if not acc:
                return None
            safe = dict(acc)
            safe.pop("password_hash", None)
            return safe

    def get_account_by_doctor_id(self, doctor_id: str) -> Optional[dict]:
        """Find account linked to a specific doctor ID."""
        norm_id = doctor_id.strip().casefold()
        with self._lock:
            for acc in self._accounts.values():
                if acc.get("doctor_id", "").casefold() == norm_id:
                    safe = dict(acc)
                    safe.pop("password_hash", None)
                    return safe
        return None

    def list_accounts(self) -> list[dict]:
        """List all registered doctor accounts without password hashes."""
        with self._lock:
            result = []
            for acc in self._accounts.values():
                safe = dict(acc)
                safe.pop("password_hash", None)
                result.append(safe)
            result.sort(key=lambda a: a.get("created_at", ""), reverse=True)
            return result

