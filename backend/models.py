# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, Float
from sqlalchemy.orm import relationship
import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False)
    email_notifications_enabled = Column(Boolean, default=True)
    calendar_token = Column(String, unique=True, index=True, nullable=True)

    insurances = relationship("Insurance", back_populates="owner")
    inbox_documents = relationship("Document", back_populates="owner")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class Insurance(Base):
    __tablename__ = "insurances"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    company = Column(String)
    insurance_number = Column(String)
    category = Column(String, nullable=True)
    cost = Column(Float, nullable=True)
    payment_cycle = Column(String, nullable=True, default="monatlich")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    cancellation_date = Column(Date, nullable=True)
    contact_info = Column(String, nullable=True)
    coverage_details = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    # KFZ Specific Attributes
    sf_class = Column(String, nullable=True)
    regional_class = Column(String, nullable=True)
    type_class = Column(String, nullable=True)
    
    # Ruhend-Stellung (Beitragsfreistellung / Suspension)
    is_suspended = Column(Boolean, default=False)
    suspension_reason = Column(String, nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    owner = relationship("User", back_populates="insurances")

    documents = relationship("Document", back_populates="insurance", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="insurance", cascade="all, delete-orphan")
    premium_history = relationship("PremiumHistory", back_populates="insurance", cascade="all, delete-orphan", order_by="PremiumHistory.effective_date.asc()")

class PremiumHistory(Base):
    __tablename__ = "premium_history"
    id = Column(Integer, primary_key=True, index=True)
    cost = Column(Float, nullable=False)
    payment_cycle = Column(String, nullable=True, default="jährlich")
    annual_cost = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    insurance_id = Column(Integer, ForeignKey("insurances.id"), index=True)
    insurance = relationship("Insurance", back_populates="premium_history")

class Claim(Base):
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String, nullable=True)
    claim_date = Column(Date, nullable=True)
    amount = Column(Float, nullable=True)
    status = Column(String, default="In Bearbeitung")
    description = Column(String, nullable=True)
    
    insurance_id = Column(Integer, ForeignKey("insurances.id"), index=True)
    insurance = relationship("Insurance", back_populates="claims")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    original_filename = Column(String)
    custom_name = Column(String, nullable=True)
    doc_type = Column(String, nullable=True)
    document_date = Column(Date, nullable=True)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    file_size = Column(Integer, nullable=True)
    
    # Posteingang (Inbox) attributes
    is_inbox = Column(Boolean, default=False, index=True)
    status = Column(String, default="pending")  # pending, analyzed, assigned
    ai_data = Column(String, nullable=True)     # JSON string of extracted data
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    owner = relationship("User", back_populates="inbox_documents")

    insurance_id = Column(Integer, ForeignKey("insurances.id"), nullable=True, index=True)
    insurance = relationship("Insurance", back_populates="documents")
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category")

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)
