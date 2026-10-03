"""Authentication and authorization utilities for Clinic CRM & Doctor Portal.

Provides secure password hashing (PBKDF2-HMAC-SHA256, 100k iterations),
cryptographic session token generation, session lifecycle tracking,
login rate limiting, account lockout protections, and FastAPI route protection dependencies.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import os
import secrets
from threading import Lock
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

# In-memory session store: token -> session dict
_ACTIVE_SESSIONS: dict[str, dict] = {}
_SESSIONS_LOCK = Lock()

# Rate limiting and lockout store: username_or_ip -> list of failure timestamps
_FAILED_ATTEMPTS: dict[str, list[float]] = {}
_LOCKED_KEYS: dict[str, float] = {}  # key -> unlock_timestamp
_LOCKOUT_LOCK = Lock()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutes
ATTEMPT_WINDOW_SECONDS = 15 * 60


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        algo_part, salt, key_hex = parts
        _, hash_name, iterations_str = algo_part.split(":")
        iterations = int(iterations_str)
        calculated_key = hashlib.pbkdf2_hmac(
            hash_name,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(calculated_key.hex(), key_hex)
    except Exception:
        return False


def check_account_lockout(key: str) -> tuple[bool, int]:
    """Check if an account or IP key is currently locked out.

    Returns:
        (is_locked, seconds_remaining)
    """
    now = datetime.now(timezone.utc).timestamp()
    with _LOCKOUT_LOCK:
        if key in _LOCKED_KEYS:
            unlock_time = _LOCKED_KEYS[key]
            if now < unlock_time:
                return True, int(unlock_time - now)
            # Expired lockout
            del _LOCKED_KEYS[key]
            _FAILED_ATTEMPTS.pop(key, None)
    return False, 0


def record_failed_login(key: str) -> tuple[bool, int]:
    """Record a failed login attempt and apply lockout if threshold is exceeded.

    Returns:
        (is_now_locked, attempts_left)
    """
    now = datetime.now(timezone.utc).timestamp()
    with _LOCKOUT_LOCK:
        attempts = _FAILED_ATTEMPTS.get(key, [])
        # Prune attempts outside window
        attempts = [t for t in attempts if now - t <= ATTEMPT_WINDOW_SECONDS]
        attempts.append(now)
        _FAILED_ATTEMPTS[key] = attempts

        if len(attempts) >= MAX_FAILED_ATTEMPTS:
            unlock_time = now + LOCKOUT_DURATION_SECONDS
            _LOCKED_KEYS[key] = unlock_time
            return True, 0
        attempts_left = MAX_FAILED_ATTEMPTS - len(attempts)
        return False, attempts_left


def clear_failed_login(key: str) -> None:
    """Clear failed login attempts on successful login."""
    with _LOCKOUT_LOCK:
        _FAILED_ATTEMPTS.pop(key, None)
        _LOCKED_KEYS.pop(key, None)


def create_session(
    username: str,
    role: str = "admin",
    expires_hours: int = 24,
    doctor_id: str = "",
    doctor_name: str = "",
    must_change_password: bool = False,
) -> str:
    """Generate a cryptographically secure session token and store session metadata."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=expires_hours)
    session_data = {
        "username": username,
        "role": role,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "must_change_password": must_change_password,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "timestamp": expires_at.timestamp(),
    }
    with _SESSIONS_LOCK:
        _ACTIVE_SESSIONS[token] = session_data
    return token


def get_session(token: str) -> Optional[dict]:
    """Retrieve session if valid and unexpired."""
    if not token:
        return None
    now = datetime.now(timezone.utc).timestamp()
    with _SESSIONS_LOCK:
        if token not in _ACTIVE_SESSIONS:
            return None
        session = _ACTIVE_SESSIONS[token]
        if now > session.get("timestamp", 0):
            _ACTIVE_SESSIONS.pop(token, None)
            return None
        return dict(session)


def revoke_session(token: str) -> bool:
    """Invalidate session token."""
    with _SESSIONS_LOCK:
        if token in _ACTIVE_SESSIONS:
            del _ACTIVE_SESSIONS[token]
            return True
    return False


def clear_expired_sessions() -> None:
    """Prune expired sessions from in-memory store."""
    now = datetime.now(timezone.utc).timestamp()
    with _SESSIONS_LOCK:
        expired = [t for t, s in _ACTIVE_SESSIONS.items() if now > s.get("timestamp", 0)]
        for t in expired:
            _ACTIVE_SESSIONS.pop(t, None)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency: Authenticate any valid user via Bearer token or cookie.

    Raises 401 if missing, invalid, or expired.
    """
    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        # Check cookie fallback
        token = request.cookies.get("admin_session")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = get_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_data = dict(session)
    session_data["token"] = token
    return session_data


async def get_current_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """FastAPI dependency: Authenticate that current user has ADMIN role.

    Raises 403 if user is not an administrator.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrator privileges required.",
        )
    return current_user


async def get_current_doctor(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """FastAPI dependency: Authenticate that current user has DOCTOR role.

    Raises 403 if user is not a verified doctor.
    """
    if current_user.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Doctor privileges required.",
        )
    return current_user


async def get_current_admin_or_doctor(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """FastAPI dependency: Authenticate that current user is either ADMIN or DOCTOR."""
    if current_user.get("role") not in ("admin", "doctor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Clinical staff or administrator privileges required.",
        )
    return current_user

