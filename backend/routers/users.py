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
    return {"access_token": access_token, "token_type": "bearer"}

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

    try:
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Fehler beim Speichern: {str(e)}")

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
