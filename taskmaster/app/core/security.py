"""
Security utilities: JWT creation/verification and password hashing.
Passwords are hashed with bcrypt via passlib. Tokens use python-jose.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of the given plain-text password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_token(
    subject: str,
    token_type: str,
    secret_key: str,
    expire_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expire_delta,
        "jti": secrets.token_hex(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret_key, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived JWT access token."""
    return _create_token(
        subject=user_id,
        token_type="access",
        secret_key=settings.SECRET_KEY,
        expire_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"role": role},
    )


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token."""
    return _create_token(
        subject=user_id,
        token_type="refresh",
        secret_key=settings.REFRESH_SECRET_KEY,
        expire_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.
    Raises JWTError on failure.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh token.
    Raises JWTError on failure.
    """
    payload = jwt.decode(
        token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return payload


def hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of a token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Password policy ───────────────────────────────────────────────────────────

def validate_password_strength(password: str) -> str:
    """
    Enforce password policy:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one digit
    Returns the password unchanged if valid, raises ValueError otherwise.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    return password
