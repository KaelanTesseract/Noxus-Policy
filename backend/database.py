import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/versicherungsmanager.db")

if "sqlite" in DATABASE_URL:
    if DATABASE_URL.startswith("sqlite:////"):
        db_path = "/" + DATABASE_URL[11:]
    elif DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL[9:]
    else:
        db_path = "data/versicherungsmanager.db"
    
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
