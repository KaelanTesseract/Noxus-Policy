# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# Users
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class AdminInitialSetupPayload(BaseModel):
    new_email: str
    new_password: str

class ProfileUpdatePayload(BaseModel):
    email: Optional[str] = None
    new_password: Optional[str] = None
    email_notifications_enabled: Optional[bool] = None

class ForgotPasswordPayload(BaseModel):
    email: str

class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str

class UserResponse(UserBase):
    id: int
    is_admin: bool
    must_change_password: bool
    email_notifications_enabled: Optional[bool] = True
    calendar_token: Optional[str] = None
    class Config:
        from_attributes = True

# Premium History / Price Adjustments
class PremiumHistoryBase(BaseModel):
    cost: float
    payment_cycle: Optional[str] = "jährlich"
    effective_date: Optional[date] = None
    note: Optional[str] = None

class PremiumHistoryCreate(PremiumHistoryBase):
    pass

class PremiumHistoryResponse(PremiumHistoryBase):
    id: int
    insurance_id: int
    annual_cost: float
    created_at: datetime
    class Config:
        from_attributes = True

# Claims
class ClaimBase(BaseModel):
    claim_number: Optional[str] = None
    claim_date: Optional[date] = None
    amount: Optional[float] = None
    status: Optional[str] = "In Bearbeitung"
    description: Optional[str] = None

class ClaimCreate(ClaimBase):
    pass

class ClaimResponse(ClaimBase):
    id: int
    insurance_id: int
    class Config:
        from_attributes = True

# Insurances
class InsuranceBase(BaseModel):
    name: str
    company: Optional[str] = None
    insurance_number: Optional[str] = None
    category: Optional[str] = None
    cost: Optional[float] = None
    payment_cycle: Optional[str] = "monatlich"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cancellation_date: Optional[date] = None
    contact_info: Optional[str] = None
    coverage_details: Optional[List[str]] = None
    notes: Optional[str] = None
    
    # KFZ Attributes
    sf_class: Optional[str] = None
    regional_class: Optional[str] = None
    type_class: Optional[str] = None
    
    # Ruhend Status
    is_suspended: Optional[bool] = False
    suspension_reason: Optional[str] = None

class InsuranceCreate(InsuranceBase):
    pass

class InsuranceUpdate(InsuranceBase):
    pass

class InsuranceResponse(InsuranceBase):
    id: int
    owner_id: int
    price_change_pct: Optional[float] = None
    claims: Optional[List[ClaimResponse]] = []
    premium_history: Optional[List[PremiumHistoryResponse]] = []
    class Config:
        from_attributes = True

# Documents
class DocumentBase(BaseModel):
    original_filename: str
    custom_name: Optional[str] = None
    doc_type: Optional[str] = None
    document_date: Optional[date] = None
    category_id: Optional[int] = None
    insurance_id: Optional[int] = None

class DocumentResponse(DocumentBase):
    id: int
    filename: str
    upload_date: datetime
    class Config:
        from_attributes = True

class ExtractionResult(BaseModel):
    company: Optional[str] = None
    insurance_number: Optional[str] = None
    category: Optional[str] = None
    doc_type: Optional[str] = None
    suggested_title: Optional[str] = None
    cost: Optional[float] = None
    payment_cycle: Optional[str] = "monatlich"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cancellation_date: Optional[date] = None
    document_date: Optional[date] = None
    coverage_details: Optional[List[str]] = None
    
    # KFZ fields
    sf_class: Optional[str] = None
    regional_class: Optional[str] = None
    type_class: Optional[str] = None
    
    # Beitragsanpassung fields
    is_price_change: Optional[bool] = False
    previous_cost: Optional[float] = None
    new_cost: Optional[float] = None
    
    extracted_text: str
    ai_used: Optional[bool] = False
    ai_model: Optional[str] = None
