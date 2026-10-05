# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""The browser-facing SSO flow end to end, against a fake provider."""

import urllib.parse

import pytest

import models, oidc
from conftest import ADMIN_EMAIL, bearer
from oidc_fake import CLIENT_ID, CLIENT_SECRET, ISSUER, FakeProvider

APP_URL = "https://app.test.example"


@pytest.fixture()
def sso(client, admin_headers, monkeypatch):
    """SSO configured against a fake provider; everything restored afterwards."""
    oidc.clear_caches()
    provider = FakeProvider()
    monkeypatch.setattr(oidc, "_own_client", lambda: provider.client())
    r = client.put("/api/users/oidc-config", headers=admin_headers, json={
        "issuer": ISSUER, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "enabled": True, "auto_create": True})
    assert r.status_code == 200
    from database import SessionLocal
    import oidc_settings
    db = SessionLocal()
    oidc_settings.set_setting(db, "app_url", APP_URL)
    db.commit()
    db.close()
    yield provider
    db = SessionLocal()
    db.query(models.SystemSetting).filter(
        models.SystemSetting.key.like("oidc_%") | (models.SystemSetting.key == "password_login_enabled")
        | (models.SystemSetting.key == "app_url")).delete(synchronize_session=False)
    db.commit()
    db.close()
    client.cookies.clear()


def begin(client):
    r = client.get("/api/auth/oidc/login", follow_redirects=False)
    assert r.status_code == 302
    location = urllib.parse.urlparse(r.headers["location"])
    query = dict(urllib.parse.parse_qsl(location.query))
    cookie = r.headers["set-cookie"].split(";")[0].split("=", 1)[1]
    client.cookies.clear()
    return r, query, cookie


def finish(client, provider, query, cookie, state=None, userinfo=None, **claim_overrides):
    claims = provider.base_claims(query["nonce"], **claim_overrides)
    code = provider.issue_code(claims, userinfo)
    return client.get("/api/auth/oidc/callback", params={"code": code, "state": state or query["state"]},
                      headers={"X-OIDC-Flow": cookie}, follow_redirects=False)


def user_by_email(email):
    from database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            db.expunge(user)
        return user
    finally:
        db.close()


def assert_signed_in(response):
    assert response.status_code == 302 and response.headers["location"] == "/sso-done"
    return response.headers["x-refreshed-token"]


def assert_refused(response, code="sso"):
    assert response.status_code == 302 and response.headers["location"] == f"/login?error={code}"
    assert "x-refreshed-token" not in response.headers


def test_login_redirects_to_the_provider_with_a_bound_flow_cookie(client, sso):
    r, query, _ = begin(client)
    assert r.headers["location"].startswith(f"{ISSUER}/authorize?")
    assert query["code_challenge_method"] == "S256" and query["redirect_uri"] == f"{APP_URL}/api/auth/oidc/callback"
    cookie_header = r.headers["set-cookie"].lower()
    assert "httponly" in cookie_header and "samesite=lax" in cookie_header and "path=/api/auth/oidc" in cookie_header


def test_new_sso_user_is_created_as_a_normal_user_and_gets_a_session(client, sso):
    _, query, cookie = begin(client)
    token = assert_signed_in(finish(client, sso, query, cookie, sub="sub-new", email="neu@test.example"))
    me = client.get("/api/users/me", headers=bearer(token)).json()
    assert me["email"] == "neu@test.example" and me["is_admin"] is False and me["oidc_linked"] is True
    # the session token never appears anywhere the browser could read it
    assert token not in str(client.get("/api/users/auth-config").text)


def test_existing_admin_is_linked_by_verified_email_and_stays_admin(client, sso):
    _, query, cookie = begin(client)
    token = assert_signed_in(finish(client, sso, query, cookie, sub="admin-sub", email=ADMIN_EMAIL))
    me = client.get("/api/users/me", headers=bearer(token)).json()
    assert me["email"] == ADMIN_EMAIL and me["is_admin"] is True and me["oidc_linked"] is True
    # cleanup for the other tests
    from database import SessionLocal
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()
    admin.oidc_issuer = admin.oidc_sub = None
    db.commit()
    db.close()


def test_returning_user_is_recognised_by_subject_even_after_an_email_change(client, sso):
    _, query, cookie = begin(client)
    assert_signed_in(finish(client, sso, query, cookie, sub="sub-wander", email="wander@test.example"))
    _, query, cookie = begin(client)
    token = assert_signed_in(finish(client, sso, query, cookie, sub="sub-wander", email="ganz-anders@test.example", email_verified=False))
    assert client.get("/api/users/me", headers=bearer(token)).json()["email"] == "wander@test.example"
    assert user_by_email("ganz-anders@test.example") is None


def test_unverified_email_neither_links_nor_creates(client, sso):
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="sub-x", email=ADMIN_EMAIL, email_verified=False), "sso_unlinked")
    assert user_by_email(ADMIN_EMAIL).oidc_sub is None
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="sub-y", email="unverified@test.example", email_verified=None), "sso_unlinked")
    assert user_by_email("unverified@test.example") is None


def test_missing_email_is_refused(client, sso):
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="sub-z", email=None, email_verified=None), "sso_unlinked")


def test_account_linked_to_another_identity_cannot_be_taken_over_by_email(client, sso):
    _, query, cookie = begin(client)
    assert_signed_in(finish(client, sso, query, cookie, sub="owner-sub", email="owned@test.example"))
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="attacker-sub", email="owned@test.example"), "sso_unlinked")


def test_automatic_creation_can_be_turned_off(client, sso, admin_headers):
    client.put("/api/users/oidc-config", headers=admin_headers, json={"auto_create": False})
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="sub-off", email="nobody@test.example"), "sso_unlinked")
    assert user_by_email("nobody@test.example") is None


def test_wrong_state_or_missing_flow_is_refused(client, sso):
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, state="forged-state", sub="s1", email="a1@test.example"))
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, "", sub="s2", email="a2@test.example"))
    _, query, _ = begin(client)
    other_cookie = oidc.pack_flow(oidc.new_flow())  # a flow started by someone else
    assert_refused(finish(client, sso, query, other_cookie, sub="s3", email="a3@test.example"))
    assert all(user_by_email(f"a{i}@test.example") is None for i in (1, 2, 3))


def test_provider_error_and_bad_token_are_refused_generically(client, sso):
    _, query, cookie = begin(client)
    r = client.get("/api/auth/oidc/callback", params={"error": "access_denied", "state": query["state"]},
                   headers={"X-OIDC-Flow": cookie}, follow_redirects=False)
    assert_refused(r)
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="s4", email="a4@test.example", aud="someone-else"))
    assert user_by_email("a4@test.example") is None


def test_callback_cannot_be_replayed(client, sso):
    _, query, cookie = begin(client)
    code = sso.issue_code(sso.base_claims(query["nonce"], sub="sub-replay", email="replay@test.example"))
    params, headers = {"code": code, "state": query["state"]}, {"X-OIDC-Flow": cookie}
    assert_signed_in(client.get("/api/auth/oidc/callback", params=params, headers=headers, follow_redirects=False))
    # the provider accepts an authorization code only once
    assert_refused(client.get("/api/auth/oidc/callback", params=params, headers=headers, follow_redirects=False))


def test_disabled_sso_refuses_everything(client):
    r = client.get("/api/auth/oidc/login", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/login?error=sso"
    r = client.get("/api/auth/oidc/callback", params={"code": "x", "state": "y"}, headers={"X-OIDC-Flow": "z"}, follow_redirects=False)
    assert_refused(r)


def test_results_are_written_to_the_audit_log(client, sso, admin_headers):
    _, query, cookie = begin(client)
    assert_signed_in(finish(client, sso, query, cookie, sub="sub-audit", email="audit@test.example"))
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="sub-audit2", email="audit2@test.example", email_verified=False), "sso_unlinked")
    entries = client.get("/api/users/audit-log?limit=60", headers=admin_headers).json()
    actions = {e["action"] for e in entries}
    assert {"sso_created", "sso_denied"} <= actions


# ----------------------------------------------------------------------------- explicit linking
def begin_link(client, headers):
    r = client.get("/api/auth/oidc/link", headers=headers, follow_redirects=False)
    assert r.status_code == 302, r.text
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(r.headers["location"]).query))
    cookie = r.headers["set-cookie"].split(";")[0].split("=", 1)[1]
    client.cookies.clear()
    return query, cookie


def assert_link_result(response, outcome):
    assert response.status_code == 302 and response.headers["location"] == f"/settings?sso={outcome}"
    assert "x-refreshed-token" not in response.headers  # linking never changes the session


def test_linking_needs_a_signed_in_user(client, sso):
    assert client.get("/api/auth/oidc/link", follow_redirects=False).status_code == 401


def test_signed_in_user_can_link_an_identity_with_a_different_email(client, sso, make_user):
    email, _, headers = make_user()
    query, cookie = begin_link(client, headers)
    response = finish(client, sso, query, cookie, sub="sub-manual", email="ganz-andere-adresse@test.example")
    assert_link_result(response, "linked")
    # the account kept its own email and now signs in through the provider
    assert user_by_email(email).oidc_sub == "sub-manual"
    assert user_by_email("ganz-andere-adresse@test.example") is None
    _, query, cookie = begin(client)
    token = assert_signed_in(finish(client, sso, query, cookie, sub="sub-manual", email="ganz-andere-adresse@test.example"))
    assert client.get("/api/users/me", headers=bearer(token)).json()["email"] == email


def test_an_identity_that_belongs_to_another_account_cannot_be_linked(client, sso, make_user):
    _, query, cookie = begin(client)
    assert_signed_in(finish(client, sso, query, cookie, sub="sub-taken", email="taken@test.example"))
    email, _, headers = make_user()
    query, cookie = begin_link(client, headers)
    assert_link_result(finish(client, sso, query, cookie, sub="sub-taken", email="taken@test.example"), "error")
    assert user_by_email(email).oidc_sub is None


def test_an_account_that_is_already_linked_is_not_sent_to_the_provider_again(client, sso, make_user):
    email, _, headers = make_user()
    query, cookie = begin_link(client, headers)
    assert_link_result(finish(client, sso, query, cookie, sub="sub-first", email="x@test.example"), "linked")
    again = client.get("/api/auth/oidc/link", headers=headers, follow_redirects=False)
    assert again.status_code == 302 and again.headers["location"] == "/settings?sso=already"
    assert user_by_email(email).oidc_sub == "sub-first"


def test_link_flow_cookie_cannot_be_used_for_a_normal_login_by_someone_else(client, sso, make_user):
    email, _, headers = make_user()
    query, cookie = begin_link(client, headers)
    # a link flow always ends as a link for the account that started it, never as a new session
    response = finish(client, sso, query, cookie, sub="sub-bound", email="bound@test.example")
    assert_link_result(response, "linked")
    assert user_by_email("bound@test.example") is None


def test_app_url_decides_the_redirect_address_and_must_be_a_url(client, admin_headers, sso):
    r = client.put("/api/users/oidc-config", headers=admin_headers, json={"app_url": "https://nexus.test.example/"})
    assert r.status_code == 200
    assert r.json()["app_url"] == "https://nexus.test.example"
    assert r.json()["redirect_uri"] == "https://nexus.test.example/api/auth/oidc/callback"
    assert client.put("/api/users/oidc-config", headers=admin_headers, json={"app_url": "javascript:alert(1)"}).status_code == 400
    assert client.put("/api/users/oidc-config", headers=admin_headers, json={"app_url": "nexus.test.example"}).status_code == 400


def test_technical_failures_stay_generic_while_missing_links_get_advice(client, sso):
    # a forged state is an attack or a broken setup: no hint about accounts
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, state="forged", sub="g1", email="g1@test.example"), "sso")
    # a valid sign-in without a linked account tells the person how to link
    _, query, cookie = begin(client)
    assert_refused(finish(client, sso, query, cookie, sub="g2", email="g2@test.example", email_verified=False), "sso_unlinked")


def test_returning_user_signs_in_even_when_token_has_no_email_and_userinfo_fails(client, sso):
    _, query, cookie = begin(client)
    assert_signed_in(finish(client, sso, query, cookie, sub="sub-quiet", email="quiet@test.example"))
    _, query, cookie = begin(client)
    token = assert_signed_in(finish(client, sso, query, cookie, sub="sub-quiet", email=None, email_verified=None))
    assert client.get("/api/users/me", headers=bearer(token)).json()["email"] == "quiet@test.example"


def test_user_can_unlink_with_password_but_not_with_a_wrong_one_or_without_password_login(client, sso, admin_headers):
    _, query, cookie = begin(client)
    token = assert_signed_in(finish(client, sso, query, cookie, sub="sub-unlink", email=ADMIN_EMAIL))
    headers = bearer(token)
    from conftest import ADMIN_PASSWORD
    assert client.post("/api/auth/oidc/unlink", headers=headers, json={"password": "falsch"}).status_code == 403
    assert user_by_email(ADMIN_EMAIL).oidc_sub == "sub-unlink"

    from database import SessionLocal
    import oidc_settings
    db = SessionLocal()
    oidc_settings.set_setting(db, "password_login_enabled", "false")
    db.commit()
    db.close()
    assert client.post("/api/auth/oidc/unlink", headers=headers, json={"password": ADMIN_PASSWORD}).status_code == 400
    db = SessionLocal()
    oidc_settings.set_setting(db, "password_login_enabled", "true")
    db.commit()
    db.close()

    assert client.post("/api/auth/oidc/unlink", headers=headers, json={"password": ADMIN_PASSWORD}).status_code == 200
    assert user_by_email(ADMIN_EMAIL).oidc_sub is None
    assert client.post("/api/auth/oidc/unlink", headers=headers, json={"password": ADMIN_PASSWORD}).status_code == 400
