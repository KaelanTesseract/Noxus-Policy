# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""OpenID Connect core (authorization code flow with PKCE), kept free of FastAPI
and of the database so it can be tested against a fake provider.

Trust model: the provider URL is configured by an administrator, everything the
provider sends is checked (issuer, audience, signature, expiry, nonce), and the
short-lived flow state that ties a callback to the browser that started it is
signed with the app's SECRET_KEY. OidcError messages are for the audit log only -
callers must show the browser a generic message."""

import base64
import hashlib
import hmac
import secrets
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import httpx
import jwt

import auth

FLOW_LIFETIME_SECONDS = 600
CACHE_SECONDS = 600
HTTP_TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 512 * 1024
SCOPES = "openid email profile"
# Algorithms accepted for ID tokens; "none" and symmetric algorithms never are.
ALLOWED_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512", "EdDSA"]


class OidcError(Exception):
    """Anything that makes a sign-in attempt invalid. The message is for logs."""


@dataclass(frozen=True)
class OidcConfig:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str


@dataclass(frozen=True)
class Flow:
    state: str
    nonce: str
    verifier: str
    # Set when a signed-in user started the flow to link their own account; the callback
    # then binds the provider identity to exactly this user instead of signing anyone in.
    link_user: Optional[int] = None


# ------------------------------------------------------------------------- HTTP helpers
_discovery_cache: dict = {}
_jwks_cache: dict = {}


def clear_caches() -> None:
    _discovery_cache.clear()
    _jwks_cache.clear()


def _own_client() -> httpx.Client:
    return httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False)


def _get_json(client: httpx.Client, url: str, **kwargs) -> dict:
    try:
        response = client.get(url, **kwargs)
    except httpx.HTTPError as e:
        raise OidcError(f"request to {url} failed: {type(e).__name__}")
    if response.status_code != 200 or len(response.content) > MAX_RESPONSE_BYTES:
        raise OidcError(f"unexpected response from {url}: {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        raise OidcError(f"{url} did not return JSON")
    if not isinstance(data, dict):
        raise OidcError(f"{url} did not return a JSON object")
    return data


def _valid_url(value, issuer: str) -> bool:
    parsed = urllib.parse.urlparse(value) if isinstance(value, str) else None
    issuer_scheme = urllib.parse.urlparse(issuer).scheme
    # Plain HTTP only for an issuer that itself is HTTP (a LAN-only setup); an HTTPS
    # issuer may never hand out an HTTP endpoint.
    return bool(parsed and parsed.netloc and parsed.scheme in ("https", "http")
                and (parsed.scheme == "https" or issuer_scheme == "http"))


# ------------------------------------------------------------------------- discovery
def get_discovery(cfg: OidcConfig, client: Optional[httpx.Client] = None) -> dict:
    cached = _discovery_cache.get(cfg.issuer)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]
    if not cfg.issuer.startswith(("https://", "http://")):
        raise OidcError("issuer must be an http(s) URL")

    owns_client = client is None
    client = client or _own_client()
    try:
        doc = _get_json(client, cfg.issuer.rstrip("/") + "/.well-known/openid-configuration")
    finally:
        if owns_client:
            client.close()

    if doc.get("issuer") != cfg.issuer:
        raise OidcError("discovery issuer does not match the configured issuer")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not _valid_url(doc.get(key), cfg.issuer):
            raise OidcError(f"discovery document has no usable {key}")
    methods = doc.get("code_challenge_methods_supported")
    if methods is not None and "S256" not in methods:
        raise OidcError("provider does not support PKCE S256")
    _discovery_cache[cfg.issuer] = (time.time(), doc)
    return doc


# ------------------------------------------------------------------------- flow state
def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def new_flow(link_user: Optional[int] = None) -> Flow:
    return Flow(state=secrets.token_urlsafe(24), nonce=secrets.token_urlsafe(24),
                verifier=secrets.token_urlsafe(48), link_user=link_user)


def pack_flow(flow: Flow) -> str:
    """The value of the short-lived cookie that binds a callback to this browser."""
    payload = {"purpose": "oidc_flow", "st": flow.state, "no": flow.nonce, "cv": flow.verifier,
               "exp": int(time.time()) + FLOW_LIFETIME_SECONDS}
    if flow.link_user is not None:
        payload["lu"] = flow.link_user
    return jwt.encode(payload, auth.SECRET_KEY, algorithm="HS256")


def unpack_flow(value: str) -> Flow:
    try:
        data = jwt.decode(value or "", auth.SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
    except jwt.PyJWTError:
        raise OidcError("flow cookie is invalid")
    if data.get("purpose") != "oidc_flow" or data.get("exp", 0) < time.time():
        raise OidcError("flow cookie is expired or of the wrong kind")
    try:
        link_user = data.get("lu")
        return Flow(state=data["st"], nonce=data["no"], verifier=data["cv"],
                    link_user=link_user if isinstance(link_user, int) else None)
    except KeyError:
        raise OidcError("flow cookie is incomplete")


def states_match(flow: Flow, state_from_query: str) -> bool:
    return hmac.compare_digest(flow.state.encode(), (state_from_query or "").encode())


def authorization_url(cfg: OidcConfig, discovery: dict, flow: Flow) -> str:
    challenge = _b64url(hashlib.sha256(flow.verifier.encode("ascii")).digest())
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "scope": SCOPES,
        "state": flow.state,
        "nonce": flow.nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    endpoint = discovery["authorization_endpoint"]
    return endpoint + ("&" if "?" in endpoint else "?") + query


# ------------------------------------------------------------------------- token exchange
def _signing_key(cfg: OidcConfig, discovery: dict, kid: Optional[str], client: httpx.Client):
    """The provider's key for ``kid``; the key set is cached and refetched once for an unknown kid."""
    for attempt in (0, 1):
        cached = _jwks_cache.get(cfg.issuer)
        if attempt == 1 or not cached or time.time() - cached[0] >= CACHE_SECONDS:
            jwks = _get_json(client, discovery["jwks_uri"])
            _jwks_cache[cfg.issuer] = (time.time(), jwks)
        keys = _jwks_cache[cfg.issuer][1].get("keys", [])
        matching = [k for k in keys if isinstance(k, dict) and (kid is None or k.get("kid") == kid)]
        if matching:
            try:
                return jwt.PyJWK(matching[0]).key
            except jwt.PyJWTError:
                raise OidcError("provider key could not be read")
    raise OidcError("no matching signing key")


def exchange_and_verify(cfg: OidcConfig, discovery: dict, code: str, flow: Flow,
                        client: Optional[httpx.Client] = None) -> dict:
    """Trades the authorization code for tokens and returns the verified ID token claims
    (completed with userinfo for the same subject when the token lacks the email)."""
    owns_client = client is None
    client = client or _own_client()
    try:
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg.redirect_uri,
            "client_id": cfg.client_id,
            "code_verifier": flow.verifier,
        }
        headers = {}
        supported = discovery.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"]
        if "client_secret_post" in supported:
            form["client_secret"] = cfg.client_secret
        else:
            headers["Authorization"] = "Basic " + base64.b64encode(
                f"{urllib.parse.quote(cfg.client_id, safe='')}:{urllib.parse.quote(cfg.client_secret, safe='')}".encode()
            ).decode()
        try:
            response = client.post(discovery["token_endpoint"], data=form, headers=headers)
        except httpx.HTTPError as e:
            raise OidcError(f"token request failed: {type(e).__name__}")
        if response.status_code != 200 or len(response.content) > MAX_RESPONSE_BYTES:
            raise OidcError(f"token endpoint answered {response.status_code}")
        try:
            tokens = response.json()
        except ValueError:
            raise OidcError("token endpoint did not return JSON")
        id_token = tokens.get("id_token") if isinstance(tokens, dict) else None
        if not isinstance(id_token, str):
            raise OidcError("no id_token in the token response")

        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.PyJWTError:
            raise OidcError("id_token is not a JWT")
        if header.get("alg") not in ALLOWED_ALGORITHMS:
            raise OidcError("id_token algorithm is not allowed")
        key = _signing_key(cfg, discovery, header.get("kid"), client)
        try:
            claims = jwt.decode(
                id_token, key, algorithms=ALLOWED_ALGORITHMS, audience=cfg.client_id, issuer=cfg.issuer,
                leeway=60, options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as e:
            raise OidcError(f"id_token rejected: {type(e).__name__}")

        if not hmac.compare_digest(str(claims.get("nonce", "")).encode(), flow.nonce.encode()):
            raise OidcError("nonce mismatch")
        audience = claims.get("aud")
        if isinstance(audience, list) and len(audience) > 1 and claims.get("azp") != cfg.client_id:
            raise OidcError("azp mismatch")

        access_token = tokens.get("access_token")
        if "email" not in claims and isinstance(access_token, str) and _valid_url(discovery.get("userinfo_endpoint"), cfg.issuer):
            try:
                info = _get_json(client, discovery["userinfo_endpoint"], headers={"Authorization": f"Bearer {access_token}"})
            except OidcError:
                # Userinfo only fills gaps. A returning user is recognised by the signed token
                # alone, so a failing userinfo endpoint must not stop the sign-in.
                info = {}
            # Only trust userinfo that is about the very same subject as the signed token.
            if info.get("sub") == claims["sub"]:
                for field in ("email", "email_verified", "name", "preferred_username"):
                    if field in info and field not in claims:
                        claims[field] = info[field]
        return claims
    finally:
        if owns_client:
            client.close()
