"""Authentication and authorization utilities for Clinic CRM Admin.

Provides secure password hashing (PBKDF2-HMAC-SHA256, 100k iterations),
cryptographic session token generation, session lifecycle tracking,
and FastAPI route protection dependencies.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

# In-memory session store: token -> session dict
_ACTIVE_SESSIONS: dict[str, dict] = {}


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
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
            iterations
        )
        return hmac.compare_digest(calculated_key.hex(), key_hex)
    except Exception:
        return False


def create_session(username: str, role: str = "admin", expires_hours: int = 24) -> str:
    """Generate a cryptographically secure session token and store session metadata."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=expires_hours)
    _ACTIVE_SESSIONS[token] = {
        "username": username,
        "role": role,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "timestamp": expires_at.timestamp(),
    }
    return token


def get_session(token: str) -> Optional[dict]:
    """Retrieve session if valid and unexpired."""
    if not token or token not in _ACTIVE_SESSIONS:
        return None
    session = _ACTIVE_SESSIONS[token]
    now = datetime.now(timezone.utc).timestamp()
    if now > session.get("timestamp", 0):
        _ACTIVE_SESSIONS.pop(token, None)
        return None
    return session


def revoke_session(token: str) -> bool:
    """Invalidate session token."""
    if token in _ACTIVE_SESSIONS:
        del _ACTIVE_SESSIONS[token]
        return True
    return False


def clear_expired_sessions() -> None:
    """Prune expired sessions from in-memory store."""
    now = datetime.now(timezone.utc).timestamp()
    expired = [t for t, s in _ACTIVE_SESSIONS.items() if now > s.get("timestamp", 0)]
    for t in expired:
        _ACTIVE_SESSIONS.pop(t, None)


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency: Authenticate admin user via Bearer token or cookie.

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
