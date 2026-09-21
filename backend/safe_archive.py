# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Bounded extraction of uploaded ZIP archives.

Backup and user-import archives come from the person uploading them - and the
user import is open to every registered user, who can build such an archive by
hand (the "encryption" only needs a password they choose themselves). A plain
``ZipFile.extractall`` would let them write terabytes to disk with a few
kilobytes of upload (zip bomb) or exhaust the inode table with millions of
empty entries, so extraction here is capped in entry count and unpacked size,
and refuses entries that try to leave the target directory."""

import os
import shutil
import stat
import zipfile

MAX_ARCHIVE_ENTRIES = 50_000
MAX_UNPACKED_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB, four times the largest accepted upload


class ArchiveRejected(ValueError):
    """The archive is unusable or exceeds a safety limit; the message is safe to show to the user."""


def _is_unsafe_name(name: str) -> bool:
    if not name or "\x00" in name or "\\" in name:
        return True
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return True
    return any(part == ".." for part in name.split("/"))


def safe_extract_zip(zip_path: str, dest_dir: str,
                     max_entries: int = MAX_ARCHIVE_ENTRIES,
                     max_unpacked_bytes: int = MAX_UNPACKED_BYTES) -> None:
    try:
        zf = zipfile.ZipFile(zip_path, "r")
    except (zipfile.BadZipFile, OSError):
        raise ArchiveRejected("Entschlüsselte Datei ist kein gültiges ZIP-Archiv.")

    with zf:
        infos = zf.infolist()
        if len(infos) > max_entries:
            raise ArchiveRejected("Das Archiv enthält zu viele Einträge.")

        declared_total = 0
        for info in infos:
            if _is_unsafe_name(info.filename):
                raise ArchiveRejected("Das Archiv enthält ungültige Dateipfade.")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ArchiveRejected("Das Archiv enthält nicht erlaubte Verknüpfungen.")
            declared_total += info.file_size
        if declared_total > max_unpacked_bytes:
            raise ArchiveRejected("Das entpackte Archiv wäre zu groß.")

        dest_root = os.path.realpath(dest_dir)
        written = 0
        for info in infos:
            target = os.path.realpath(os.path.join(dest_root, info.filename))
            if target != dest_root and not target.startswith(dest_root + os.sep):
                raise ArchiveRejected("Das Archiv enthält ungültige Dateipfade.")

            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue

            os.makedirs(os.path.dirname(target), exist_ok=True)
            try:
                with zf.open(info) as src, open(target, "wb") as dst:
                    # Count what really comes out instead of trusting the header.
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > max_unpacked_bytes:
                            raise ArchiveRejected("Das entpackte Archiv wäre zu groß.")
                        dst.write(chunk)
            except (zipfile.BadZipFile, OSError, RuntimeError, EOFError):
                raise ArchiveRejected("Entschlüsselte Datei ist kein gültiges ZIP-Archiv.")


def copy_tree_files(src_root: str, dst_root: str) -> None:
    """Copies every regular file below ``src_root`` into ``dst_root`` (keeping the
    relative layout) and skips anything that is not a plain file."""
    for root, _, files in os.walk(src_root):
        for name in files:
            src = os.path.join(root, name)
            if os.path.islink(src):
                continue
            dst = os.path.join(dst_root, os.path.relpath(src, start=src_root))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
