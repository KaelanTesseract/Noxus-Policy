# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import os
import time
import threading
import datetime

from database import SessionLocal
import models

INBOX_BASE_DIR = os.path.abspath("documents/inbox")
os.makedirs(INBOX_BASE_DIR, exist_ok=True)

def scan_inbox_directories():
    """Scan documents/inbox/<user_id>/ and register any unregistered files in SQLite database."""
    if not os.path.exists(INBOX_BASE_DIR):
        return

    db = SessionLocal()
    try:
        user_dirs = [d for d in os.listdir(INBOX_BASE_DIR) if os.path.isdir(os.path.join(INBOX_BASE_DIR, d))]
        for uid_str in user_dirs:
            try:
                user_id = int(uid_str)
            except ValueError:
                continue

            user_dir_path = os.path.join(INBOX_BASE_DIR, uid_str)
            files = [f for f in os.listdir(user_dir_path) if os.path.isfile(os.path.join(user_dir_path, f))]

            for fname in files:
                fpath = os.path.join(user_dir_path, fname)
                file_size = os.path.getsize(fpath)

                # Check if document already exists in DB for this user
                existing = db.query(models.Document).filter(
                    models.Document.owner_id == user_id,
                    models.Document.filename == fname,
                    models.Document.is_inbox == True
                ).first()

                if not existing:
                    new_doc = models.Document(
                        filename=fname,
                        original_filename=fname,
                        custom_name=os.path.splitext(fname)[0],
                        doc_type="Posteingang",
                        upload_date=datetime.datetime.utcnow(),
                        file_size=file_size,
                        is_inbox=True,
                        status="pending",
                        owner_id=user_id
                    )
                    db.add(new_doc)
                    db.commit()
                    print(f"[Inbox Watcher] Registered new inbox document '{fname}' for user ID {user_id}.")
    except Exception as e:
        print(f"[Inbox Watcher Error] {e}")
        db.rollback()
    finally:
        db.close()

def start_inbox_watcher_thread(interval_seconds=3):
    """Start background watcher thread."""
    def run_loop():
        print(f"[Inbox Watcher] Background scanner started (interval: {interval_seconds}s)...")
        while True:
            try:
                scan_inbox_directories()
            except Exception as e:
                print(f"[Inbox Watcher Loop Error] {e}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    return thread
