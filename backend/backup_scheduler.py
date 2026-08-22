# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import os
import time
import datetime
import zipfile
import json
import tempfile
import threading
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from routers.backup import DB_FILE_PATH, DOCUMENTS_DIR, encrypt_archive

BACKUPS_STORE_DIR = os.path.join("data", "backups")

def get_backup_setting(db: Session, key: str, default_val: str = "") -> str:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if setting and setting.value is not None:
        return setting.value
    return default_val

def set_backup_setting(db: Session, key: str, value: str):
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if not setting:
        setting = models.SystemSetting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()

def run_backup_cleanup(retention_days: int, retention_count: int):
    """Deletes backups exceeding retention days or retention count limit."""
    if not os.path.exists(BACKUPS_STORE_DIR):
        return

    files = []
    for f in os.listdir(BACKUPS_STORE_DIR):
        if f.endswith(".noxusbackup"):
            full_p = os.path.join(BACKUPS_STORE_DIR, f)
            files.append({
                "name": f,
                "path": full_p,
                "mtime": os.path.getmtime(full_p)
            })

    # Sort newest first
    files.sort(key=lambda x: x["mtime"], reverse=True)

    # 1. Clean up by retention days
    now = time.time()
    if retention_days > 0:
        cutoff = now - (retention_days * 86400)
        remaining_files = []
        for file_info in files:
            if file_info["mtime"] < cutoff:
                try:
                    os.remove(file_info["path"])
                    print(f"[Backup-Cleanup] Removed old backup file by age limit ({retention_days} days): {file_info['name']}")
                except Exception as e:
                    print(f"[Backup-Cleanup] Error removing {file_info['name']}: {e}")
            else:
                remaining_files.append(file_info)
        files = remaining_files

    # 2. Clean up by retention count limit
    if retention_count > 0 and len(files) > retention_count:
        to_delete = files[retention_count:]
        for file_info in to_delete:
            try:
                os.remove(file_info["path"])
                print(f"[Backup-Cleanup] Removed excess backup file by count limit ({retention_count}): {file_info['name']}")
            except Exception as e:
                print(f"[Backup-Cleanup] Error removing {file_info['name']}: {e}")

def create_automated_backup(db: Session, is_manual_trigger: bool = False) -> str:
    """Executes a full backup, encrypts it, and saves it in data/backups/."""
    os.makedirs(BACKUPS_STORE_DIR, exist_ok=True)

    password = get_backup_setting(db, "auto_backup_password", "")
    if not password:
        password = "NoxusDefaultBackupSecretPassword123!"

    users_count = db.query(models.User).count()
    insurances_count = db.query(models.Insurance).count()
    documents_count = db.query(models.Document).count()

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "backup.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(DB_FILE_PATH):
                zf.write(DB_FILE_PATH, arcname="versicherungsmanager.db")

            if os.path.exists(DOCUMENTS_DIR):
                for root, _, files in os.walk(DOCUMENTS_DIR):
                    for file in files:
                        abs_file = os.path.join(root, file)
                        rel_file = os.path.relpath(abs_file, start=DOCUMENTS_DIR)
                        zf.write(abs_file, arcname=os.path.join("documents", rel_file))

            manifest = {
                "app": "Noxus Policy",
                "version": "1.0",
                "created_at": datetime.datetime.utcnow().isoformat(),
                "type": "manual" if is_manual_trigger else "auto",
                "users_count": users_count,
                "insurances_count": insurances_count,
                "documents_count": documents_count
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        with open(zip_path, "rb") as f:
            raw_zip_bytes = f.read()

        encrypted_bytes = encrypt_archive(raw_zip_bytes, password.strip())

        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        prefix = "manual" if is_manual_trigger else "auto"
        filename = f"{prefix}_backup_{timestamp_str}.noxusbackup"
        target_path = os.path.join(BACKUPS_STORE_DIR, filename)

        with open(target_path, "wb") as f:
            f.write(encrypted_bytes)

    # Run Retention cleanup
    retention_days = int(get_backup_setting(db, "auto_backup_retention_days", "14"))
    retention_count = int(get_backup_setting(db, "auto_backup_retention_count", "10"))
    run_backup_cleanup(retention_days, retention_count)

    set_backup_setting(db, "auto_backup_last_run", datetime.datetime.now().isoformat())
    print(f"[Backup-Scheduler] Successfully created backup file: {filename}")
    return filename


def check_and_run_scheduled_backup():
    """Background check executed periodically."""
    db = SessionLocal()
    try:
        enabled = get_backup_setting(db, "auto_backup_enabled", "false").lower() in ["true", "1", "yes"]
        if not enabled:
            return

        target_time_str = get_backup_setting(db, "auto_backup_time", "03:00")
        interval = get_backup_setting(db, "auto_backup_interval", "daily")
        last_run_str = get_backup_setting(db, "auto_backup_last_run", "")

        now = datetime.datetime.now()
        
        # Parse target time (e.g. 03:00 -> hour 3, minute 0)
        try:
            target_h, target_m = map(int, target_time_str.split(":"))
        except Exception:
            target_h, target_m = 3, 0

        # Determine if run is due
        is_due = False
        if not last_run_str:
            is_due = True
        else:
            try:
                last_run_dt = datetime.datetime.fromisoformat(last_run_str)
                delta_days = (now.date() - last_run_dt.date()).days

                if interval == "daily" and delta_days >= 1:
                    is_due = True
                elif interval == "3days" and delta_days >= 3:
                    is_due = True
                elif interval == "weekly" and delta_days >= 7:
                    is_due = True
                elif interval == "30days" and delta_days >= 30:
                    is_due = True
            except Exception:
                is_due = True

        # Also ensure we are at or past the target time of day
        current_time_minutes = now.hour * 60 + now.minute
        target_time_minutes = target_h * 60 + target_m

        if is_due and current_time_minutes >= target_time_minutes:
            create_automated_backup(db, is_manual_trigger=False)

    except Exception as e:
        print(f"[Backup-Scheduler] Error in check: {e}")
    finally:
        db.close()


def check_and_send_cancellation_notifications():
    """Checks for upcoming cancellation deadlines and sends email notifications to users who opted in."""
    db = SessionLocal()
    try:
        from routers.users import send_email_message, get_smtp_setting
        smtp_server = get_smtp_setting(db, "smtp_server", "")
        if not smtp_server or not smtp_server.strip():
            return

        try:
            users = db.query(models.User).filter(models.User.email_notifications_enabled == True).all()
        except Exception:
            users = db.query(models.User).all()

        today = datetime.date.today()

        for user in users:
            if not user.email or "@" not in user.email:
                continue

            insurances = db.query(models.Insurance).filter(models.Insurance.owner_id == user.id).all()
            upcoming = []
            for ins in insurances:
                if ins.cancellation_date:
                    delta_days = (ins.cancellation_date - today).days
                    if 0 <= delta_days <= 30:
                        upcoming.append((ins, delta_days))

            if upcoming:
                lines = [f"Hallo {user.email},\n\nhier ist deine Fristen-Erinnerung von Noxus Policy:\n"]
                for ins, days in upcoming:
                    company_name = ins.company or "Gesellschaft k.A."
                    lines.append(f"• {ins.name} ({company_name}): Kündigungsfrist am {ins.cancellation_date.strftime('%d.%m.%Y')} (in {days} Tagen)")
                lines.append("\nBitte überprüfe deine Verträge rechtzeitig in deiner Noxus Policy App.\n\nViele Grüße,\nDein Noxus Policy Team")

                content = "\n".join(lines)
                try:
                    send_email_message(user.email, f"⏰ Kündigungsfrist-Erinnerung ({len(upcoming)} Verträge)", content, db)
                    print(f"[Notifier] Sent cancellation reminder email to {user.email}")
                except Exception as ne:
                    print(f"[Notifier] Failed to send email to {user.email}: {ne}")
    except Exception as e:
        print(f"[Notifier] Error checking cancellation notifications: {e}")
    finally:
        db.close()

def start_scheduler_thread():
    def loop():
        print("[Backup-Scheduler] Background scheduler loop started.")
        last_notification_check = 0
        while True:
            try:
                check_and_run_scheduled_backup()

                # Run cancellation notification check once every 24 hours (86400 seconds)
                now = time.time()
                if now - last_notification_check > 86400:
                    check_and_send_cancellation_notifications()
                    last_notification_check = now
            except Exception as e:
                print(f"[Backup-Scheduler] Loop error: {e}")
            time.sleep(60) # Check every 60 seconds

    t = threading.Thread(target=loop, daemon=True)
    t.start()
