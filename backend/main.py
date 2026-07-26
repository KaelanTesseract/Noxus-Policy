# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models
from routers import users, insurances, documents, backup
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal
import auth
import os

from backup_scheduler import start_scheduler_thread

app = FastAPI(title="Versicherungsmanager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(insurances.router)
app.include_router(documents.router)
app.include_router(backup.router)

import threading
import ocr

def preload_ai_model():
    try:
        print("[Startup] Pre-loading Mini-AI model in background...")
        ocr.get_llm()
    except Exception as e:
        print(f"[Startup] AI pre-load notice: {e}")

@app.on_event("startup")
def startup_db_init():
    try:
        Base.metadata.create_all(bind=engine)
        
        # Start background backup scheduler thread
        try:
            start_scheduler_thread()
        except Exception as se:
            print(f"Error starting backup scheduler thread: {se}")

        # Start pre-loading AI model in background
        threading.Thread(target=preload_ai_model, daemon=True).start()
        
        # Auto-migrate missing columns in existing SQLite database
        with engine.connect() as conn:
            # insurances table
            res_ins = conn.execute(text("PRAGMA table_info(insurances)")).fetchall()
            ins_cols = [r[1] for r in res_ins]
            if "category" not in ins_cols:
                conn.execute(text("ALTER TABLE insurances ADD COLUMN category VARCHAR"))
            if "cost" not in ins_cols:
                conn.execute(text("ALTER TABLE insurances ADD COLUMN cost FLOAT"))
            if "payment_cycle" not in ins_cols:
                conn.execute(text("ALTER TABLE insurances ADD COLUMN payment_cycle VARCHAR DEFAULT 'monatlich'"))
            if "coverage_details" not in ins_cols:
                conn.execute(text("ALTER TABLE insurances ADD COLUMN coverage_details VARCHAR"))

            # documents table
            res_doc = conn.execute(text("PRAGMA table_info(documents)")).fetchall()
            doc_cols = [r[1] for r in res_doc]
            if "custom_name" not in doc_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN custom_name VARCHAR"))
            if "doc_type" not in doc_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN doc_type VARCHAR"))

            # users table
            res_usr = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            usr_cols = [r[1] for r in res_usr]
            if "email_notifications_enabled" not in usr_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_notifications_enabled BOOLEAN DEFAULT 1"))

            # insurances table
            res_ins = conn.execute(text("PRAGMA table_info(insurances)")).fetchall()
            ins_cols = [r[1] for r in res_ins]
            if "notes" not in ins_cols:
                conn.execute(text("ALTER TABLE insurances ADD COLUMN notes VARCHAR"))

            conn.commit()
    except Exception as mig_err:
        print(f"Database auto-migration notice: {mig_err}")

    try:
        db = SessionLocal()
        any_admin = db.query(models.User).filter(models.User.is_admin == True).first()
        if not any_admin:
            hashed_password = auth.get_password_hash("admin")
            admin_user = models.User(
                email="Admin",
                hashed_password=hashed_password,
                is_admin=True,
                must_change_password=True
            )
            db.add(admin_user)
            db.commit()
            print("Default 'Admin' user created since no admin account existed.")
        db.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing admin user: {e}")

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
