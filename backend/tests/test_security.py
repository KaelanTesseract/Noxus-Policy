# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Security regression tests: authentication, second factor, access control,
upload/import limits, pattern safety and output escaping. Each one pins down a
weakness that was fixed - if it fails, something re-opened a hole."""

import base64
import io
import json
import os
import time
import zipfile

import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, login


# ----------------------------------------------------------------------------- passwords
@pytest.mark.parametrize("password", [
    "kurz", "password123", "Passwort2024!", "aaaaaaaaaaaa", "ä" * 40,
])
def test_weak_passwords_are_refused(client, make_user, password):
    _, _, headers = make_user()
    assert client.put("/api/users/profile", headers=headers, json={"new_password": password}).status_code == 400


def test_password_equal_to_email_is_refused(client, make_user):
    email, _, headers = make_user()
    assert client.put("/api/users/profile", headers=headers, json={"new_password": email}).status_code == 400


def test_password_change_signs_out_other_sessions_and_hands_back_a_token(client, make_user):
    email, _, old = make_user()
    r = client.put("/api/users/profile", headers=old, json={"new_password": "Neues-Passwort-Sturm-77"})
    assert r.status_code == 200 and "x-refreshed-token" in r.headers
    assert client.get("/api/users/me", headers=old).status_code == 401
    assert client.get("/api/users/me", headers=bearer(r.headers["x-refreshed-token"])).status_code == 200


# ----------------------------------------------------------------------------- login
def test_login_lockout_after_repeated_failures(client, make_user):
    email, _, _ = make_user()
    codes = [login(client, email, "Falsches-Passwort-1").status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429
    assert login(client, email, USER_PASSWORD).status_code == 429  # even the right password is refused while locked


def test_login_is_case_insensitive_but_never_a_wildcard(client, make_user):
    email, _, _ = make_user()
    assert login(client, email.upper(), USER_PASSWORD).status_code == 200
    assert login(client, email[:4] + "%", USER_PASSWORD).status_code == 401


def test_token_purposes_are_not_interchangeable(client, make_user):
    import auth, models
    from database import SessionLocal
    email, _, _ = make_user()
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == email).first()
    reset_token = auth.create_reset_token(user)
    login_token = auth.create_login_token(user)
    db.close()
    assert client.get("/api/users/me", headers=bearer(reset_token)).status_code == 401
    r = client.post("/api/users/reset-password", json={"token": login_token, "new_password": "Irgendein-Passwort-77"})
    assert r.status_code == 400
    r = client.post("/api/users/reset-password", json={"token": reset_token, "new_password": "Irgendein-Passwort-77"})
    assert r.status_code == 200
    r = client.post("/api/users/reset-password", json={"token": reset_token, "new_password": "Noch-ein-Passwort-88"})
    assert r.status_code == 400  # single use


def test_logout_revokes_every_token(client, make_user):
    _, _, headers = make_user()
    assert client.post("/api/users/logout", headers=headers).status_code == 200
    assert client.get("/api/users/me", headers=headers).status_code == 401


def test_forged_and_unsigned_tokens_are_refused(client):
    forged = jwt.encode({"sub": ADMIN_EMAIL, "tv": 0, "exp": int(time.time()) + 600}, "not-the-real-key", algorithm="HS256")
    assert client.get("/api/users/me", headers=bearer(forged)).status_code == 401
    unsigned = jwt.encode({"sub": ADMIN_EMAIL, "exp": int(time.time()) + 600}, None, algorithm="none")
    assert client.get("/api/users/me", headers=bearer(unsigned)).status_code == 401


def test_sliding_session_refreshes_only_near_expiry_and_within_max_age(client):
    import auth
    # the token's version claim must match the one stored for the account
    current_tv = jwt.decode(login(client, ADMIN_EMAIL, ADMIN_PASSWORD).json()["access_token"], auth.SECRET_KEY, algorithms=["HS256"])["tv"]
    def token_tv(remaining, started_ago):
        now = int(time.time())
        return jwt.encode({"sub": ADMIN_EMAIL, "tv": current_tv, "exp": now + remaining, "sat": now - started_ago}, auth.SECRET_KEY, algorithm="HS256")
    assert "x-refreshed-token" in client.get("/api/users/me", headers=bearer(token_tv(200, 600))).headers
    assert "x-refreshed-token" not in client.get("/api/users/me", headers=bearer(token_tv(800, 600))).headers
    assert "x-refreshed-token" not in client.get("/api/users/me", headers=bearer(token_tv(200, 13 * 3600))).headers


# ----------------------------------------------------------------------------- second factor
def test_two_factor_login_flow(client, make_user):
    import totp
    email, password, headers = make_user()
    secret = client.post("/api/users/2fa/setup", headers=headers, json={"password": password}).json()["secret"]
    step = int(time.time() // 30)
    r = client.post("/api/users/2fa/enable", headers=headers, json={"code": totp._code_for_step(secret, step)})
    assert r.status_code == 200
    recovery = r.json()["recovery_codes"]
    assert len(recovery) == 8

    assert login(client, email, password).json() == {"mfa_required": True}
    assert login(client, email, password, "000000").status_code == 401
    assert login(client, email, "Falsches-Passwort-1", totp._code_for_step(secret, step + 1)).status_code == 401
    assert login(client, email, password, totp._code_for_step(secret, step)).status_code == 401  # replay of the enrolment code
    code = totp._code_for_step(secret, step + 1)
    assert "access_token" in login(client, email, password, code).json()
    assert login(client, email, password, code).status_code == 401  # a code works once
    assert "access_token" in login(client, email, password, recovery[0]).json()
    assert login(client, email, password, recovery[0]).status_code == 401  # recovery codes too


def test_two_factor_can_be_reset_only_by_an_admin(client, make_user, admin_headers):
    import totp
    email, password, headers = make_user()
    secret = client.post("/api/users/2fa/setup", headers=headers, json={"password": password}).json()["secret"]
    r = client.post("/api/users/2fa/enable", headers=headers, json={"code": totp._code_for_step(secret, int(time.time() // 30))})
    fresh = bearer(r.headers["x-refreshed-token"])
    uid = client.get("/api/users/me", headers=fresh).json()["id"]
    assert client.post(f"/api/users/2fa/reset/{uid}", headers=fresh).status_code == 403
    assert client.post(f"/api/users/2fa/reset/{uid}", headers=admin_headers).status_code == 200
    assert "access_token" in login(client, email, password).json()


def test_totp_matches_the_rfc_6238_test_vector():
    import totp
    # RFC 6238 appendix B, SHA-1, secret "12345678901234567890", T=59s -> 94287082 (8 digits); last 6 = 287082
    secret = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
    assert totp._code_for_step(secret, 59 // 30) == "287082"


# ----------------------------------------------------------------------------- access control
@pytest.mark.parametrize("path", ["/api/users/smtp-status", "/api/users/webcal-config", "/api/documents/ai-config", "/api/users/me"])
def test_settings_endpoints_require_login(client, path):
    assert client.get(path).status_code == 401


def test_admin_user_list_does_not_leak_calendar_tokens(client, make_user, admin_headers):
    make_user()
    users = client.get("/api/users/all", headers=admin_headers).json()
    assert users and all("calendar_token" not in u and "hashed_password" not in u for u in users)


def test_secrets_are_not_sent_back_to_the_admin_ui(client, admin_headers):
    client.post("/api/users/smtp-config", headers=admin_headers, json={"smtp_server": "mail.example.com", "smtp_password": "sehr-geheim-123"})
    cfg = client.get("/api/users/smtp-config", headers=admin_headers).json()
    assert "smtp_password" not in cfg and cfg["smtp_password_set"] is True
    client.post("/api/backup/config", headers=admin_headers, json={"password": "Ein-Langes-Backup-Passwort"})
    backup_cfg = client.get("/api/backup/config", headers=admin_headers).json()
    assert "password" not in backup_cfg and backup_cfg["password_set"] is True
    assert client.post("/api/backup/config/reveal-password", headers=admin_headers, json={"account_password": "falsch"}).status_code == 403
    r = client.post("/api/backup/config/reveal-password", headers=admin_headers, json={"account_password": ADMIN_PASSWORD})
    assert r.json()["password"] == "Ein-Langes-Backup-Passwort"


def test_short_backup_passwords_are_refused(client, admin_headers):
    assert client.post("/api/backup/export", headers=admin_headers, json={"password": "kurz1234"}).status_code == 400
    assert client.post("/api/backup/config", headers=admin_headers, json={"password": "kurz"}).status_code == 400


def test_audit_log_records_events_for_admins_only(client, make_user, admin_headers):
    email, _, user_headers = make_user()
    login(client, email, "Falsches-Passwort-1")
    assert client.get("/api/users/audit-log", headers=user_headers).status_code == 403
    entries = client.get("/api/users/audit-log?limit=50", headers=admin_headers).json()
    assert any(e["action"] == "login_failed" and e["actor"] == email for e in entries)
    assert "Falsches" not in json.dumps(entries)


# ----------------------------------------------------------------------------- request limits
def test_oversized_bodies_are_rejected_before_processing(client, make_user):
    _, _, headers = make_user()
    big = b"%PDF" + b"0" * (17 * 1024 * 1024)
    r = client.post("/api/inbox/upload", headers=headers, files={"file": ("x.pdf", big, "application/pdf")})
    assert r.status_code == 413
    r = client.post("/api/users/login", content=b"{" + b" " * (3 * 1024 * 1024) + b"}", headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_upload_rejects_wrong_content_and_traversal_names(client, make_user):
    _, _, headers = make_user()
    r = client.post("/api/inbox/upload", headers=headers, files={"file": ("x.pdf", b"not a pdf at all", "application/pdf")})
    assert r.status_code == 400
    r = client.post("/api/inbox/upload", headers=headers, files={"file": ("../../evil.pdf", b"%PDF-1.4 x", "application/pdf")})
    assert r.status_code == 200 and r.json()["original_filename"] == "evil.pdf"


# ----------------------------------------------------------------------------- archives
def _zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return buf.getvalue()


def _encrypt(raw, password="pw-test-123456"):
    salt = os.urandom(16)
    key = base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000).derive(password.encode()))
    return b"NOXUSBK1" + salt + Fernet(key).encrypt(raw)


@pytest.mark.parametrize("name", ["../evil.txt", "/abs/evil.txt", "a/../../evil.txt", "..\\evil.txt"])
def test_archive_with_escaping_paths_is_rejected(tmp_path, name):
    from safe_archive import ArchiveRejected, safe_extract_zip
    archive = tmp_path / "a.zip"
    archive.write_bytes(_zip([("ok.txt", "x"), (name, "x")]))
    with pytest.raises(ArchiveRejected):
        safe_extract_zip(str(archive), str(tmp_path / "out"))
    assert not (tmp_path / "evil.txt").exists()


def test_archive_limits_entry_count_and_unpacked_size(tmp_path):
    from safe_archive import ArchiveRejected, safe_extract_zip
    many = tmp_path / "many.zip"
    many.write_bytes(_zip([(f"f{i}.txt", "") for i in range(30)]))
    with pytest.raises(ArchiveRejected):
        safe_extract_zip(str(many), str(tmp_path / "o1"), max_entries=10)
    bomb = tmp_path / "bomb.zip"
    bomb.write_bytes(_zip([("zeros.bin", bytes(5 * 1024 * 1024))]))
    with pytest.raises(ArchiveRejected):
        safe_extract_zip(str(bomb), str(tmp_path / "o2"), max_unpacked_bytes=1024 * 1024)
    safe_extract_zip(str(bomb), str(tmp_path / "o3"))  # within the default limit it extracts normally
    assert (tmp_path / "o3" / "zeros.bin").stat().st_size == 5 * 1024 * 1024


def test_user_import_sanitises_document_names_and_types(client, make_user):
    email, _, headers = make_user()
    uid = client.get("/api/users/me", headers=headers).json()["id"]
    archive = _zip([
        ("user.json", json.dumps({"email": email})),
        ("insurances.json", json.dumps([{"id": 1, "name": "Vertrag", "company": "X", "end_date": "2030-01-01"}])),
        ("documents.json", json.dumps([
            {"insurance_id": 1, "filename": "../../etc/passwd", "original_filename": "a.pdf"},
            {"insurance_id": 1, "filename": "page.html", "original_filename": "page.html"},
            {"insurance_id": 1, "filename": "fake.pdf", "original_filename": "fake.pdf"},
            {"insurance_id": 1, "filename": "good.pdf", "original_filename": "../../x/Rechnung.pdf"},
        ])),
        ("files/page.html", "<script>1</script>"),
        ("files/fake.pdf", "not a pdf"),
        ("files/good.pdf", b"%PDF-1.4 ok"),
    ])
    r = client.post("/api/backup/import-user", headers=headers, data={"password": "pw-test-123456", "target_user_id": str(uid)},
                    files={"file": ("u.noxususer", _encrypt(archive), "application/octet-stream")})
    assert r.status_code == 200 and r.json()["documents_count"] == 1
    ins_id = client.get("/api/insurances", headers=headers).json()[0]["id"]
    docs = client.get(f"/api/documents/insurance/{ins_id}", headers=headers).json()
    assert [d["original_filename"] for d in docs] == ["Rechnung.pdf"]


# ----------------------------------------------------------------------------- account erasure
def test_deleting_a_user_removes_rows_and_files(client, make_user, admin_headers):
    email, password, headers = make_user()
    uid = client.get("/api/users/me", headers=headers).json()["id"]
    assert client.post("/api/inbox/upload", headers=headers, files={"file": ("brief.pdf", b"%PDF-1.4 hi", "application/pdf")}).status_code == 200
    inbox_dir = os.path.join("documents", "inbox", str(uid))
    assert os.path.isdir(inbox_dir)
    assert client.delete(f"/api/users/{uid}", headers=admin_headers).status_code == 200
    assert not os.path.exists(inbox_dir)
    assert login(client, email, password).status_code == 401


def test_self_deletion_needs_the_password_and_excludes_admins(client, make_user, admin_headers):
    _, password, headers = make_user()
    assert client.post("/api/users/me/delete", headers=headers, json={"password": "falsch"}).status_code == 403
    assert client.post("/api/users/me/delete", headers=admin_headers, json={"password": ADMIN_PASSWORD}).status_code == 400
    assert client.post("/api/users/me/delete", headers=headers, json={"password": password}).status_code == 200
    assert client.get("/api/users/me", headers=headers).status_code == 401


# ----------------------------------------------------------------------------- learned patterns
GOOD_PATTERNS = [
    r"(?i)(?:tarifgruppe|regionalklasse|regio)\s*[:\-]?\s*(?:kfz\-haftpflicht\s*)?(R\d{2}|R\s*\d{1,2})",
    r"Tarifgruppe : Kfz-Haftpflicht ([A-Za-z0-9\-/]+)",
    r"(?i)(?:typklasse|tk)\s*[:\-]?\s*(\d{1,2})",
]
BAD_PATTERNS = [r"(a+)+$(x)?", r"(x+x+)+y(.)", r"((a|aa)+)(b)", r"(a*)*(b)", r"(?=x)(a)", r"(a)\1", r"nogroup", "(", "x" * 400 + "(a)"]


@pytest.mark.parametrize("pattern", GOOD_PATTERNS)
def test_reasonable_learned_patterns_are_accepted(pattern):
    from pattern_safety import is_safe_pattern
    assert is_safe_pattern(pattern)


@pytest.mark.parametrize("pattern", BAD_PATTERNS)
def test_dangerous_learned_patterns_are_rejected(pattern):
    from pattern_safety import is_safe_pattern
    assert not is_safe_pattern(pattern)


def test_pattern_file_is_filtered_and_runs_isolated():
    from pattern_safety import apply_patterns, sanitize_pattern_db
    db = {"vendors": {"huk": {"company_aliases": ["HUK"], "patterns": {
        "regional_class": [GOOD_PATTERNS[0], BAD_PATTERNS[0]], "cost": [GOOD_PATTERNS[0]], "evil": [GOOD_PATTERNS[0]]}}}}
    assert sanitize_pattern_db(db)["vendors"]["huk"]["patterns"] == {"regional_class": [GOOD_PATTERNS[0]]}
    assert apply_patterns("Regionalklasse: R12\nTypklasse: 17", {"regional_class": [GOOD_PATTERNS[0]], "type_class": [GOOD_PATTERNS[2]]}) == {"regional_class": "R12", "type_class": "17"}


def test_learned_lines_are_stored_escaped():
    from pattern_safety import is_safe_pattern
    from sanitizer import extract_safe_anchor_pattern
    import re
    line = "Regionalklasse (Kfz-Haftpflicht) [R5] +*? 12345"
    pattern = extract_safe_anchor_pattern("Kopf\n" + line + "\nEnde", "12345", ["regionalklasse"])
    assert pattern and is_safe_pattern(pattern) and re.search(pattern, line).group(1) == "12345"


# ----------------------------------------------------------------------------- output escaping
def test_ics_text_cannot_inject_calendar_properties():
    from http_utils import ics_text
    escaped = ics_text("Evil\r\nX-INJECT:1;a,b\\c")
    assert "\n" not in escaped and "\r" not in escaped
    assert escaped == "Evil\\nX-INJECT:1\\;a\\,b\\\\c"


def test_content_disposition_survives_hostile_filenames():
    from http_utils import content_disposition
    header = content_disposition("attachment", 'x".pdf\r\nSet-Cookie: a=b')
    assert "\r" not in header and "\n" not in header and header.count('"') == 2
    assert "filename*=UTF-8''" in header


def test_secret_encryption_round_trips_and_reports_unreadable_values():
    import secrets_crypto
    stored = secrets_crypto.encrypt_secret("hunter2-hunter2")
    assert stored.startswith("enc:") and "hunter2" not in stored
    assert secrets_crypto.decrypt_secret(stored) == "hunter2-hunter2"
    assert secrets_crypto.decrypt_secret("enc:not-a-valid-token") == ""
