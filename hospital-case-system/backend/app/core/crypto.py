"""Field-level encryption for API keys, Aadhaar numbers and Drive blobs."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

ENC_PREFIX = "enc:"


def _build_fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if key:
        try:
            return Fernet(key.encode())
        except Exception:
            pass
    material = (settings.FIELD_ENCRYPTION_KEY or settings.SECRET_KEY).encode()
    derived = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(derived)


_fernet = _build_fernet()


def encrypt_key(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_key(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()


def mask_key(value: str | None) -> str:
    if not value:
        return ""
    return "••••••••" + value[-4:]


def encrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    return ENC_PREFIX + _fernet.encrypt(value.encode()).decode()


def decrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not value.startswith(ENC_PREFIX):
        return value  # legacy plaintext
    try:
        return _fernet.decrypt(value[len(ENC_PREFIX):].encode()).decode()
    except (InvalidToken, Exception):
        return None


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet.encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    return _fernet.decrypt(data)
