import os
import hmac
import hashlib
import base64
import time
import json
import logging

logger = logging.getLogger("cabinops.security.tokens")

# Ensure .env is loaded if it exists
def _load_env():
    from pathlib import Path
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass

_load_env()

SECRET_KEY = os.getenv("SECRET_KEY")
TESTING = os.getenv("TESTING", "false").lower() == "true"

if not SECRET_KEY:
    if TESTING:
        SECRET_KEY = "cabinops_test_secure_salt_secret_123!"
    else:
        # Fallback to an auto-generated token in development if not loaded
        if os.getenv("ENV") != "production":
            import secrets
            SECRET_KEY = secrets.token_hex(32)
            os.environ["SECRET_KEY"] = SECRET_KEY
        else:
            raise RuntimeError("SECRET_KEY environment variable must be configured")

def generate_token(payload: dict) -> str:
    payload = {**payload, "exp": time.time() + 86400}  # 24-hour expiration
    payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), payload_str.encode(), hashlib.sha256).digest()
    sig_str = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{payload_str}.{sig_str}"

def verify_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_str, sig_str = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_str.encode(), hashlib.sha256).digest()
        expected_sig_str = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if not hmac.compare_digest(sig_str, expected_sig_str):
            return None
        
        padded = payload_str + "=" * (-len(payload_str) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception as exc:
        logger.error(f"Token verification error: {exc}")
        return None
