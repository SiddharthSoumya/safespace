from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import get_settings

settings = get_settings()


def _load_or_create_fernet() -> Fernet:
    if settings.fernet_key:
        try:
            return Fernet(settings.fernet_key.encode("utf-8"))
        except (TypeError, ValueError):
            raise RuntimeError("FERNET_KEY must be a valid Fernet key.") from None

    key_path = Path(settings.fernet_key_file)
    if key_path.exists():
        try:
            return Fernet(key_path.read_bytes())
        except (TypeError, ValueError):
            raise RuntimeError("The local Fernet key file is invalid.") from None

    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise RuntimeError("Production requires FERNET_KEY; a local key file will not be generated.")

    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    try:
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        try:
            return Fernet(key_path.read_bytes())
        except (TypeError, ValueError):
            raise RuntimeError("The local Fernet key file is invalid.") from None
    with os.fdopen(descriptor, "wb") as key_file:
        key_file.write(key)
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
        raise RuntimeError("Stored data could not be decrypted; verify that FERNET_KEY has not changed.") from None


def hash_access_code(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_access_code() -> str:
    return secrets.token_hex(16).upper()


def verify_access_code_hash(stored_hash: str, provided_code: str) -> bool:
    return hmac.compare_digest(stored_hash, hash_access_code(provided_code.strip()))


def generate_ticket_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(3).upper()
    return f"{settings.ticket_prefix}-{stamp}-{suffix}"
