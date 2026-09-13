# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Encrypts secrets (SMTP password, pattern-sync GitHub token) before they're
stored in the SystemSetting table, which was previously plaintext - readable
to anyone with DB access rather than just the app itself. The key is derived
from SECRET_KEY, so it's already required to be a long random value (see
auth.py) and never lives in the database.

Values written before this module existed are plain, unprefixed strings;
decrypt_secret() returns those as-is rather than failing, and they get
re-encrypted the next time an admin re-saves that setting."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from auth import SECRET_KEY

_ENC_PREFIX = "enc:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"noxus-policy-secrets-at-rest:{SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    if not value:
        return value
    return _ENC_PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    if not value or not value.startswith(_ENC_PREFIX):
        return value or ""
    try:
        return _fernet().decrypt(value[len(_ENC_PREFIX):].encode()).decode()
    except InvalidToken:
        return ""
