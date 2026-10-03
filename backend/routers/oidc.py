# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Browser-facing endpoints of the single sign-on flow.

Both endpoints are plain navigations (the browser is redirected to the provider
and back), so every failure ends in a redirect to the login page with a generic
message; the real reason only goes to the audit log. The finished session is
handed to the Next.js proxy in the X-Refreshed-Token header, exactly like a
password change does - the proxy turns it into the httpOnly session cookie, so
the ID token and the session token never reach page scripts."""

import secrets
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import audit, auth, models, oidc, oidc_settings
from database import get_db
from rate_limit import rate_limiter

router = APIRouter(prefix="/api/auth/oidc", tags=["oidc"])

FLOW_COOKIE = "noxus_oidc"
FLOW_COOKIE_PATH = "/api/auth/oidc"
_limit = rate_limiter(max_calls=20, period_seconds=300)


def _error_redirect() -> RedirectResponse:
    response = RedirectResponse("/login?error=sso", status_code=302)
    response.delete_cookie(FLOW_COOKIE, path=FLOW_COOKIE_PATH)
    return response


def _verified(claims: dict) -> bool:
    flag = claims.get("email_verified")
    return flag is True or (isinstance(flag, str) and flag.lower() == "true")


def resolve_user(db: Session, claims: dict, cfg: oidc.OidcConfig) -> Tuple[Optional[models.User], str]:
    """Maps verified ID token claims to an account.

    Returns (user, event) where event is the audit action for a success
    (sso_login, sso_linked, sso_created) or (None, reason) for a refusal.
    A returning user is recognised by (issuer, sub); the email is only used for the
    very first sign-in, and only when the provider vouches for it."""
    subject = str(claims["sub"])
    user = db.query(models.User).filter(
        models.User.oidc_issuer == cfg.issuer, models.User.oidc_sub == subject).first()
    if user:
        return user, "sso_login"

    email = str(claims.get("email") or "").strip()
    if not email:
        return None, "provider sent no email address"
    if not _verified(claims):
        return None, "email address is not verified by the provider"

    existing = auth.get_user_by_email(db, email)
    try:
        if existing:
            if existing.oidc_sub:
                return None, "account is already linked to a different identity"
            existing.oidc_issuer, existing.oidc_sub = cfg.issuer, subject
            db.commit()
            return existing, "sso_linked"

        if not oidc_settings.auto_create_enabled(db):
            return None, "no account for this email and automatic creation is off"
        created = models.User(
            email=email,
            # Nobody knows this password; the account signs in through SSO.
            hashed_password=auth.get_password_hash(secrets.token_urlsafe(32)),
            is_admin=False,
            must_change_password=False,
            oidc_issuer=cfg.issuer,
            oidc_sub=subject,
        )
        db.add(created)
        db.commit()
        db.refresh(created)
        return created, "sso_created"
    except IntegrityError:
        db.rollback()
        return None, "account could not be created (conflict)"


@router.get("/login", dependencies=[Depends(_limit)])
def oidc_login(request: Request, db: Session = Depends(get_db)):
    cfg = oidc_settings.load_config(db)
    if cfg is None:
        return _error_redirect()
    try:
        discovery = oidc.get_discovery(cfg)
    except oidc.OidcError as e:
        audit.log_event(db, "sso_denied", request, detail=f"Discovery: {e}"[:250])
        return _error_redirect()

    flow = oidc.new_flow()
    response = RedirectResponse(oidc.authorization_url(cfg, discovery, flow), status_code=302)
    # Lax (not Strict): the callback is a top-level navigation coming from the provider.
    response.set_cookie(
        FLOW_COOKIE, oidc.pack_flow(flow), max_age=oidc.FLOW_LIFETIME_SECONDS, httponly=True,
        samesite="lax", secure=cfg.redirect_uri.startswith("https://"), path=FLOW_COOKIE_PATH,
    )
    return response


@router.get("/callback", dependencies=[Depends(_limit)])
def oidc_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    def refuse(reason: str, actor: Optional[str] = None) -> RedirectResponse:
        audit.log_event(db, "sso_denied", request, actor=actor, detail=reason[:250])
        return _error_redirect()

    cfg = oidc_settings.load_config(db)
    if cfg is None:
        return refuse("SSO is not enabled")

    try:
        # The Next.js proxy forwards the flow cookie in this header (it does not pass cookies on).
        flow = oidc.unpack_flow(request.headers.get("x-oidc-flow", ""))
        if error:
            raise oidc.OidcError(f"provider reported an error: {error[:60]}")
        if not code or not oidc.states_match(flow, state or ""):
            raise oidc.OidcError("state mismatch or missing code")
        discovery = oidc.get_discovery(cfg)
        claims = oidc.exchange_and_verify(cfg, discovery, code, flow)
    except oidc.OidcError as e:
        return refuse(str(e))

    user, event = resolve_user(db, claims, cfg)
    if user is None:
        return refuse(event, actor=str(claims.get("email") or "")[:120] or None)

    audit.log_event(db, event, request, user=user, detail=None if event == "sso_login" else "Provider: " + cfg.issuer[:100])
    response = RedirectResponse("/sso-done", status_code=302)
    response.headers["X-Refreshed-Token"] = auth.create_login_token(user)
    response.delete_cookie(FLOW_COOKIE, path=FLOW_COOKIE_PATH)
    return response
