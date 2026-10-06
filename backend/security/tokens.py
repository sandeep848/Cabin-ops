"""Bounded HMAC sessions with server-side revocation; never store bearer secrets."""

import os
import hmac
import hashlib
import base64
import time
import json
import secrets
from backend import config
from backend.database.connection import get_connection

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("ENV") == "production":
        raise RuntimeError("SECRET_KEY must be configured in production")
    SECRET_KEY = secrets.token_hex(32)
if os.getenv("ENV") == "production" and len(SECRET_KEY) < 32:
    raise RuntimeError("Use a random SECRET_KEY of at least 32 characters")
SESSION_SECONDS = 6 * 60 * 60


def generate_token(payload: dict) -> str:
    now = int(time.time())
    token_id = secrets.token_hex(24)
    subject = (
        ("crew:" + payload.get("username", "crew"))
        if payload["role"] == "crew"
        else (payload["flight_id"] + ":" + payload["seat"])
    )
    claims = {
        **payload,
        "iat": now,
        "exp": now + SESSION_SECONDS,
        "jti": token_id,
        "aud": "cabin-atlas",
    }
    encoded = (
        base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    signature = (
        base64.urlsafe_b64encode(
            hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).digest()
        )
        .decode()
        .rstrip("=")
    )
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        conn.execute(
            "INSERT INTO sessions (token_id, subject, expires_at) VALUES (?, ?, ?)",
            (token_id, subject, claims["exp"]),
        )
        # Limit retained sessions for a shared device/principal.
        conn.execute(
            "DELETE FROM sessions WHERE subject = ? AND token_id NOT IN (SELECT token_id FROM sessions WHERE subject = ? ORDER BY rowid DESC LIMIT 8)",
            (subject, subject),
        )
    return encoded + "." + signature


def verify_token(token: str) -> dict | None:
    if not isinstance(token, str) or len(token) > 4096:
        return None
    try:
        encoded, signature = token.split(".")
        expected = (
            base64.urlsafe_b64encode(
                hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).digest()
            )
            .decode()
            .rstrip("=")
        )
        if not hmac.compare_digest(signature, expected):
            return None
        claims = json.loads(
            base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        )
        now = time.time()
        if (
            not isinstance(claims, dict)
            or claims.get("aud") != "cabin-atlas"
            or not isinstance(claims.get("exp"), (int, float))
            or claims["exp"] <= now
        ):
            return None
        if claims.get("role") not in {"crew", "passenger"} or not isinstance(
            claims.get("jti"), str
        ):
            return None
        with get_connection() as conn:
            row = conn.execute(
                "SELECT expires_at FROM sessions WHERE token_id = ?", (claims["jti"],)
            ).fetchone()
        return claims if row and row["expires_at"] > now else None
    except (ValueError, TypeError, KeyError, UnicodeError):
        return None


def revoke_token(claims: dict) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM media_grants WHERE token_id = ?", (claims["jti"],))
        conn.execute("DELETE FROM sessions WHERE token_id = ?", (claims["jti"],))


def revoke_subject(subject: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM media_grants WHERE token_id IN (SELECT token_id FROM sessions WHERE subject = ?)",
            (subject,),
        )
        conn.execute("DELETE FROM sessions WHERE subject = ?", (subject,))
