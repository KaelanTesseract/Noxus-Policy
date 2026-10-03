# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""A stand-in OpenID provider for tests: RSA key, discovery document, JWKS, token
and userinfo endpoints behind an httpx MockTransport, so the real code path runs
without any network."""

import json
import time
import urllib.parse

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://id.test.example"
CLIENT_ID = "zettelfrieden-test-client"
CLIENT_SECRET = "zettelfrieden-test-secret"
REDIRECT_URI = "https://app.test.example/api/auth/oidc/callback"


class FakeProvider:
    def __init__(self, issuer: str = ISSUER, discovery_issuer: str | None = None):
        self.issuer = issuer
        self.discovery_issuer = discovery_issuer or issuer
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = "test-key-1"
        self.codes: dict[str, dict] = {}           # authorization code -> id token claims
        self.access_tokens: dict[str, dict] = {}   # access token -> userinfo claims
        self.requests: list[httpx.Request] = []
        self.sign_key = self.key                   # tests swap this to forge a signature

    # ------------------------------------------------------------------ tokens
    def base_claims(self, nonce: str, **overrides) -> dict:
        now = int(time.time())
        claims = {
            "iss": self.issuer, "aud": CLIENT_ID, "sub": "user-1", "iat": now, "exp": now + 300,
            "nonce": nonce, "email": "anna@test.example", "email_verified": True, "name": "Anna Test",
        }
        claims.update(overrides)
        return {k: v for k, v in claims.items() if v is not None}

    def make_id_token(self, claims: dict) -> str:
        return jwt.encode(claims, self.sign_key, algorithm="RS256", headers={"kid": self.kid})

    def issue_code(self, claims: dict, userinfo: dict | None = None) -> str:
        code = f"code-{len(self.codes) + 1}"
        self.codes[code] = claims
        if userinfo is not None:
            self.access_tokens[f"at-{code}"] = userinfo
        return code

    # ------------------------------------------------------------------ http
    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            return httpx.Response(200, json={
                "issuer": self.discovery_issuer,
                "authorization_endpoint": f"{self.issuer}/authorize",
                "token_endpoint": f"{self.issuer}/token",
                "jwks_uri": f"{self.issuer}/jwks",
                "userinfo_endpoint": f"{self.issuer}/userinfo",
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            })
        if path == "/jwks":
            public = jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key(), as_dict=True)
            public.update({"kid": self.kid, "use": "sig", "alg": "RS256"})
            return httpx.Response(200, json={"keys": [public]})
        if path == "/token":
            form = dict(urllib.parse.parse_qsl(request.content.decode()))
            claims = self.codes.pop(form.get("code", ""), None)   # authorization codes are single use
            if claims is None or form.get("client_id") != CLIENT_ID or form.get("client_secret") != CLIENT_SECRET \
                    or form.get("redirect_uri") != REDIRECT_URI or not form.get("code_verifier"):
                return httpx.Response(400, json={"error": "invalid_grant"})
            body = {"id_token": self.make_id_token(claims), "token_type": "Bearer", "access_token": f"at-{form['code']}"}
            return httpx.Response(200, json=body)
        if path == "/userinfo":
            token = request.headers.get("authorization", "").removeprefix("Bearer ")
            info = self.access_tokens.get(token)
            return httpx.Response(200, json=info) if info is not None else httpx.Response(401)
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handler))
