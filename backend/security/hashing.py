import hashlib
import os
import hmac

def hash_password(password: str) -> str:
    # Use PBKDF2 with SHA512, 600,000 iterations (OWASP recommendation), and a random 32-byte salt
    salt = os.urandom(32)
    pw_hash = hashlib.pbkdf2_hmac('sha512', password.encode(), salt, 600000)
    return f"{salt.hex()}:{pw_hash.hex()}"

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    try:
        salt_hex, hash_hex = stored_password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        pw_hash = hashlib.pbkdf2_hmac('sha512', provided_password.encode(), salt, 600000)
        return hmac.compare_digest(pw_hash, expected_hash)
    except Exception:
        return False
