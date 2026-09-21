# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import shutil
import zipfile
import json
import base64
import datetime
import tempfile
import uuid

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import models, auth, audit
from database import get_db, engine, SessionLocal
from http_utils import content_disposition
from rate_limit import rate_limiter
from upload_validation import ALLOWED_EXTENSIONS, matches_signature, sanitize_filename
from safe_archive import ArchiveRejected, safe_extract_zip, copy_tree_files
from request_limits import MAX_BACKUP_BODY_BYTES

router = APIRouter(prefix="/api/backup", tags=["backup"])

# Archives contain every user's data, and the password is the only thing protecting
# them once the file leaves the server (PBKDF2 makes guessing slow, not impossible).
MIN_BACKUP_PASSWORD_LENGTH = 12
MAGIC_HEADER = b"NOXUSBK1"
DB_FILE_PATH = os.path.join("data", "versicherungsmanager.db")
DOCUMENTS_DIR = "documents"

def audit_restore(request: Request, actor: str, detail: str) -> None:
    # The database file was just replaced under the request's session, so log through a fresh one.
    with SessionLocal() as audit_db:
        audit.log_event(audit_db, "backup_restored", request, actor=actor, detail=detail)

def require_strong_backup_password(password) -> str:
    cleaned = (password or "").strip()
    if len(cleaned) < MIN_BACKUP_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Bitte gib ein Passwort mit mindestens {MIN_BACKUP_PASSWORD_LENGTH} Zeichen für die Backup-Verschlüsselung an."
        )
    return cleaned

def secret_key_fingerprint() -> str:
    """Short, non-reversible fingerprint of this instance's SECRET_KEY. Stored in the
    backup's manifest so a restore can tell that the stored passwords (SMTP, backup,
    GitHub token) were encrypted with a different key and can no longer be read."""
    import hashlib
    return hashlib.sha256(f"noxus-backup-fingerprint:{auth.SECRET_KEY}".encode()).hexdigest()[:12]

def restore_warnings(manifest_info: dict) -> list:
    fingerprint = manifest_info.get("secret_key_fingerprint") if isinstance(manifest_info, dict) else None
    if fingerprint and fingerprint != secret_key_fingerprint():
        return [
            "Dieses Backup stammt von einer Instanz mit anderem SECRET_KEY. Gespeicherte Passwörter "
            "(SMTP, automatisches Backup, GitHub-Token) können nicht gelesen werden und müssen neu "
            "eingegeben werden. Alle Benutzer müssen sich neu anmelden."
        ]
    return []

def read_backup_upload(file: UploadFile) -> bytes:
    """Reads an uploaded archive, refusing anything above the accepted size
    (the request-size middleware already stops oversized bodies; this keeps the
    endpoint safe on its own)."""
    contents = file.file.read(MAX_BACKUP_BODY_BYTES + 1)
    if len(contents) > MAX_BACKUP_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Die Backup-Datei ist zu groß.")
    return contents

def derive_fernet_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_archive(raw_bytes: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    key = derive_fernet_key(password, salt)
    f = Fernet(key)
    ciphertext = f.encrypt(raw_bytes)
    return MAGIC_HEADER + salt + ciphertext

def decrypt_archive(encrypted_payload: bytes, password: str) -> bytes:
    if not encrypted_payload.startswith(MAGIC_HEADER):
        raise ValueError("Ungültiges Backup-Dateiformat. (Magic Header fehlt)")
    
    payload = encrypted_payload[len(MAGIC_HEADER):]
    if len(payload) < 16:
        raise ValueError("Backup-Datei ist zu kurz oder beschädigt.")
        
    salt = payload[:16]
    ciphertext = payload[16:]
    
    key = derive_fernet_key(password, salt)
    f = Fernet(key)
    try:
        return f.decrypt(ciphertext)
    except InvalidToken:
        raise ValueError("Falsches Passwort oder beschädigte Backup-Datei.")

@router.post("/export")
def export_system_backup(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren können System-Backups erstellen.")
        
    password = require_strong_backup_password(payload.get("password"))

    try:
        # Check counts
        users_count = db.query(models.User).count()
        insurances_count = db.query(models.Insurance).count()
        documents_count = db.query(models.Document).count()

        # Create temporary ZIP file
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "backup.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 1. Add database file if exists
                if os.path.exists(DB_FILE_PATH):
                    zf.write(DB_FILE_PATH, arcname="versicherungsmanager.db")

                # 2. Add documents
                if os.path.exists(DOCUMENTS_DIR):
                    for root, _, files in os.walk(DOCUMENTS_DIR):
                        for file in files:
                            abs_file = os.path.join(root, file)
                            rel_file = os.path.relpath(abs_file, start=DOCUMENTS_DIR)
                            zf.write(abs_file, arcname=os.path.join("documents", rel_file))

                # 3. Add manifest
                manifest = {
                    "app": "Noxus Policy",
                    "version": "1.0",
                    "created_at": datetime.datetime.utcnow().isoformat(),
                    "created_by": current_user.email,
                    "secret_key_fingerprint": secret_key_fingerprint(),
                    "users_count": users_count,
                    "insurances_count": insurances_count,
                    "documents_count": documents_count
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Read raw ZIP bytes
            with open(zip_path, "rb") as f:
                raw_zip_bytes = f.read()

            # Encrypt raw ZIP bytes
            encrypted_bytes = encrypt_archive(raw_zip_bytes, password)

            filename = f"noxus_policy_backup_{datetime.date.today().strftime('%Y-%m-%d')}.noxusbackup"
            
            audit.log_event(db, "backup_exported", request, user=current_user)
            return Response(
                content=encrypted_bytes,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": content_disposition("attachment", filename)
                }
            )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error generating backup: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Erstellen des Backups.")


@router.post("/import")
def import_system_backup(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren können System-Backups wiederherstellen.")

    if not password:
        raise HTTPException(status_code=400, detail="Bitte gib das Entschlüsselungspasswort an.")

    try:
        encrypted_contents = read_backup_upload(file)
        
        # 1. Decrypt Archive
        try:
            raw_zip_bytes = decrypt_archive(encrypted_contents, password.strip())
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        # 2. Extract and restore
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "imported.zip")
            with open(zip_path, "wb") as f:
                f.write(raw_zip_bytes)

            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            try:
                safe_extract_zip(zip_path, extract_dir)
            except ArchiveRejected as ae:
                raise HTTPException(status_code=400, detail=str(ae))

            # Validate manifest
            manifest_path = os.path.join(extract_dir, "manifest.json")
            manifest_info = {}
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as mf:
                        manifest_info = json.load(mf)
                except Exception:
                    pass

            # Close current DB sessions to release file locks
            db.close()

            # 3. Restore Database
            imported_db = os.path.join(extract_dir, "versicherungsmanager.db")
            if os.path.exists(imported_db):
                os.makedirs(os.path.dirname(DB_FILE_PATH), exist_ok=True)
                shutil.copy2(imported_db, DB_FILE_PATH)

            # 4. Restore Documents
            imported_docs = os.path.join(extract_dir, "documents")
            if os.path.exists(imported_docs):
                os.makedirs(DOCUMENTS_DIR, exist_ok=True)
                copy_tree_files(imported_docs, DOCUMENTS_DIR)

            audit_restore(request, current_user.email, "Upload")
            return {
                "msg": "System-Backup erfolgreich wiederhergestellt! Sämtliche Benutzer, Polizzen und Dokumente wurden synchronisiert.",
                "manifest": manifest_info,
                "warnings": restore_warnings(manifest_info)
            }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error restoring backup: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Wiederherstellen des Backups.")

# Automated Backup Configuration & Management Endpoints
from backup_scheduler import get_backup_setting, set_backup_setting, create_automated_backup, run_backup_cleanup, BACKUPS_STORE_DIR

@router.get("/config")
def get_auto_backup_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Backup-Einstellungen verwalten.")

    return {
        "enabled": get_backup_setting(db, "auto_backup_enabled", "false").lower() in ["true", "1", "yes"],
        "interval": get_backup_setting(db, "auto_backup_interval", "daily"),
        "time": get_backup_setting(db, "auto_backup_time", "03:00"),
        # Not sent to the browser; see POST /config/reveal-password for a re-authenticated look.
        "password_set": bool(get_backup_setting(db, "auto_backup_password", "")),
        "retention_days": int(get_backup_setting(db, "auto_backup_retention_days", "14")),
        "retention_count": int(get_backup_setting(db, "auto_backup_retention_count", "10")),
        "last_run": get_backup_setting(db, "auto_backup_last_run", "")
    }

@router.post("/config")
def save_auto_backup_config(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Backup-Einstellungen verwalten.")

    if "enabled" in payload:
        set_backup_setting(db, "auto_backup_enabled", "true" if payload["enabled"] else "false")
    if "interval" in payload:
        set_backup_setting(db, "auto_backup_interval", str(payload["interval"]).strip())
    if "time" in payload:
        set_backup_setting(db, "auto_backup_time", str(payload["time"]).strip())
    # Empty means "keep the current one" - the form is never pre-filled with the secret.
    if payload.get("password"):
        set_backup_setting(db, "auto_backup_password", require_strong_backup_password(payload["password"]))
    if "retention_days" in payload:
        set_backup_setting(db, "auto_backup_retention_days", str(payload["retention_days"]).strip())
    if "retention_count" in payload:
        set_backup_setting(db, "auto_backup_retention_count", str(payload["retention_count"]).strip())

    # Trigger retention cleanup immediately after settings update
    r_days = int(get_backup_setting(db, "auto_backup_retention_days", "14"))
    r_count = int(get_backup_setting(db, "auto_backup_retention_count", "10"))
    run_backup_cleanup(r_days, r_count)
    audit.log_event(db, "backup_config_changed", request, user=current_user)

    return {"msg": "Automatische Backup-Einstellungen erfolgreich gespeichert!"}

@router.post("/config/reveal-password", dependencies=[Depends(rate_limiter(max_calls=5, period_seconds=300))])
def reveal_auto_backup_password(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Shows the automatic-backup password, but only after the admin re-enters their
    own account password. Without the backup password the stored archives are useless
    on a fresh server, so it has to be retrievable - just not by anyone who happens to
    hold (or steal) an open admin session."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Backup-Einstellungen verwalten.")
    if not auth.verify_password(str(payload.get("account_password") or ""), current_user.hashed_password):
        audit.log_event(db, "login_failed", request, user=current_user, detail="Backup-Passwort anzeigen: falsches Passwort")
        raise HTTPException(status_code=403, detail="Das Passwort ist nicht korrekt.")
    audit.log_event(db, "backup_password_revealed", request, user=current_user)
    return {"password": get_backup_setting(db, "auto_backup_password", "")}

@router.get("/list")
def list_stored_backups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen gespeicherte Backups verwalten.")

    os.makedirs(BACKUPS_STORE_DIR, exist_ok=True)
    backups = []
    for f in os.listdir(BACKUPS_STORE_DIR):
        if f.endswith(".noxusbackup"):
            full_path = os.path.join(BACKUPS_STORE_DIR, f)
            stat = os.stat(full_path)
            created_at = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            
            backups.append({
                "filename": f,
                "size_mb": size_mb,
                "size_bytes": stat.st_size,
                "created_at": created_at,
                "type": "Manuell" if f.startswith("manual_") else "Automatisch"
            })

    # Sort newest first
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups

@router.get("/download/{filename}")
def download_stored_backup(
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Backups herunterladen.")

    file_path = os.path.join(BACKUPS_STORE_DIR, sanitize_filename(filename))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Backup-Datei nicht gefunden.")

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=filename
    )

@router.post("/restore-stored/{filename}")
def restore_stored_backup(
    filename: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Backups wiederherstellen.")

    # Without a typed password, use the one this server encrypts its automatic backups with.
    password = payload.get("password") or get_backup_setting(db, "auto_backup_password", "")
    if not password:
        raise HTTPException(status_code=400, detail="Bitte gib das Entschlüsselungs-Passwort an.")

    file_path = os.path.join(BACKUPS_STORE_DIR, sanitize_filename(filename))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Backup-Datei nicht gefunden.")

    with open(file_path, "rb") as f:
        encrypted_contents = f.read()

    try:
        raw_zip_bytes = decrypt_archive(encrypted_contents, password.strip())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "imported.zip")
        with open(zip_path, "wb") as f:
            f.write(raw_zip_bytes)

        extract_dir = os.path.join(tmpdir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            safe_extract_zip(zip_path, extract_dir)
        except ArchiveRejected as ae:
            raise HTTPException(status_code=400, detail=str(ae))

        db.close()

        # Restore DB
        imported_db = os.path.join(extract_dir, "versicherungsmanager.db")
        if os.path.exists(imported_db):
            os.makedirs(os.path.dirname(DB_FILE_PATH), exist_ok=True)
            shutil.copy2(imported_db, DB_FILE_PATH)

        # Restore Docs
        imported_docs = os.path.join(extract_dir, "documents")
        if os.path.exists(imported_docs):
            os.makedirs(DOCUMENTS_DIR, exist_ok=True)
            copy_tree_files(imported_docs, DOCUMENTS_DIR)

        manifest_info = {}
        try:
            with open(os.path.join(extract_dir, "manifest.json"), "r", encoding="utf-8") as mf:
                manifest_info = json.load(mf)
        except Exception:
            pass

    audit_restore(request, current_user.email, filename[:120])
    return {"msg": f"Backup '{filename}' wurde erfolgreich wiederhergestellt!", "warnings": restore_warnings(manifest_info)}

@router.delete("/delete-stored/{filename}")
def delete_stored_backup(
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Backups löschen.")

    file_path = os.path.join(BACKUPS_STORE_DIR, sanitize_filename(filename))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Backup-Datei nicht gefunden.")

    try:
        os.remove(file_path)
        return {"msg": f"Backup-Datei '{filename}' wurde erfolgreich gelöscht."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Löschen der Datei: {str(e)}")

@router.post("/run-now")
def trigger_backup_now(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Backups manuell ausführen.")

    try:
        filename = create_automated_backup(db, is_manual_trigger=True)
        return {"msg": f"Backup wurde erfolgreich sofort auf dem Server erstellt!", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Erstellen des Backups: {str(e)}")


# Single User Export & Import Endpoints
@router.post("/export-user/{user_id}")
def export_user_backup(
    user_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Keine Berechtigung zum Exportieren dieses Benutzers.")

    password = require_strong_backup_password(payload.get("password"))

    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden.")

    try:
        # Get user insurances
        user_insurances = db.query(models.Insurance).filter(models.Insurance.owner_id == target_user.id).all()
        insurance_ids = [ins.id for ins in user_insurances]

        # Get user documents
        user_documents = []
        if insurance_ids:
            user_documents = db.query(models.Document).filter(models.Document.insurance_id.in_(insurance_ids)).all()

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "user_export.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 1. User Profile data
                user_data = {
                    "email": target_user.email,
                    "hashed_password": target_user.hashed_password,
                    "is_admin": target_user.is_admin,
                    "must_change_password": target_user.must_change_password
                }
                zf.writestr("user.json", json.dumps(user_data, indent=2))

                # 2. Insurances data
                insurances_list = []
                for ins in user_insurances:
                    ins_dict = {
                        "id": ins.id,
                        "name": ins.name,
                        "company": ins.company,
                        "insurance_number": ins.insurance_number,
                        "start_date": ins.start_date.isoformat() if ins.start_date else None,
                        "end_date": ins.end_date.isoformat() if ins.end_date else None,
                        "cancellation_date": ins.cancellation_date.isoformat() if ins.cancellation_date else None,
                        "cost": ins.cost,
                        "payment_cycle": ins.payment_cycle,
                        "category": ins.category,
                        "contact_info": ins.contact_info,
                        "notes": ins.notes,
                        "coverage_details": ins.coverage_details
                    }
                    insurances_list.append(ins_dict)
                zf.writestr("insurances.json", json.dumps(insurances_list, indent=2))

                # 3. Documents data & physical files
                documents_list = []
                for doc in user_documents:
                    doc_dict = {
                        "id": doc.id,
                        "insurance_id": doc.insurance_id,
                        "filename": doc.filename,
                        "original_filename": doc.original_filename,
                        "custom_name": doc.custom_name,
                        "doc_type": doc.doc_type,
                        "upload_date": doc.upload_date.isoformat() if doc.upload_date else None
                    }
                    documents_list.append(doc_dict)

                    # Add physical file if exists
                    if doc.filename:
                        phys_path = os.path.join(DOCUMENTS_DIR, doc.filename)
                        if os.path.exists(phys_path):
                            arc_file = os.path.join("files", doc.filename)
                            zf.write(phys_path, arcname=arc_file)

                zf.writestr("documents.json", json.dumps(documents_list, indent=2))

                # 4. Manifest
                manifest = {
                    "app": "Noxus Policy",
                    "export_type": "user",
                    "user_email": target_user.email,
                    "created_at": datetime.datetime.utcnow().isoformat(),
                    "insurances_count": len(user_insurances),
                    "documents_count": len(user_documents)
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            with open(zip_path, "rb") as f:
                raw_zip_bytes = f.read()

            encrypted_bytes = encrypt_archive(raw_zip_bytes, password)

            clean_email = target_user.email.replace("@", "_at_").replace(".", "_")
            filename = f"noxus_user_backup_{clean_email}_{datetime.date.today().strftime('%Y-%m-%d')}.noxususer"

            audit.log_event(db, "user_exported", request, user=current_user, detail=f"Konto: {target_user.email}")
            return Response(
                content=encrypted_bytes,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": content_disposition("attachment", filename)
                }
            )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error exporting user backup: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Exportieren des Benutzers.")


@router.post("/import-user")
def import_user_backup(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(...),
    target_user_id: int = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin and (not target_user_id or current_user.id != target_user_id):
        raise HTTPException(status_code=403, detail="Nur Administratoren können fremde Benutzer importieren.")

    if not password:
        raise HTTPException(status_code=400, detail="Bitte gib das Entschlüsselungs-Passwort an.")

    try:
        encrypted_contents = read_backup_upload(file)

        try:
            raw_zip_bytes = decrypt_archive(encrypted_contents, password.strip())
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "imported_user.zip")
            with open(zip_path, "wb") as f:
                f.write(raw_zip_bytes)

            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            try:
                safe_extract_zip(zip_path, extract_dir)
            except ArchiveRejected as ae:
                raise HTTPException(status_code=400, detail=str(ae))

            # Load user.json
            user_json_path = os.path.join(extract_dir, "user.json")
            if not os.path.exists(user_json_path):
                raise HTTPException(status_code=400, detail="Die Datei scheint kein gültiges Benutzer-Backup zu sein (user.json fehlt).")

            with open(user_json_path, "r", encoding="utf-8") as uf:
                user_data = json.load(uf)

            # Determine destination user
            dest_user = None
            if target_user_id:
                dest_user = db.query(models.User).filter(models.User.id == target_user_id).first()
            elif current_user.is_admin:
                # Find or create user by email
                dest_user = auth.get_user_by_email(db, user_data["email"])
                if not dest_user:
                    dest_user = models.User(
                        email=user_data["email"],
                        hashed_password=user_data["hashed_password"],
                        is_admin=user_data.get("is_admin", False),
                        must_change_password=user_data.get("must_change_password", False)
                    )
                    db.add(dest_user)
                    db.commit()
                    db.refresh(dest_user)
            else:
                dest_user = current_user

            if not dest_user:
                raise HTTPException(status_code=404, detail="Ziel-Benutzer konnte nicht ermittelt werden.")

            # Load insurances.json
            insurances_json_path = os.path.join(extract_dir, "insurances.json")
            ins_id_mapping = {} # old_id -> new_insurance_id
            ins_count = 0

            if os.path.exists(insurances_json_path):
                with open(insurances_json_path, "r", encoding="utf-8") as inf:
                    ins_list = json.load(inf)

                for ins_dict in ins_list:
                    s_date = datetime.date.fromisoformat(ins_dict["start_date"]) if ins_dict.get("start_date") else None
                    e_date = datetime.date.fromisoformat(ins_dict["end_date"]) if ins_dict.get("end_date") else None
                    c_date = datetime.date.fromisoformat(ins_dict["cancellation_date"]) if ins_dict.get("cancellation_date") else None

                    new_ins = models.Insurance(
                        owner_id=dest_user.id,
                        name=ins_dict.get("name", "Unbekannter Vertrag"),
                        company=ins_dict.get("company", "Unbekannt"),
                        insurance_number=ins_dict.get("insurance_number", ""),
                        start_date=s_date,
                        end_date=e_date,
                        cancellation_date=c_date,
                        cost=ins_dict.get("cost", 0.0),
                        payment_cycle=ins_dict.get("payment_cycle", "monatlich"),
                        category=ins_dict.get("category", "Sonstige"),
                        contact_info=ins_dict.get("contact_info", ""),
                        notes=ins_dict.get("notes", ""),
                        coverage_details=ins_dict.get("coverage_details", "")
                    )
                    db.add(new_ins)
                    db.commit()
                    db.refresh(new_ins)

                    ins_id_mapping[ins_dict["id"]] = new_ins.id
                    ins_count += 1

            # Load documents.json
            documents_json_path = os.path.join(extract_dir, "documents.json")
            doc_count = 0

            if os.path.exists(documents_json_path):
                with open(documents_json_path, "r", encoding="utf-8") as df:
                    doc_list = json.load(df)

                os.makedirs(DOCUMENTS_DIR, exist_ok=True)
                for doc_dict in doc_list:
                    old_ins_id = doc_dict.get("insurance_id")
                    new_ins_id = ins_id_mapping.get(old_ins_id)
                    if not new_ins_id:
                        continue

                    # The archive is user-controlled: never let its filenames pick
                    # a path, and hold imported files to the same rules as uploads.
                    old_filename = os.path.basename(str(doc_dict.get("filename") or ""))
                    ext = os.path.splitext(old_filename)[1].lower()
                    extracted_file = os.path.join(extract_dir, "files", old_filename)
                    if (not old_filename or ext not in ALLOWED_EXTENSIONS
                            or not os.path.isfile(extracted_file) or os.path.islink(extracted_file)):
                        continue
                    with open(extracted_file, "rb") as probe:
                        if not matches_signature(ext, probe.read(16)):
                            continue

                    new_filename = f"imp_{uuid.uuid4().hex}{ext}"
                    shutil.copy2(extracted_file, os.path.join(DOCUMENTS_DIR, new_filename))

                    original_name = os.path.basename(str(doc_dict.get("original_filename") or "")) or old_filename
                    new_doc = models.Document(
                        insurance_id=new_ins_id,
                        filename=new_filename,
                        original_filename=original_name,
                        custom_name=doc_dict.get("custom_name", ""),
                        doc_type=doc_dict.get("doc_type", "")
                    )
                    db.add(new_doc)
                    doc_count += 1

                db.commit()

            audit.log_event(db, "user_imported", request, user=current_user, detail=f"Konto: {dest_user.email}")
            return {
                "msg": f"Benutzer '{dest_user.email}' mit {ins_count} Polizzen und {doc_count} Dokumenten erfolgreich importiert!",
                "user_email": dest_user.email,
                "insurances_count": ins_count,
                "documents_count": doc_count
            }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error importing user backup: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Importieren des Benutzers.")


