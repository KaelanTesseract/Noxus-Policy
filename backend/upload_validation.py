# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Shared validation for user-uploaded files (Posteingang + Dokumente).
Previously the client-supplied filename was used unsanitized to build the
on-disk path (directory traversal via e.g. "../../x"), and neither the
extension nor the actual file content was checked against what the upload UI
promises to accept."""

import os

from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # matches the "max. 15MB" the upload UI states

_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


def matches_signature(ext: str, head: bytes) -> bool:
    """True if the first bytes of a file fit the type its extension claims."""
    signatures = _MAGIC_SIGNATURES.get(ext, ())
    return bool(signatures) and any(head.startswith(sig) for sig in signatures)


def sanitize_filename(filename: str) -> str:
    """Strips any directory components so the result can never escape the
    intended upload folder, regardless of what the client sends."""
    name = os.path.basename((filename or "").strip())
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname.")
    return name


def validate_upload(file: UploadFile, filename: str) -> bytes:
    """Checks extension, size and magic bytes, and returns the file's full
    contents (already read - the caller should write these bytes directly
    instead of re-reading file.file)."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Nicht unterstützter Dateityp. Erlaubt: PDF, PNG, JPG.")

    # Read at most one byte more than allowed, so an oversized file is detected
    # without ever holding all of it in memory.
    contents = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="Datei ist leer.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"Datei zu groß (max. {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).")

    if not matches_signature(ext, contents[:16]):
        raise HTTPException(status_code=400, detail="Dateiinhalt passt nicht zur angegebenen Dateiendung.")

    file.file.seek(0)
    return contents
