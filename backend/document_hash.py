# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Recognises a document that was uploaded before.

Scanning the same letter twice (or uploading a file again) is easy to do and fills
the archive with copies - and every copy with a premium would be added to the
premium history again. Each stored document therefore carries the SHA-256 of its
file, and an upload is compared with the documents of the same user. Only the
user's own documents are ever compared, so a hash can never reveal that someone else
holds a file.

The check only warns; the user decides whether to keep both.
"""

import hashlib
import os
import threading
from typing import Optional

from sqlalchemy import or_

import models

DOCUMENTS_DIR = os.path.abspath("documents")
INBOX_DIR = os.path.abspath(os.path.join("documents", "inbox"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicate(db, user_id: int, file_hash: str, exclude_id: Optional[int] = None,
                   only_before_id: Optional[int] = None) -> Optional[dict]:
    """The oldest document of this user with the same file, as a small description for the
    UI, or None. ``only_before_id`` limits the search to documents stored earlier (used in
    the inbox, so that of two copies only the later one is called the duplicate)."""
    if not file_hash:
        return None
    query = (db.query(models.Document)
             .outerjoin(models.Insurance, models.Document.insurance_id == models.Insurance.id)
             .filter(models.Document.file_hash == file_hash,
                     or_(models.Document.owner_id == user_id, models.Insurance.owner_id == user_id)))
    if exclude_id is not None:
        query = query.filter(models.Document.id != exclude_id)
    if only_before_id is not None:
        query = query.filter(models.Document.id < only_before_id)
    found = query.order_by(models.Document.id).first()
    if found is None:
        return None
    insurance = found.insurance
    return {
        "document_id": found.id,
        "name": found.custom_name or found.original_filename,
        "uploaded": found.upload_date.date().isoformat() if found.upload_date else None,
        "insurance_id": found.insurance_id,
        "insurance_name": insurance.name if insurance else None,
        "in_inbox": bool(found.is_inbox),
    }


def stored_path(doc) -> str:
    """Where the file of a stored document lies (inbox folder of the owner, or the archive)."""
    if doc.is_inbox and doc.owner_id is not None:
        inbox_file = os.path.join(INBOX_DIR, str(doc.owner_id), doc.filename or "")
        if os.path.exists(inbox_file):
            return inbox_file
    return os.path.join(DOCUMENTS_DIR, doc.filename or "")


def backfill_missing_hashes(session_factory) -> int:
    """Documents stored before this feature have no hash. Compute it from the files; a missing
    or unreadable file is skipped (and tried again at the next start)."""
    done = 0
    db = session_factory()
    try:
        for doc in db.query(models.Document).filter(models.Document.file_hash.is_(None)).all():
            path = stored_path(doc)
            try:
                if doc.filename and os.path.isfile(path):
                    doc.file_hash = sha256_file(path)
                    done += 1
            except OSError:
                continue
        db.commit()
    finally:
        db.close()
    return done


def start_backfill_thread(session_factory) -> threading.Thread:
    """In the background: a large archive must not delay the start of the app."""
    def run():
        try:
            count = backfill_missing_hashes(session_factory)
            if count:
                print(f"[Duplicate check] {count} existing documents fingerprinted.")
        except Exception as e:  # never let this take the app down
            print(f"[Duplicate check] backfill failed: {e}")

    thread = threading.Thread(target=run, name="document-hash-backfill", daemon=True)
    thread.start()
    return thread
