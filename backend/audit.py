# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Audit trail for security-relevant events, readable by admins in the settings.

Never put secrets, passwords, tokens or document contents into ``detail``. A
failure to write an entry must not break the action being logged, so errors are
swallowed (and printed)."""

import datetime
import threading
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

import models
from rate_limit import get_client_ip

RETENTION_DAYS = 365
_PRUNE_EVERY = 200
_counter = 0
_counter_lock = threading.Lock()

# Human-readable labels; the frontend shows these, unknown codes are shown as-is.
ACTION_LABELS = {
    "login_success": "Anmeldung",
    "login_failed": "Fehlgeschlagene Anmeldung",
    "login_locked": "Anmeldung gesperrt (zu viele Fehlversuche)",
    "logout": "Abmeldung",
    "register": "Neues Konto registriert",
    "password_changed": "Passwort geändert",
    "email_changed": "E-Mail-Adresse geändert",
    "password_reset_requested": "Passwort-Reset angefordert",
    "password_reset_completed": "Passwort per Reset gesetzt",
    "admin_initial_setup": "Ersteinrichtung des Admin-Kontos",
    "user_deleted": "Benutzer gelöscht",
    "account_deleted": "Eigenes Konto gelöscht",
    "twofa_enabled": "2-Faktor-Authentifizierung aktiviert",
    "twofa_disabled": "2-Faktor-Authentifizierung deaktiviert",
    "twofa_reset": "2-Faktor-Authentifizierung vom Admin zurückgesetzt",
    "recovery_code_used": "Wiederherstellungscode verwendet",
    "registration_changed": "Registrierung ein-/ausgeschaltet",
    "smtp_config_changed": "SMTP-Einstellungen geändert",
    "backup_config_changed": "Backup-Einstellungen geändert",
    "backup_password_revealed": "Backup-Passwort angezeigt",
    "backup_exported": "System-Backup exportiert",
    "backup_restored": "System-Backup wiederhergestellt",
    "user_exported": "Benutzerdaten exportiert",
    "user_imported": "Benutzerdaten importiert",
    "ai_config_changed": "KI-Einstellung geändert",
    "pattern_sync_changed": "Muster-Sync-Einstellung geändert",
    "webcal_config_changed": "WebCal-Einstellung geändert",
    "calendar_token_rotated": "Kalender-Token erneuert",
}


def log_event(db: Session, action: str, request: Optional[Request] = None,
              user: Optional[models.User] = None, actor: Optional[str] = None,
              detail: Optional[str] = None) -> None:
    global _counter
    try:
        db.add(models.AuditLog(
            action=action,
            user_id=user.id if user is not None else None,
            actor=(user.email if user is not None else actor),
            ip=get_client_ip(request) if request is not None else None,
            detail=(detail or None) and detail[:300],
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Audit] could not record '{action}': {type(e).__name__}")
        return

    with _counter_lock:
        _counter += 1
        due = _counter % _PRUNE_EVERY == 0
    if due:
        prune(db)


def prune(db: Session) -> None:
    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=RETENTION_DAYS)
        db.query(models.AuditLog).filter(models.AuditLog.created_at < cutoff).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Audit] prune failed: {type(e).__name__}")
