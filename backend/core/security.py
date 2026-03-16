from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import get_settings

settings = get_settings()


def _load_or_create_fernet() -> Fernet:
    if settings.fernet_key:
        return Fernet(settings.fernet_key.encode())

    key_path = Path(settings.fernet_key_file)
    if key_path.exists():
        return Fernet(key_path.read_bytes())

    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    return Fernet(key)


_cipher = _load_or_create_fernet()


def encrypt_text(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return _cipher.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    try:
        return _cipher.decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return "[Unable to decrypt data. Check your FERNET_KEY.]"


def hash_access_code(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_access_code() -> str:
    return secrets.token_hex(4).upper()


def generate_ticket_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(3).upper()
    return f"{settings.ticket_prefix}-{stamp}-{suffix}"
