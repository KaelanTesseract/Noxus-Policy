# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os

from database import get_db
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
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
MIN_PASSWORD_LENGTH = 8

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")

def validate_password_strength(password: Optional[str]):
    """Raises HTTPException(400) if the password doesn't meet the minimum bar.
    Applied everywhere a password is set (register, reset, admin setup, profile
    change) - previously only registration checked length, and only >= 4 chars."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Passwort zu kurz (mindestens {MIN_PASSWORD_LENGTH} Zeichen)."
        )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not plain_password or not hashed_password:
            return False
        
        plain_bytes = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
        hash_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        
        if bcrypt.checkpw(plain_bytes, hash_bytes):
            return True
            
        if isinstance(plain_password, str) and plain_password != plain_password.lower():
            plain_lower_bytes = plain_password.lower().encode('utf-8')
            if bcrypt.checkpw(plain_lower_bytes, hash_bytes):
                return True
            
        return False
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8') if isinstance(hashed, bytes) else hashed

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
        
    user = db.query(models.User).filter(models.User.email.ilike(email)).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    return current_user
