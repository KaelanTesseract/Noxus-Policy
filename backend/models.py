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
    
    insurances = relationship("Insurance", back_populates="owner")

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
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="insurances")
    
    documents = relationship("Document", back_populates="insurance", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    original_filename = Column(String)
    custom_name = Column(String, nullable=True)
    doc_type = Column(String, nullable=True)
    document_date = Column(Date, nullable=True)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    
    insurance_id = Column(Integer, ForeignKey("insurances.id"), nullable=True)
    insurance = relationship("Insurance", back_populates="documents")
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category")

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)
