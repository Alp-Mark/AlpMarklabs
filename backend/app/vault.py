from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet

VAULT_KEY_VERSION = "v1"


def _build_vault_key() -> bytes:
    raw_key = os.getenv("ALPMARK_CREDENTIAL_VAULT_KEY")
    if raw_key:
        return raw_key.encode("utf-8")

    # Dev fallback: derive a stable key from auth secret when explicit
    # vault key is absent.
    fallback_secret = os.getenv(
        "AUTH_JWT_SECRET",
        "alpmark-dev-secret-alpmark-dev-secret-2026",
    )
    digest = hashlib.sha256(fallback_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_connector_secret(secret_value: str) -> str:
    cipher = Fernet(_build_vault_key())
    token = cipher.encrypt(secret_value.encode("utf-8"))
    return token.decode("utf-8")


def get_secret_fingerprint(secret_value: str) -> str:
    return hashlib.sha256(secret_value.encode("utf-8")).hexdigest()[:16]
