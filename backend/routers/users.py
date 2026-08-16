# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import smtplib
from email.message import EmailMessage
import os

import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

def get_smtp_setting(db: Session, key: str, default_val: str = "") -> str:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if setting and setting.value is not None:
        return setting.value
    return os.getenv(key.upper(), default_val)

def set_smtp_setting(db: Session, key: str, value: str):
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if not setting:
        setting = models.SystemSetting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value

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
    app_url = get_smtp_setting(db, "app_url", "http://192.168.1.251:3000").rstrip("/")
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
        print(f"Reset email successfully sent to {email_to} with URL {reset_url}")
    except Exception as e:
        print(f"Failed to send reset email to {email_to}: {e}")

@router.post("/login")
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email.ilike(login_data.username)).first()
    
    is_valid = auth.verify_password(login_data.password, user.hashed_password) if user else False
    if user and user.must_change_password and not is_valid:
        if login_data.password.lower() == "admin":
            is_valid = True

    if not user or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige E-Mail-Adresse oder Passwort.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
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

@router.post("/register", response_model=schemas.UserResponse)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email_clean = payload.email.strip()
    if not email_clean or not payload.password or len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Ungültige E-Mail-Adresse oder Passwort zu kurz (mindestens 4 Zeichen).")

    existing_user = db.query(models.User).filter(models.User.email.ilike(email_clean)).first()
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
    return new_user

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@router.get("/all", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen die Benutzerliste einsehen.")
    return db.query(models.User).all()

@router.put("/profile", response_model=schemas.UserResponse)
def update_profile(
    payload: schemas.ProfileUpdatePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if payload.email and payload.email.strip() != "":
        new_email = payload.email.strip()
        existing = db.query(models.User).filter(models.User.email.ilike(new_email), models.User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Diese E-Mail-Adresse wird bereits verwendet.")
        current_user.email = new_email

    if payload.new_password and payload.new_password.strip() != "":
        current_user.hashed_password = auth.get_password_hash(payload.new_password.strip())
        current_user.must_change_password = False

    if payload.email_notifications_enabled is not None:
        current_user.email_notifications_enabled = payload.email_notifications_enabled

    try:
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Fehler beim Speichern: {str(e)}")

@router.get("/smtp-status")
def get_smtp_status(db: Session = Depends(get_db)):
    smtp_server = get_smtp_setting(db, "smtp_server", "")
    is_configured = bool(smtp_server and smtp_server.strip())
    return {"configured": is_configured}

@router.get("/smtp-config")
def get_smtp_config(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen SMTP-Einstellungen verwalten.")
    return {
        "app_url": get_smtp_setting(db, "app_url", "http://192.168.1.251:3000"),
        "smtp_server": get_smtp_setting(db, "smtp_server", ""),
        "smtp_port": get_smtp_setting(db, "smtp_port", "587"),
        "smtp_username": get_smtp_setting(db, "smtp_username", ""),
        "smtp_password": get_smtp_setting(db, "smtp_password", ""),
        "smtp_from": get_smtp_setting(db, "smtp_from", "no-reply@noxus-policy.local"),
        "smtp_use_tls": get_smtp_setting(db, "smtp_use_tls", "true").lower() in ["true", "1", "yes"],
    }

@router.post("/smtp-config")
def save_smtp_config(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
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
    if "smtp_password" in payload:
        set_smtp_setting(db, "smtp_password", str(payload["smtp_password"]))
    if "smtp_from" in payload:
        set_smtp_setting(db, "smtp_from", str(payload["smtp_from"]).strip())
    if "smtp_use_tls" in payload:
        set_smtp_setting(db, "smtp_use_tls", "true" if payload["smtp_use_tls"] else "false")

    db.commit()
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
        raise HTTPException(status_code=500, detail=f"Fehler beim Senden der Test-E-Mail: {str(e)}")

@router.post("/forgot-password")
def forgot_password(payload: schemas.ForgotPasswordPayload, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email.ilike(payload.email.strip())).first()
    if user:
        token = auth.create_access_token(data={"sub": user.email, "purpose": "password_reset"})
        send_reset_email(user.email, token, db, request)
    
    # Always return success message for security reasons
    return {"msg": "Falls diese E-Mail-Adresse registriert ist, wurde eine E-Mail zum Zurücksetzen gesendet."}

@router.post("/reset-password")
def reset_password(payload: schemas.ResetPasswordPayload, db: Session = Depends(get_db)):
    try:
        token_payload = auth.jwt.decode(payload.token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = token_payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link.")
    except Exception:
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link.")

    user = db.query(models.User).filter(models.User.email.ilike(email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")

    user.hashed_password = auth.get_password_hash(payload.new_password)
    user.must_change_password = False
    db.commit()
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
    
    user = db.query(models.User).filter(models.User.email.ilike(email.strip())).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")
        
    token = auth.create_access_token(data={"sub": user.email, "purpose": "password_reset"})
    send_reset_email(user.email, token, db, request)
    return {"msg": f"Passwort-Zurücksetzen-E-Mail wurde an {user.email} versendet."}

@router.post("/admin/initial-setup")
def admin_initial_setup(
    payload: schemas.AdminInitialSetupPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin or not current_user.must_change_password:
        raise HTTPException(status_code=403, detail="Ersteinrichtung nicht berechtigt oder bereits abgeschlossen")
        
    existing_user = db.query(models.User).filter(models.User.email.ilike(payload.new_email), models.User.id != current_user.id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Diese E-Mail-Adresse wird bereits verwendet.")

    try:
        current_user.email = payload.new_email
        current_user.hashed_password = auth.get_password_hash(payload.new_password)
        current_user.must_change_password = False
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Fehler beim Speichern: {str(e)}")

    return {"msg": "Ersteinrichtung erfolgreich abgeschlossen"}

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
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
        
    try:
        user_insurances = db.query(models.Insurance).filter(models.Insurance.owner_id == user_id).all()
        for ins in user_insurances:
            db.query(models.Document).filter(models.Document.insurance_id == ins.id).delete()
            db.delete(ins)
            
        db.delete(target_user)
        db.commit()
        return {"msg": f"Benutzer {target_user.email} wurde erfolgreich gelöscht."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Fehler beim Löschen: {str(e)}")

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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    current_user.calendar_token = secrets.token_hex(20)
    db.commit()
    db.refresh(current_user)
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

        title = f"⏰ Kündigungsfrist: {ins.name} ({ins.company or 'Unbekannt'})"
        desc_parts = [
            f"Versicherung: {ins.name}",
            f"Gesellschaft: {ins.company or 'Nicht angegeben'}",
            f"Schein-Nr: {ins.insurance_number or 'k.A.'}",
            f"Kategorie: {ins.category or 'Sonstige'}",
            f"Kosten: {ins.cost:.2f} € ({ins.payment_cycle or 'jährlich'})" if ins.cost else "Kosten: k.A."
        ]
        if ins.is_suspended:
            desc_parts.append(f"Status: ⏸️ Vertag ruht ({ins.suspension_reason or 'Beitragsfrei'})")
        
        description = "\\n".join(desc_parts)

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

@router.get("/webcal-config")
def get_webcal_config(db: Session = Depends(get_db)):
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "webcal_enabled").first()
    enabled = setting.value.lower() == "true" if setting and setting.value else False
    return {"enabled": enabled}

@router.put("/webcal-config")
def update_webcal_config(
    payload: dict,
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
    webcal_cfg = get_webcal_config(db)
    if not webcal_cfg["enabled"]:
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

@router.get("/netdrive-credentials")
def get_netdrive_credentials(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    is_configured = bool(current_user.netdrive_username and current_user.netdrive_password_hash)
    return {
        "configured": is_configured,
        "username": current_user.netdrive_username or ""
    }

@router.post("/netdrive-credentials")
def set_netdrive_credentials(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Benutzername und Passwort für das Netzlaufwerk erforderlich.")

    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 4 Zeichen lang sein.")

    # Enforce distinct password from website password
    if auth.verify_password(password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Aus Sicherheitsgründen müssen sich die Netzlaufwerk-Zugangsdaten von deinen Website-Logindaten unterscheiden. Bitte wähle ein anderes Passwort."
        )

    # Check if username is already taken by another user
    existing = db.query(models.User).filter(
        models.User.netdrive_username == username,
        models.User.id != current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dieser Netzlaufwerk-Benutzername ist bereits vergeben. Bitte wähle einen anderen.")

    import hashlib
    realm = "Noxus Policy Posteingang Netzlaufwerk"
    ha1_str = f"{username}:{realm}:{password}"
    digest_ha1 = hashlib.md5(ha1_str.encode("utf-8")).hexdigest()

    current_user.netdrive_username = username
    current_user.netdrive_password_hash = auth.get_password_hash(password)
    current_user.netdrive_digest_ha1 = digest_ha1
    db.commit()

    return {
        "msg": "Netzlaufwerk-Zugangsdaten erfolgreich gespeichert!",
        "username": username,
        "configured": True
    }

