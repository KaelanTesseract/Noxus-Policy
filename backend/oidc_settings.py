# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Single sign-on settings, stored like the other instance settings in the
SystemSetting table. The client secret is encrypted at rest and is only ever read
back by the server itself, never sent to the browser."""

import os
from typing import Optional

from sqlalchemy.orm import Session

import models
from oidc import OidcConfig
from secrets_crypto import decrypt_secret, encrypt_secret

_ENCRYPTED_KEYS = {"oidc_client_secret"}
CALLBACK_PATH = "/api/auth/oidc/callback"


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if row is None or row.value is None:
        return default
    return decrypt_secret(row.value) if key in _ENCRYPTED_KEYS else row.value


def set_setting(db: Session, key: str, value: str) -> None:
    """Stores a value; the caller commits."""
    stored = encrypt_secret(value) if key in _ENCRYPTED_KEYS else value
    row = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if row is None:
        db.add(models.SystemSetting(key=key, value=stored))
    else:
        row.value = stored


def _flag(db: Session, key: str, default: bool) -> bool:
    value = get_setting(db, key, "")
    return default if value == "" else value.lower() in ("true", "1", "yes")


def oidc_enabled(db: Session) -> bool:
    return _flag(db, "oidc_enabled", False)


def password_login_enabled(db: Session) -> bool:
    return _flag(db, "password_login_enabled", True)


def auto_create_enabled(db: Session) -> bool:
    return _flag(db, "oidc_auto_create", True)


def app_base(db: Session) -> str:
    """The public address of this installation (the same setting the password-reset
    mails use): what an administrator typed, else the APP_URL environment variable."""
    base = (get_setting(db, "app_url", "") or os.getenv("APP_URL", "http://localhost:3000")).strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    return base


def redirect_uri(db: Session) -> str:
    """Built from the configured address, never from request headers: a forged Host
    header must not be able to steer where the provider sends the browser back."""
    return app_base(db) + CALLBACK_PATH


def load_config(db: Session) -> Optional[OidcConfig]:
    """The complete configuration, or None when SSO is off or not fully set up."""
    if not oidc_enabled(db):
        return None
    issuer = get_setting(db, "oidc_issuer").strip()
    client_id = get_setting(db, "oidc_client_id").strip()
    secret = get_setting(db, "oidc_client_secret")
    if not (issuer and client_id and secret):
        return None
    return OidcConfig(issuer=issuer, client_id=client_id, client_secret=secret, redirect_uri=redirect_uri(db))
