# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/versicherungsmanager.db")

def resolve_sqlite_path(database_url: str) -> str:
    """Extract the filesystem path from a sqlite:// DATABASE_URL, or None if not sqlite."""
    if "sqlite" not in database_url:
        return None
    if database_url.startswith("sqlite:////"):
        return "/" + database_url[11:]
    if database_url.startswith("sqlite:///"):
        return database_url[9:]
    return "data/versicherungsmanager.db"

if "sqlite" in DATABASE_URL:
    db_path = resolve_sqlite_path(DATABASE_URL)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception:
            pass

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
