# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""SSO settings, the public auth-config and the switch that turns the password
login off."""

import pytest

from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, login
from oidc_fake import CLIENT_ID, CLIENT_SECRET, ISSUER

FULL = {"issuer": ISSUER, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "enabled": True, "auto_create": True}


def link_admin(subject):
    import models
    from database import SessionLocal
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()
    admin.oidc_issuer, admin.oidc_sub = (ISSUER, subject) if subject else (None, None)
    db.commit()
    db.close()


@pytest.fixture()
def clean_sso(client, admin_headers):
    """Leaves the instance as it found it: no SSO settings, password login on, admin unlinked."""
    yield
    import models
    from database import SessionLocal
    db = SessionLocal()
    db.query(models.SystemSetting).filter(
        models.SystemSetting.key.like("oidc_%") | (models.SystemSetting.key == "password_login_enabled")
    ).delete(synchronize_session=False)
    db.commit()
    db.close()
    link_admin(None)


def test_auth_config_is_public_and_defaults_to_password_only(client):
    r = client.get("/api/users/auth-config")
    assert r.status_code == 200
    assert r.json() == {"oidc_enabled": False, "oidc_label": "Mit Pocket ID anmelden", "password_login_enabled": True}


def test_oidc_config_needs_an_admin(client, make_user):
    assert client.get("/api/users/oidc-config").status_code == 401
    _, _, headers = make_user()
    assert client.get("/api/users/oidc-config", headers=headers).status_code == 403
    assert client.put("/api/users/oidc-config", headers=headers, json={"enabled": True}).status_code == 403


def test_saved_config_never_returns_the_secret(client, admin_headers, clean_sso):
    r = client.put("/api/users/oidc-config", headers=admin_headers, json={**FULL, "button_label": "Mit Pocket ID"})
    assert r.status_code == 200
    body = r.json()
    assert "client_secret" not in body and body["client_secret_set"] is True
    assert CLIENT_SECRET not in client.get("/api/users/oidc-config", headers=admin_headers).text
    assert body["redirect_uri"].endswith("/api/auth/oidc/callback")
    public = client.get("/api/users/auth-config").json()
    assert public["oidc_enabled"] is True and public["oidc_label"] == "Mit Pocket ID"


def test_empty_secret_keeps_the_stored_one(client, admin_headers, clean_sso):
    client.put("/api/users/oidc-config", headers=admin_headers, json=FULL)
    client.put("/api/users/oidc-config", headers=admin_headers, json={"client_secret": "", "button_label": "Neu"})
    import oidc_settings
    from database import SessionLocal
    db = SessionLocal()
    try:
        assert oidc_settings.get_setting(db, "oidc_client_secret") == CLIENT_SECRET
    finally:
        db.close()


def test_secret_is_encrypted_in_the_database(client, admin_headers, clean_sso):
    client.put("/api/users/oidc-config", headers=admin_headers, json=FULL)
    import models
    from database import SessionLocal
    db = SessionLocal()
    try:
        raw = db.query(models.SystemSetting).filter(models.SystemSetting.key == "oidc_client_secret").first().value
        assert raw.startswith("enc:") and CLIENT_SECRET not in raw
    finally:
        db.close()


def test_issuer_must_be_an_http_url(client, admin_headers, clean_sso):
    assert client.put("/api/users/oidc-config", headers=admin_headers, json={"issuer": "ftp://x"}).status_code == 400
    assert client.put("/api/users/oidc-config", headers=admin_headers, json={"issuer": "javascript:alert(1)"}).status_code == 400


def test_incomplete_config_is_not_offered_on_the_login_page(client, admin_headers, clean_sso):
    client.put("/api/users/oidc-config", headers=admin_headers, json={"enabled": True, "issuer": ISSUER, "client_id": CLIENT_ID, "client_secret": ""})
    assert client.get("/api/users/auth-config").json()["oidc_enabled"] is False


def test_password_login_cannot_be_switched_off_before_sso_is_ready_and_linked(client, admin_headers, clean_sso):
    # not configured at all
    r = client.put("/api/users/oidc-config", headers=admin_headers, json={"password_login_enabled": False})
    assert r.status_code == 400
    # configured, but the admin's own account is not linked yet
    client.put("/api/users/oidc-config", headers=admin_headers, json=FULL)
    r = client.put("/api/users/oidc-config", headers=admin_headers, json={"password_login_enabled": False})
    assert r.status_code == 400
    assert client.get("/api/users/auth-config").json()["password_login_enabled"] is True


def test_switching_password_login_off_blocks_login_and_registration(client, make_user, admin_headers, clean_sso):
    email, password, _ = make_user()
    client.put("/api/users/oidc-config", headers=admin_headers, json=FULL)
    link_admin("admin-sub")
    r = client.put("/api/users/oidc-config", headers=admin_headers, json={"password_login_enabled": False})
    assert r.status_code == 200 and r.json()["password_login_enabled"] is False
    assert client.get("/api/users/auth-config").json()["password_login_enabled"] is False

    assert login(client, email, password).status_code == 403
    assert client.post("/api/users/register", json={"email": "new@test.example", "password": USER_PASSWORD}).status_code == 403
    # an already issued session keeps working
    assert client.get("/api/users/me", headers=admin_headers).status_code == 200

    r = client.put("/api/users/oidc-config", headers=admin_headers, json={"password_login_enabled": True})
    assert r.json()["password_login_enabled"] is True
    assert login(client, email, password).status_code == 200


def test_config_changes_are_written_to_the_audit_log(client, admin_headers, clean_sso):
    client.put("/api/users/oidc-config", headers=admin_headers, json={"button_label": "Audit-Test"})
    actions = [e["action"] for e in client.get("/api/users/audit-log?limit=20", headers=admin_headers).json()]
    assert "oidc_config_changed" in actions


def test_user_response_tells_whether_the_account_is_linked(client, admin_headers, clean_sso):
    assert client.get("/api/users/me", headers=admin_headers).json()["oidc_linked"] is False
    link_admin("sub-x")
    assert client.get("/api/users/me", headers=admin_headers).json()["oidc_linked"] is True
