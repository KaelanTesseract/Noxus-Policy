# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import smtplib
from email.message import EmailMessage
import json
import os

import models, schemas, auth, audit, totp
from database import get_db
from rate_limit import rate_limiter, login_failures
from secrets_crypto import encrypt_secret, decrypt_secret
from user_data import delete_user_completely
from http_utils import ics_text as _ics_text

router = APIRouter(prefix="/api/users", tags=["users"])

_ENCRYPTED_SETTING_KEYS = {"smtp_password"}

# Base URL for links in password-reset mails. Deliberately never taken from the
# incoming request (a forged Host/Origin header would let an attacker point the
# reset link at their own server); set it under Systemeinstellungen or via APP_URL.
DEFAULT_APP_URL = os.getenv("APP_URL", "http://localhost:3000")

def get_smtp_setting(db: Session, key: str, default_val: str = "") -> str:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if setting and setting.value is not None:
        value = setting.value
        if key in _ENCRYPTED_SETTING_KEYS:
            value = decrypt_secret(value)
        return value
    return os.getenv(key.upper(), default_val)

def set_smtp_setting(db: Session, key: str, value: str):
    stored_value = encrypt_secret(value) if key in _ENCRYPTED_SETTING_KEYS else value
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if not setting:
        setting = models.SystemSetting(key=key, value=stored_value)
        db.add(setting)
    else:
        setting.value = stored_value

def send_email_message(to_email: str, subject: str, content: str, db: Session):
    smtp_server = get_smtp_setting(db, "smtp_server", "")
    smtp_port = int(get_smtp_setting(db, "smtp_port", "587"))
    smtp_user = get_smtp_setting(db, "smtp_username", "")
    smtp_pw = get_smtp_setting(db, "smtp_password", "")
    smtp_from = get_smtp_setting(db, "smtp_from", "no-reply@noxus-policy.local")
    smtp_use_tls = get_smtp_setting(db, "smtp_use_tls", "true").lower() in ["true", "1", "yes"]

    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email

    if smtp_use_tls or smtp_port == 587:
        with smtplib.SMTP(smtp_server, smtp_port) as s:
            s.starttls()
            if smtp_user and smtp_pw:
                s.login(smtp_user, smtp_pw)
            s.send_message(msg)
    elif smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as s:
            if smtp_user and smtp_pw:
                s.login(smtp_user, smtp_pw)
            s.send_message(msg)
    else:
        with smtplib.SMTP(smtp_server, smtp_port) as s:
            if smtp_user and smtp_pw:
                s.login(smtp_user, smtp_pw)
            s.send_message(msg)

def send_reset_email(email_to: str, token: str, db: Session, request: Request = None):
    app_url = get_smtp_setting(db, "app_url", DEFAULT_APP_URL).rstrip("/")
    if not app_url.startswith("http://") and not app_url.startswith("https://"):
        app_url = f"http://{app_url}"

    reset_url = f"{app_url}/reset-password?token={token}"

    content = (
        f"Hallo,\n\n"
        f"Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts bei Noxus Policy gestellt.\n\n"
        f"Bitte klicken Sie auf folgenden Link, um Ihr Passwort zurückzusetzen:\n"
        f"{reset_url}\n\n"
        f"Falls Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.\n\n"
        f"Viele Grüße,\nIhr Noxus Policy Team"
    )
    try:
        send_email_message(email_to, "Passwort zurücksetzen - Noxus Policy", content, db)
        print(f"Reset email successfully sent to {email_to}")
    except Exception as e:
        print(f"Failed to send reset email to {email_to}: {e}")

def _consume_second_factor(user: models.User, code: str) -> str:
    """Checks the authenticator code or a recovery code for an account with 2FA.
    Returns "totp", "recovery" or "" (invalid) and updates the user row (replay
    protection / used recovery code) - the caller commits."""
    secret = decrypt_secret(user.totp_secret or "")
    if secret:
        step = totp.verify_code(secret, code, user.totp_last_step or 0)
        if step is not None:
            user.totp_last_step = step
            return "totp"
    try:
        stored = json.loads(user.recovery_codes or "[]")
    except ValueError:
        stored = []
    remaining = totp.consume_recovery_code(stored, code)
    if remaining is not None:
        user.recovery_codes = json.dumps(remaining)
        return "recovery"
    return ""


@router.post("/login")
def login(login_data: schemas.UserLogin, request: Request, db: Session = Depends(get_db)):
    try:
        login_failures.check(request, login_data.username)
    except HTTPException as locked:
        if locked.status_code == 429:
            audit.log_event(db, "login_locked", request, actor=login_data.username[:120])
        raise

    user = auth.get_user_by_email(db, login_data.username)
    # Unknown accounts are verified against a dummy hash so the response takes as
    # long as for a wrong password (no account enumeration through timing).
    password_ok = auth.verify_password(login_data.password, user.hashed_password if user else auth.DUMMY_PASSWORD_HASH)
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültige E-Mail-Adresse oder Passwort.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not password_ok:
        login_failures.record_failure(request, login_data.username)
        audit.log_event(db, "login_failed", request, user=user, actor=login_data.username[:120])
        raise invalid

    if user.totp_enabled:
        code = (login_data.otp or "").strip()
        if not code:
            # Password was right; ask for the second factor. No token yet.
            return {"mfa_required": True}
        method = _consume_second_factor(user, code)
        if not method:
            db.rollback()
            login_failures.record_failure(request, login_data.username)
            audit.log_event(db, "login_failed", request, user=user, detail="Zweiter Faktor ungültig")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger Bestätigungscode.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        db.commit()
        if method == "recovery":
            audit.log_event(db, "recovery_code_used", request, user=user)

    login_failures.reset_account(request, login_data.username)
    audit.log_event(db, "login_success", request, user=user)
    access_token = auth.create_login_token(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "must_change_password": user.must_change_password
        }
    }

def _registration_enabled(db: Session) -> bool:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "registration_enabled").first()
    if setting and setting.value is not None:
        return setting.value.lower() in ["true", "1", "yes"]
    return True

@router.get("/registration-status")
def get_registration_status(db: Session = Depends(get_db)):
    # Public on purpose: the register page needs it before anyone is logged in.
    return {"enabled": _registration_enabled(db)}

@router.put("/registration-config")
def update_registration_config(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Systemeinstellungen verändern.")

    value = "true" if payload.get("enabled") else "false"
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "registration_enabled").first()
    if not setting:
        db.add(models.SystemSetting(key="registration_enabled", value=value))
    else:
        setting.value = value
    db.commit()
    audit.log_event(db, "registration_changed", request, user=current_user, detail=f"aktiv={value}")
    return {"enabled": value == "true"}

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Bumping the token version invalidates this token and every other one
    # issued to this account - logging out ends all sessions, not just this browser's.
    auth.revoke_tokens(current_user)
    db.commit()
    # The sliding-session refresh may already have queued a new token; it is now void.
    if "X-Refreshed-Token" in response.headers:
        del response.headers["X-Refreshed-Token"]
    audit.log_event(db, "logout", request, user=current_user)
    return {"msg": "Abgemeldet."}

@router.post("/register", response_model=schemas.UserResponse, dependencies=[Depends(rate_limiter(max_calls=3, period_seconds=300))])
def register_user(payload: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    if not _registration_enabled(db):
        raise HTTPException(status_code=403, detail="Die Registrierung ist auf dieser Instanz deaktiviert.")

    email_clean = payload.email.strip()
    if not email_clean:
        raise HTTPException(status_code=400, detail="Ungültige E-Mail-Adresse.")
    auth.validate_password_strength(payload.password, email_clean)

    existing_user = auth.get_user_by_email(db, email_clean)
    if existing_user:
        raise HTTPException(status_code=400, detail="Diese E-Mail-Adresse ist bereits registriert.")

    hashed_pw = auth.get_password_hash(payload.password)
    new_user = models.User(
        email=email_clean,
        hashed_password=hashed_pw,
        is_admin=False,
        must_change_password=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    audit.log_event(db, "register", request, user=new_user)
    return new_user

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@router.get("/all", response_model=List[schemas.UserListItem])
def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen die Benutzerliste einsehen.")
    return db.query(models.User).all()

@router.put("/profile", response_model=schemas.UserResponse)
def update_profile(
    payload: schemas.ProfileUpdatePayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    credentials_changed = False
    audit_events = []
    if payload.email and payload.email.strip() != "":
        new_email = payload.email.strip()
        existing = auth.get_user_by_email(db, new_email)
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Diese E-Mail-Adresse wird bereits verwendet.")
        if new_email != current_user.email:
            credentials_changed = True
            audit_events.append("email_changed")
        current_user.email = new_email

    if payload.new_password and payload.new_password.strip() != "":
        auth.validate_password_strength(payload.new_password.strip(), current_user.email)
        current_user.hashed_password = auth.get_password_hash(payload.new_password.strip())
        current_user.must_change_password = False
        auth.revoke_tokens(current_user)
        credentials_changed = True
        audit_events.append("password_changed")

    if payload.email_notifications_enabled is not None:
        current_user.email_notifications_enabled = payload.email_notifications_enabled

    try:
        db.commit()
        db.refresh(current_user)
        for event in audit_events:
            audit.log_event(db, event, request, user=current_user)
        if credentials_changed:
            # The token in use was just invalidated (password changed - all older
            # tokens are revoked - or the email it is bound to changed), so hand
            # the caller a fresh one instead of silently logging them out.
            response.headers["X-Refreshed-Token"] = auth.create_login_token(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        print(f"[Profile Update Error] {e}")
        raise HTTPException(status_code=400, detail="Fehler beim Speichern des Profils.")

@router.get("/smtp-status")
def get_smtp_status(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    smtp_server = get_smtp_setting(db, "smtp_server", "")
    is_configured = bool(smtp_server and smtp_server.strip())
    return {"configured": is_configured}

@router.get("/smtp-config")
def get_smtp_config(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen SMTP-Einstellungen verwalten.")
    return {
        "app_url": get_smtp_setting(db, "app_url", DEFAULT_APP_URL),
        "smtp_server": get_smtp_setting(db, "smtp_server", ""),
        "smtp_port": get_smtp_setting(db, "smtp_port", "587"),
        "smtp_username": get_smtp_setting(db, "smtp_username", ""),
        # Never sent back: the admin UI (and anyone who can read its responses) doesn't
        # need the stored secret, only to know whether one is set.
        "smtp_password_set": bool(get_smtp_setting(db, "smtp_password", "")),
        "smtp_from": get_smtp_setting(db, "smtp_from", "no-reply@noxus-policy.local"),
        "smtp_use_tls": get_smtp_setting(db, "smtp_use_tls", "true").lower() in ["true", "1", "yes"],
    }

@router.post("/smtp-config")
def save_smtp_config(payload: dict, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen SMTP-Einstellungen verwalten.")

    if "app_url" in payload:
        set_smtp_setting(db, "app_url", str(payload["app_url"]).strip())
    if "smtp_server" in payload:
        set_smtp_setting(db, "smtp_server", str(payload["smtp_server"]).strip())
    if "smtp_port" in payload:
        set_smtp_setting(db, "smtp_port", str(payload["smtp_port"]).strip())
    if "smtp_username" in payload:
        set_smtp_setting(db, "smtp_username", str(payload["smtp_username"]).strip())
    # An empty value means "keep the stored password" - the form is never pre-filled with it.
    if payload.get("smtp_password"):
        set_smtp_setting(db, "smtp_password", str(payload["smtp_password"]))
    if "smtp_from" in payload:
        set_smtp_setting(db, "smtp_from", str(payload["smtp_from"]).strip())
    if "smtp_use_tls" in payload:
        set_smtp_setting(db, "smtp_use_tls", "true" if payload["smtp_use_tls"] else "false")

    db.commit()
    audit.log_event(db, "smtp_config_changed", request, user=current_user)
    return {"msg": "SMTP-Einstellungen erfolgreich gespeichert!"}

@router.post("/smtp-test")
def test_smtp_config(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Test-E-Mails versenden.")

    target_email = payload.get("target_email") or current_user.email
    try:
        send_email_message(
            target_email,
            "Noxus Policy - E-Mail Test erfolgreich!",
            f"Hallo {current_user.email},\n\ndiese Test-E-Mail bestätigt, dass deine SMTP-Konfiguration in Noxus Policy einwandfrei funktioniert!\n\nViele Grüße,\nNoxus Policy Team",
            db
        )
        return {"msg": f"Test-E-Mail wurde erfolgreich an {target_email} versendet!"}
    except Exception as e:
        print(f"[SMTP Test] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Senden der Test-E-Mail ({type(e).__name__}). Details stehen im Server-Log.")

@router.post("/forgot-password", dependencies=[Depends(rate_limiter(max_calls=3, period_seconds=300))])
def forgot_password(payload: schemas.ForgotPasswordPayload, request: Request, db: Session = Depends(get_db)):
    user = auth.get_user_by_email(db, payload.email)
    if user:
        token = auth.create_reset_token(user)
        send_reset_email(user.email, token, db, request)
        audit.log_event(db, "password_reset_requested", request, user=user)

    # Always return success message for security reasons
    return {"msg": "Falls diese E-Mail-Adresse registriert ist, wurde eine E-Mail zum Zurücksetzen gesendet."}

@router.post("/reset-password", dependencies=[Depends(rate_limiter(max_calls=5, period_seconds=300))])
def reset_password(payload: schemas.ResetPasswordPayload, request: Request, db: Session = Depends(get_db)):
    user = auth.resolve_reset_token(payload.token, db)

    auth.validate_password_strength(payload.new_password, user.email)

    user.hashed_password = auth.get_password_hash(payload.new_password)
    user.must_change_password = False
    # Makes the reset link single-use and signs out every existing session.
    auth.revoke_tokens(user)
    db.commit()
    audit.log_event(db, "password_reset_completed", request, user=user)
    return {"msg": "Passwort erfolgreich zurückgesetzt. Sie können sich jetzt anmelden."}

@router.post("/admin/send-reset-email")
def admin_send_reset_email(
    email: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren können Passwort-Resets versenden.")

    user = auth.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")

    token = auth.create_reset_token(user)
    send_reset_email(user.email, token, db, request)
    return {"msg": f"Passwort-Zurücksetzen-E-Mail wurde an {user.email} versendet."}

@router.post("/admin/initial-setup")
def admin_initial_setup(
    payload: schemas.AdminInitialSetupPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin or not current_user.must_change_password:
        raise HTTPException(status_code=403, detail="Ersteinrichtung nicht berechtigt oder bereits abgeschlossen")

    existing_user = auth.get_user_by_email(db, payload.new_email)
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(status_code=400, detail="Diese E-Mail-Adresse wird bereits verwendet.")

    auth.validate_password_strength(payload.new_password, payload.new_email)

    try:
        current_user.email = payload.new_email
        current_user.hashed_password = auth.get_password_hash(payload.new_password)
        current_user.must_change_password = False
        auth.revoke_tokens(current_user)
        db.commit()
        audit.log_event(db, "admin_initial_setup", request, user=current_user)
    except Exception as e:
        db.rollback()
        print(f"[Admin Initial Setup Error] {e}")
        raise HTTPException(status_code=400, detail="Fehler beim Speichern der Ersteinrichtung.")

    return {"msg": "Ersteinrichtung erfolgreich abgeschlossen"}

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Benutzer löschen.")

    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Sie können Ihren eigenen Admin-Account nicht löschen.")

    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")

    target_email = target_user.email
    try:
        delete_user_completely(db, target_user)
    except Exception as e:
        db.rollback()
        print(f"[Delete User Error] {e}")
        raise HTTPException(status_code=400, detail="Fehler beim Löschen des Benutzers.")

    audit.log_event(db, "user_deleted", request, user=current_user, detail=f"Konto: {target_email}")
    return {"msg": f"Benutzer {target_email} wurde erfolgreich gelöscht. Bereits erstellte Backups enthalten dessen Daten weiterhin, bis sie gelöscht werden."}

@router.post("/me/delete", dependencies=[Depends(rate_limiter(max_calls=5, period_seconds=300))])
def delete_own_account(
    payload: schemas.PasswordConfirmPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Right to erasure: lets a user remove their own account and all its data.
    Administrators are excluded so an instance can never end up without one - they
    hand over the role first (or another admin deletes the account)."""
    if current_user.is_admin:
        raise HTTPException(status_code=400, detail="Administrator-Konten können nicht selbst gelöscht werden.")
    if not auth.verify_password(payload.password, current_user.hashed_password):
        audit.log_event(db, "login_failed", request, user=current_user, detail="Kontolöschung: falsches Passwort")
        raise HTTPException(status_code=403, detail="Das Passwort ist nicht korrekt.")

    email = current_user.email
    try:
        delete_user_completely(db, current_user)
    except Exception as e:
        db.rollback()
        print(f"[Delete Own Account Error] {e}")
        raise HTTPException(status_code=400, detail="Fehler beim Löschen des Kontos.")
    audit.log_event(db, "account_deleted", request, actor=email)
    return {"msg": "Dein Konto und alle zugehörigen Daten wurden gelöscht."}

import secrets
from fastapi import Response
import datetime

@router.get("/calendar-token")
def get_calendar_token(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.calendar_token:
        current_user.calendar_token = secrets.token_hex(20)
        db.commit()
        db.refresh(current_user)
    return {"calendar_token": current_user.calendar_token}

@router.post("/calendar-token/rotate")
def rotate_calendar_token(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    current_user.calendar_token = secrets.token_hex(20)
    db.commit()
    db.refresh(current_user)
    audit.log_event(db, "calendar_token_rotated", request, user=current_user)
    return {"calendar_token": current_user.calendar_token, "msg": "Neuer Kalender-Token wurde generiert."}

def build_ics_string(user_id: int, insurances: list) -> str:
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Noxus Policy//Live Calendar Sync//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Noxus Policy - Kündigungsfristen",
        "X-WR-CALDESC:Live-Synchronisation aller Kündigungsfristen deiner Versicherungspolicen.",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H"
    ]

    for ins in insurances:
        deadline_date = ins.cancellation_date or ins.end_date
        if not deadline_date:
            continue

        date_str = deadline_date.strftime("%Y%m%d")
        created_str = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = f"noxus-policy-ins-{ins.id}-{date_str}@noxus-policy"

        title = _ics_text(f"⏰ Kündigungsfrist: {ins.name} ({ins.company or 'Unbekannt'})")
        desc_parts = [
            f"Versicherung: {ins.name}",
            f"Gesellschaft: {ins.company or 'Nicht angegeben'}",
            f"Schein-Nr: {ins.insurance_number or 'k.A.'}",
            f"Kategorie: {ins.category or 'Sonstige'}",
            f"Kosten: {ins.cost:.2f} € ({ins.payment_cycle or 'jährlich'})" if ins.cost else "Kosten: k.A."
        ]
        if ins.is_suspended:
            desc_parts.append(f"Status: ⏸️ Vertag ruht ({ins.suspension_reason or 'Beitragsfrei'})")

        description = "\\n".join(_ics_text(part) for part in desc_parts)

        event_block = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{created_str}",
            f"DTSTART;VALUE=DATE:{date_str}",
            f"DTEND;VALUE=DATE:{date_str}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{description}",
            "STATUS:CONFIRMED",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Erinnerung Kündigungsfrist in 14 Tagen",
            "TRIGGER:-P14D",
            "END:VALARM",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Eilige Erinnerung Kündigungsfrist in 7 Tagen",
            "TRIGGER:-P7D",
            "END:VALARM",
            "END:VEVENT"
        ]
        ics_lines.extend(event_block)

    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines)

def _webcal_enabled(db: Session) -> bool:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "webcal_enabled").first()
    return setting.value.lower() == "true" if setting and setting.value else False

@router.get("/webcal-config")
def get_webcal_config(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return {"enabled": _webcal_enabled(db)}

@router.put("/webcal-config")
def update_webcal_config(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Systemeinstellungen verändern.")

    enabled_val = "true" if payload.get("enabled") else "false"
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "webcal_enabled").first()
    if not setting:
        setting = models.SystemSetting(key="webcal_enabled", value=enabled_val)
        db.add(setting)
    else:
        setting.value = enabled_val
    db.commit()
    audit.log_event(db, "webcal_config_changed", request, user=current_user, detail=f"aktiv={enabled_val}")
    return {"msg": f"WebCal-Einstellung wurde auf '{enabled_val}' aktualisiert."}

@router.get("/calendar/export.ics")
def download_manual_calendar_ics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    insurances = db.query(models.Insurance).filter(models.Insurance.owner_id == current_user.id).all()
    ics_content = build_ics_string(current_user.id, insurances)
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="noxus_policy_kuendigungsfristen.ics"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

@router.get("/calendar/feed.ics")
def get_calendar_feed(
    token: str,
    db: Session = Depends(get_db)
):
    if not _webcal_enabled(db):
        raise HTTPException(status_code=403, detail="WebCal Live-Sync ist vom Administrator deaktiviert.")

    if not token or len(token) < 10:
        raise HTTPException(status_code=401, detail="Ungültiger Token")

    user = db.query(models.User).filter(models.User.calendar_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Kalender-Abonnement nicht autorisiert")

    insurances = db.query(models.Insurance).filter(models.Insurance.owner_id == user.id).all()
    ics_content = build_ics_string(user.id, insurances)

    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="noxus_policy_calendar_{user.id}.ics"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )


# --------------------------------------------------------------------------------
# Second factor (TOTP) and audit log
# --------------------------------------------------------------------------------

_twofa_limit = rate_limiter(max_calls=10, period_seconds=300)


def _require_password(request: Request, db: Session, user: models.User, password: str) -> None:
    if not auth.verify_password(password, user.hashed_password):
        audit.log_event(db, "login_failed", request, user=user, detail="Bestätigung mit falschem Passwort")
        raise HTTPException(status_code=403, detail="Das Passwort ist nicht korrekt.")


@router.post("/2fa/setup", dependencies=[Depends(_twofa_limit)])
def twofa_setup(
    payload: schemas.PasswordConfirmPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Step 1: creates a fresh secret (not active yet) for the authenticator app."""
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="Die 2-Faktor-Authentifizierung ist bereits aktiv.")
    _require_password(request, db, current_user, payload.password)

    secret = totp.generate_secret()
    current_user.totp_secret = encrypt_secret(secret)
    db.commit()
    return {"secret": secret, "otpauth_uri": totp.provisioning_uri(secret, current_user.email)}


@router.post("/2fa/enable", dependencies=[Depends(_twofa_limit)])
def twofa_enable(
    payload: schemas.TwoFactorEnablePayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Step 2: activates the second factor once the user proves the app works, and
    returns the single-use recovery codes (shown only this once)."""
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="Die 2-Faktor-Authentifizierung ist bereits aktiv.")
    secret = decrypt_secret(current_user.totp_secret or "")
    if not secret:
        raise HTTPException(status_code=400, detail="Bitte starte die Einrichtung zuerst.")
    step = totp.verify_code(secret, payload.code)
    if step is None:
        raise HTTPException(status_code=400, detail="Der Code stimmt nicht. Bitte prüfe die Uhrzeit deines Geräts und versuche es erneut.")

    codes = totp.generate_recovery_codes()
    current_user.totp_enabled = True
    current_user.totp_last_step = step
    current_user.recovery_codes = json.dumps([totp.hash_recovery_code(c) for c in codes])
    # Other sessions were opened without the second factor - end them, keep this one.
    auth.revoke_tokens(current_user)
    db.commit()
    db.refresh(current_user)
    response.headers["X-Refreshed-Token"] = auth.create_login_token(current_user)
    audit.log_event(db, "twofa_enabled", request, user=current_user)
    return {"recovery_codes": codes}


@router.post("/2fa/disable", dependencies=[Depends(_twofa_limit)])
def twofa_disable(
    payload: schemas.TwoFactorDisablePayload,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="Die 2-Faktor-Authentifizierung ist nicht aktiv.")
    _require_password(request, db, current_user, payload.password)
    if not _consume_second_factor(current_user, payload.code.strip()):
        db.rollback()
        audit.log_event(db, "login_failed", request, user=current_user, detail="Deaktivieren: Code ungültig")
        raise HTTPException(status_code=403, detail="Ungültiger Bestätigungscode.")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_last_step = 0
    current_user.recovery_codes = None
    auth.revoke_tokens(current_user)
    db.commit()
    db.refresh(current_user)
    response.headers["X-Refreshed-Token"] = auth.create_login_token(current_user)
    audit.log_event(db, "twofa_disabled", request, user=current_user)
    return {"msg": "Die 2-Faktor-Authentifizierung wurde deaktiviert."}


@router.post("/2fa/reset/{user_id}")
def twofa_admin_reset(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """For a user who lost both their authenticator and their recovery codes."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen die 2-Faktor-Authentifizierung zurücksetzen.")
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")
    target.totp_enabled = False
    target.totp_secret = None
    target.totp_last_step = 0
    target.recovery_codes = None
    auth.revoke_tokens(target)
    db.commit()
    audit.log_event(db, "twofa_reset", request, user=current_user, detail=f"Konto: {target.email}")
    return {"msg": f"Die 2-Faktor-Authentifizierung von {target.email} wurde zurückgesetzt."}


@router.get("/audit-log", response_model=List[schemas.AuditLogEntry])
def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen das Protokoll einsehen.")
    query = db.query(models.AuditLog)
    if action:
        query = query.filter(models.AuditLog.action == action)
    rows = query.order_by(models.AuditLog.id.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 500)).all()
    return [
        schemas.AuditLogEntry(
            id=r.id, created_at=r.created_at, action=r.action,
            action_label=audit.ACTION_LABELS.get(r.action, r.action),
            user_id=r.user_id, actor=r.actor, ip=r.ip, detail=r.detail,
        )
        for r in rows
    ]
