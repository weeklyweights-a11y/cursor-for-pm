"""Fernet symmetric encryption for sensitive data (e.g. Slack tokens)."""

import base64
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings


def _get_fernet() -> Fernet:
    """Build Fernet from settings.encryption_key (raw or base64)."""
    key = (settings.encryption_key or "").strip()
    if not key:
        raise ValueError("ENCRYPTION_KEY is not set; cannot encrypt or decrypt.")
    try:
        # If it's valid base64 32-byte Fernet key, use as-is
        decoded = base64.urlsafe_b64decode(key)
        if len(decoded) == 32:
            return Fernet(base64.urlsafe_b64encode(decoded))
    except Exception:
        pass
    # Otherwise derive 32-byte key from password-like key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"cursor_for_pms_salt",
        iterations=100000,
    )
    derived = base64.urlsafe_b64encode(kdf.derive(key.encode("utf-8")))
    return Fernet(derived)


def encrypt(plain_text: str) -> str:
    """Encrypt a string; returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plain_text.encode("utf-8")).decode("ascii")


def decrypt(cipher_text: str) -> str:
    """Decrypt ciphertext from encrypt(). Raises if key wrong or tampered."""
    f = _get_fernet()
    try:
        return f.decrypt(cipher_text.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Decryption failed (wrong key or tampered data).") from e
