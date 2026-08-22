# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, DATABASE_URL, SessionLocal, resolve_sqlite_path
import models
from routers import users, insurances, documents, backup, inbox
import auth
import os
import sqlite3

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
app.include_router(inbox.router)

def auto_migrate_sqlite():
    try:
        if "sqlite" in DATABASE_URL:
            db_path = resolve_sqlite_path(DATABASE_URL)

            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # insurances table
                try:
                    cursor.execute("PRAGMA table_info(insurances)")
                    ins_cols = [row[1] for row in cursor.fetchall()]
                    if "category" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN category VARCHAR")
                    if "cost" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN cost FLOAT")
                    if "payment_cycle" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN payment_cycle VARCHAR DEFAULT 'monatlich'")
                    if "coverage_details" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN coverage_details VARCHAR")
                    if "notes" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN notes VARCHAR")
                    if "contact_info" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN contact_info VARCHAR")
                    if "sf_class" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN sf_class VARCHAR")
                    if "regional_class" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN regional_class VARCHAR")
                    if "type_class" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN type_class VARCHAR")
                    if "is_suspended" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN is_suspended BOOLEAN DEFAULT 0")
                    if "suspension_reason" not in ins_cols:
                        cursor.execute("ALTER TABLE insurances ADD COLUMN suspension_reason VARCHAR")
                except Exception as e:
                    print(f"[Auto-Migrate insurances] {e}")

                # documents table
                try:
                    cursor.execute("PRAGMA table_info(documents)")
                    doc_cols = [row[1] for row in cursor.fetchall()]
                    if "custom_name" not in doc_cols:
                        cursor.execute("ALTER TABLE documents ADD COLUMN custom_name VARCHAR")
                    if "doc_type" not in doc_cols:
                        cursor.execute("ALTER TABLE documents ADD COLUMN doc_type VARCHAR")
                    if "file_size" not in doc_cols:
                        cursor.execute("ALTER TABLE documents ADD COLUMN file_size INTEGER")
                    if "is_inbox" not in doc_cols:
                        cursor.execute("ALTER TABLE documents ADD COLUMN is_inbox BOOLEAN DEFAULT 0")
                    if "status" not in doc_cols:
                        cursor.execute("ALTER TABLE documents ADD COLUMN status VARCHAR DEFAULT 'pending'")
                    if "ai_data" not in doc_cols:
                        cursor.execute("ALTER TABLE documents ADD COLUMN ai_data VARCHAR")
                    if "owner_id" not in doc_cols:
                        cursor.execute("ALTER TABLE documents ADD COLUMN owner_id INTEGER")
                except Exception as e:
                    print(f"[Auto-Migrate documents] {e}")

                # users table
                try:
                    cursor.execute("PRAGMA table_info(users)")
                    usr_cols = [row[1] for row in cursor.fetchall()]
                    if "email_notifications_enabled" not in usr_cols:
                        cursor.execute("ALTER TABLE users ADD COLUMN email_notifications_enabled BOOLEAN DEFAULT 1")
                    if "calendar_token" not in usr_cols:
                        cursor.execute("ALTER TABLE users ADD COLUMN calendar_token VARCHAR")
                except Exception as e:
                    print(f"[Auto-Migrate users] {e}")

                # Indexes on foreign key columns (added after initial release; safe to (re-)create)
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS ix_insurances_owner_id ON insurances (owner_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS ix_documents_owner_id ON documents (owner_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS ix_documents_insurance_id ON documents (insurance_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS ix_claims_insurance_id ON claims (insurance_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS ix_premium_history_insurance_id ON premium_history (insurance_id)")
                except Exception as e:
                    print(f"[Auto-Migrate indexes] {e}")

                conn.commit()
                conn.close()
                print("[Auto-Migration] Database schema check completed.")
    except Exception as mig_err:
        print(f"[Auto-Migration] Notice: {mig_err}")

@app.on_event("startup")
def startup_db_init():
    # 1. Create tables first
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Base.metadata.create_all notice: {e}")

    # 2. Auto-migrate missing columns in existing SQLite database via raw sqlite3
    auto_migrate_sqlite()

    # 3. Create default admin if missing
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

    # 4. Start background schedulers AFTER DB initialization
    try:
        start_scheduler_thread()
    except Exception as se:
        print(f"Error starting backup scheduler thread: {se}")

    try:
        from learning import start_daily_pattern_scheduler
        start_daily_pattern_scheduler()
    except Exception as pe:
        print(f"Error starting daily pattern scheduler thread: {pe}")

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
