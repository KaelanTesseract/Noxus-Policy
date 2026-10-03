# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""OIDC core: discovery, PKCE/state handling and ID token validation, run against
a fake provider (no network)."""

import time
import urllib.parse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import oidc
from oidc_fake import CLIENT_ID, CLIENT_SECRET, ISSUER, REDIRECT_URI, FakeProvider

CONFIG = oidc.OidcConfig(issuer=ISSUER, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI)


@pytest.fixture()
def provider():
    oidc.clear_caches()
    return FakeProvider()


def run_flow(provider, **claim_overrides):
    """Start a flow, let the fake provider issue a code for it, and exchange it."""
    http = provider.client()
    discovery = oidc.get_discovery(CONFIG, http)
    flow = oidc.new_flow()
    url = oidc.authorization_url(CONFIG, discovery, flow)
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    claims = provider.base_claims(query["nonce"], **claim_overrides)
    code = provider.issue_code(claims)
    return oidc.exchange_and_verify(CONFIG, discovery, code, flow, http), url, query


def test_authorization_url_uses_pkce_and_binds_state_and_nonce(provider):
    discovery = oidc.get_discovery(CONFIG, provider.client())
    flow = oidc.new_flow()
    url = oidc.authorization_url(CONFIG, discovery, flow)
    parsed = urllib.parse.urlparse(url)
    q = dict(urllib.parse.parse_qsl(parsed.query))
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == f"{ISSUER}/authorize"
    assert q["response_type"] == "code" and q["client_id"] == CLIENT_ID and q["redirect_uri"] == REDIRECT_URI
    assert q["state"] == flow.state and q["nonce"] == flow.nonce
    assert q["code_challenge_method"] == "S256" and q["code_challenge"] != flow.verifier
    assert set(q["scope"].split()) == {"openid", "email", "profile"}


def test_successful_exchange_returns_verified_claims(provider):
    claims, _, _ = run_flow(provider)
    assert claims["sub"] == "user-1" and claims["email"] == "anna@test.example" and claims["email_verified"] is True


def test_wrong_nonce_is_rejected(provider):
    http = provider.client()
    discovery = oidc.get_discovery(CONFIG, http)
    flow = oidc.new_flow()
    code = provider.issue_code(provider.base_claims("not-the-nonce"))
    with pytest.raises(oidc.OidcError):
        oidc.exchange_and_verify(CONFIG, discovery, code, flow, http)


@pytest.mark.parametrize("override", [
    {"iss": "https://evil.example"},
    {"aud": "someone-else"},
    {"exp": int(time.time()) - 3600},
    {"sub": None},
])
def test_invalid_claims_are_rejected(provider, override):
    with pytest.raises(oidc.OidcError):
        run_flow(provider, **override)


def test_token_signed_with_another_key_is_rejected(provider):
    provider.sign_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(oidc.OidcError):
        run_flow(provider)


def test_unsigned_token_is_rejected(provider):
    http = provider.client()
    discovery = oidc.get_discovery(CONFIG, http)
    flow = oidc.new_flow()
    forged = jwt.encode(provider.base_claims(flow.nonce), key=None, algorithm="none")
    provider.codes["forged"] = {}
    original = provider.make_id_token
    provider.make_id_token = lambda claims: forged
    try:
        with pytest.raises(oidc.OidcError):
            oidc.exchange_and_verify(CONFIG, discovery, "forged", flow, http)
    finally:
        provider.make_id_token = original


def test_unknown_code_is_rejected(provider):
    http = provider.client()
    discovery = oidc.get_discovery(CONFIG, http)
    with pytest.raises(oidc.OidcError):
        oidc.exchange_and_verify(CONFIG, discovery, "nope", oidc.new_flow(), http)


def test_discovery_issuer_must_match_configuration():
    oidc.clear_caches()
    liar = FakeProvider(discovery_issuer="https://other.example")
    with pytest.raises(oidc.OidcError):
        oidc.get_discovery(CONFIG, liar.client())


def test_missing_email_is_filled_from_userinfo_of_the_same_subject(provider):
    http = provider.client()
    discovery = oidc.get_discovery(CONFIG, http)
    flow = oidc.new_flow()
    claims = provider.base_claims(flow.nonce, email=None, email_verified=None)
    code = provider.issue_code(claims, userinfo={"sub": "user-1", "email": "anna@test.example", "email_verified": True})
    result = oidc.exchange_and_verify(CONFIG, discovery, code, flow, http)
    assert result["email"] == "anna@test.example" and result["email_verified"] is True


def test_userinfo_for_a_different_subject_is_ignored(provider):
    http = provider.client()
    discovery = oidc.get_discovery(CONFIG, http)
    flow = oidc.new_flow()
    claims = provider.base_claims(flow.nonce, email=None, email_verified=None)
    code = provider.issue_code(claims, userinfo={"sub": "someone-else", "email": "victim@test.example", "email_verified": True})
    result = oidc.exchange_and_verify(CONFIG, discovery, code, flow, http)
    assert "email" not in result


def test_flow_cookie_round_trip_and_tampering():
    flow = oidc.new_flow()
    restored = oidc.unpack_flow(oidc.pack_flow(flow))
    assert (restored.state, restored.nonce, restored.verifier) == (flow.state, flow.nonce, flow.verifier)
    with pytest.raises(oidc.OidcError):
        oidc.unpack_flow(oidc.pack_flow(flow)[:-3] + "abc")
    with pytest.raises(oidc.OidcError):
        oidc.unpack_flow("")


def test_expired_flow_cookie_is_rejected(monkeypatch):
    flow = oidc.new_flow()
    packed = oidc.pack_flow(flow)
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 3600)
    with pytest.raises(oidc.OidcError):
        oidc.unpack_flow(packed)
