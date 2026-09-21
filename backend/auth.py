# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from datetime import datetime, timedelta
from typing import Optional
import time
import jwt
import bcrypt
from fastapi import Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func
from sqlalchemy.orm import Session
import os

from database import get_db
from common_passwords import is_common_password
import models, schemas

_KNOWN_INSECURE_SECRETS = {"changeme123", "changeme", "secret", "your-secret-key", ""}

SECRET_KEY = os.getenv("SECRET_KEY", "")
if SECRET_KEY.lower() in _KNOWN_INSECURE_SECRETS or len(SECRET_KEY) < 16:
    raise RuntimeError(
        "SECRET_KEY is not set (or is a known-insecure/too-short default). "
        "Every JWT is signed with this value, so a shared/guessable key lets "
        "anyone forge a valid login token for any account. Set SECRET_KEY to a "
        "long random value (install.sh/update.sh now generate one automatically "
        "into a local .env file) before starting the backend."
    )

ALGORITHM = "HS256"
# Login and password-reset tokens both live this long. (An earlier constant here
# claimed 7 days but was never used - tokens have always actually expired after
# create_access_token()'s 15-minute default. Kept at 15, now explicit and
# overridable via env for anyone who wants longer sessions.)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
# Sessions slide: while someone keeps working, the backend hands out a fresh
# token (X-Refreshed-Token, which the frontend proxy turns into a new cookie)
# once less than half of the token's lifetime is left - so an idle browser is
# signed out after ACCESS_TOKEN_EXPIRE_MINUTES, but active use isn't interrupted.
# SESSION_MAX_HOURS caps this: after that long since the actual login the user
# has to authenticate again, no matter how active.
SESSION_MAX_HOURS = int(os.getenv("SESSION_MAX_HOURS", "12"))
MIN_PASSWORD_LENGTH = 8
# bcrypt only looks at the first 72 bytes and (in the version we ship) silently
# ignores the rest, so a longer password would give a false sense of security.
MAX_PASSWORD_BYTES = 72

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")

def validate_password_strength(password: Optional[str], email: Optional[str] = None):
    """Raises HTTPException(400) if the password doesn't meet the minimum bar.
    Applied everywhere a password is set (register, reset, admin setup, profile
    change). Besides length it rejects the passwords every attacker tries first
    (offline list, see common_passwords.py), passwords built from the account's
    own email address, and ones that exceed what bcrypt actually uses."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Passwort zu kurz (mindestens {MIN_PASSWORD_LENGTH} Zeichen)."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Passwort zu lang (höchstens {MAX_PASSWORD_BYTES} Bytes; Umlaute und Sonderzeichen zählen mehrfach)."
        )
    folded = password.strip().lower()
    if len(set(folded)) < 3 or is_common_password(password):
        raise HTTPException(status_code=400, detail="Dieses Passwort ist zu leicht zu erraten. Bitte wähle ein anderes.")
    if email:
        local_part = email.strip().lower().split("@")[0]
        if folded == email.strip().lower() or (len(local_part) >= 4 and local_part in folded and len(folded) <= len(local_part) + 4):
            raise HTTPException(status_code=400, detail="Das Passwort darf nicht aus der E-Mail-Adresse bestehen.")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not plain_password or not hashed_password:
            return False
        
        plain_bytes = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
        hash_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8') if isinstance(hashed, bytes) else hashed

# Verified against when a login names an account that doesn't exist, so that
# "unknown user" costs as much time as "wrong password" and response timing
# can't be used to find out which email addresses are registered.
DUMMY_PASSWORD_HASH = get_password_hash("noxus-timing-equalisation-only")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: Optional[str]):
    """Exact, case-insensitive match. The previous ilike(user_input) treated %
    and _ in the input as SQL wildcards, so e.g. a login name of "vict%" matched
    (and could authenticate as) any account starting with "vict"."""
    if not email or not email.strip():
        return None
    return db.query(models.User).filter(func.lower(models.User.email) == email.strip().lower()).first()

# Every token carries the user's token_version ("tv"). Bumping it on the user
# row (password change/reset, logout) invalidates all tokens issued before -
# stateless JWTs otherwise can't be revoked at all. Tokens issued before this
# existed have no "tv" claim and are treated as version 0, which is what every
# existing row defaults to, so nobody is logged out by the upgrade itself.
def create_login_token(user: models.User, session_started_at: Optional[int] = None) -> str:
    return create_access_token({
        "sub": user.email,
        "tv": user.token_version or 0,
        "sat": session_started_at or int(time.time()),
    })

def create_reset_token(user: models.User) -> str:
    return create_access_token({"sub": user.email, "tv": user.token_version or 0, "purpose": "password_reset"})

def revoke_tokens(user: models.User):
    user.token_version = (user.token_version or 0) + 1

def resolve_reset_token(token: str, db: Session) -> models.User:
    """Validates a password-reset token and returns its user. Requires the
    explicit reset purpose - previously any valid login token was accepted here,
    letting a stolen session token reset the password without email access."""
    invalid = HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Link.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise invalid
    if payload.get("purpose") != "password_reset":
        raise invalid
    user = get_user_by_email(db, payload.get("sub"))
    if user is None or payload.get("tv", 0) != (user.token_version or 0):
        raise invalid
    return user

def get_current_user(response: Response, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    # A password-reset token is only good for resetting the password - it must
    # never double as a session token.
    if payload.get("purpose"):
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None or payload.get("tv", 0) != (user.token_version or 0):
        raise credentials_exception

    # Sliding session (see SESSION_MAX_HOURS above).
    now = time.time()
    lifetime = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    started = payload.get("sat") or (payload.get("exp", now) - lifetime)
    if payload.get("exp", 0) - now < lifetime / 2 and now - started < SESSION_MAX_HOURS * 3600:
        response.headers["X-Refreshed-Token"] = create_login_token(user, int(started))
    return user

def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    return current_user
