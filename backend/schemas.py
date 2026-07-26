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

class ForgotPasswordPayload(BaseModel):
    email: str

class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str

class UserResponse(UserBase):
    id: int
    is_admin: bool
    must_change_password: bool
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

class InsuranceCreate(InsuranceBase):
    pass

class InsuranceUpdate(InsuranceBase):
    pass

class InsuranceResponse(InsuranceBase):
    id: int
    owner_id: int
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
    extracted_text: str
    ai_used: Optional[bool] = False
    ai_model: Optional[str] = None
