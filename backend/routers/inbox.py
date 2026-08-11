# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
import json
import datetime

import models, schemas, auth, ocr
from database import get_db

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

INBOX_BASE_DIR = os.path.abspath("documents/inbox")
PERMANENT_DOCS_DIR = os.path.abspath("documents")
os.makedirs(INBOX_BASE_DIR, exist_ok=True)
os.makedirs(PERMANENT_DOCS_DIR, exist_ok=True)

class AssignPayload(BaseModel):
    insurance_id: int
    custom_name: Optional[str] = None
    doc_type: Optional[str] = None

class CreateInsurancePayload(BaseModel):
    name: str
    company: str
    insurance_number: Optional[str] = ""
    category: Optional[str] = None
    cost: Optional[float] = 0.0
    payment_cycle: Optional[str] = "monatlich"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    cancellation_date: Optional[str] = None
    notes: Optional[str] = None
    sf_class: Optional[str] = None
    regional_class: Optional[str] = None
    type_class: Optional[str] = None

def get_file_path_for_inbox_doc(doc: models.Document) -> str:
    user_inbox_dir = os.path.join(INBOX_BASE_DIR, str(doc.owner_id))
    inbox_file = os.path.join(user_inbox_dir, doc.filename)
    if os.path.exists(inbox_file):
        return inbox_file
    
    perm_file = os.path.join(PERMANENT_DOCS_DIR, doc.filename)
    if os.path.exists(perm_file):
        return perm_file

    return inbox_file

@router.get("", response_model=List[schemas.DocumentResponse])
def get_inbox_documents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    docs = db.query(models.Document).filter(
        models.Document.owner_id == current_user.id,
        models.Document.is_inbox == True
    ).order_by(models.Document.upload_date.desc()).all()
    return docs

@router.post("/upload", response_model=schemas.DocumentResponse)
def upload_to_inbox(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    user_inbox_dir = os.path.join(INBOX_BASE_DIR, str(current_user.id))
    os.makedirs(user_inbox_dir, exist_ok=True)

    safe_filename = file.filename
    target_path = os.path.join(user_inbox_dir, safe_filename)

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(target_path)

    doc = models.Document(
        filename=safe_filename,
        original_filename=file.filename,
        custom_name=os.path.splitext(file.filename)[0],
        doc_type="Posteingang",
        upload_date=datetime.datetime.utcnow(),
        file_size=file_size,
        is_inbox=True,
        status="pending",
        owner_id=current_user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@router.post("/{doc_id}/analyze")
def analyze_inbox_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.owner_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    file_path = get_file_path_for_inbox_doc(doc)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Datei auf dem Server nicht gefunden.")

    extracted_text = ocr.extract_text_from_file(file_path)
    extracted_data = ocr.extract_insurance_data(extracted_text, db=db)
    extracted_data["extracted_text"] = extracted_text

    doc.ai_data = json.dumps(extracted_data)
    doc.status = "analyzed"
    db.commit()

    return {"doc_id": doc.id, "status": "analyzed", "ai_data": extracted_data}

@router.post("/{doc_id}/assign")
def assign_inbox_document(
    doc_id: int,
    payload: AssignPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.owner_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    insurance = db.query(models.Insurance).filter(
        models.Insurance.id == payload.insurance_id,
        models.Insurance.owner_id == current_user.id
    ).first()
    if not insurance:
        raise HTTPException(status_code=404, detail="Ziel-Versicherung nicht gefunden.")

    old_file_path = get_file_path_for_inbox_doc(doc)
    new_file_path = os.path.join(PERMANENT_DOCS_DIR, doc.filename)

    # Move file from inbox folder to permanent documents folder
    if os.path.exists(old_file_path) and old_file_path != new_file_path:
        try:
            shutil.move(old_file_path, new_file_path)
        except Exception as e:
            print(f"[Assign Document Move Notice] {e}")

    doc.insurance_id = insurance.id
    doc.is_inbox = False
    doc.status = "assigned"
    if payload.custom_name:
        doc.custom_name = payload.custom_name
    if payload.doc_type:
        doc.doc_type = payload.doc_type

    db.commit()
    return {"msg": "Dokument erfolgreich zugewiesen!", "document_id": doc.id, "insurance_id": insurance.id}

@router.post("/{doc_id}/create-insurance")
def create_insurance_and_assign(
    doc_id: int,
    payload: CreateInsurancePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.owner_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    # Parse dates if string
    start_d = datetime.datetime.strptime(payload.start_date, "%Y-%m-%d").date() if payload.start_date else None
    end_d = datetime.datetime.strptime(payload.end_date, "%Y-%m-%d").date() if payload.end_date else None
    canc_d = datetime.datetime.strptime(payload.cancellation_date, "%Y-%m-%d").date() if payload.cancellation_date else None

    new_insurance = models.Insurance(
        name=payload.name,
        company=payload.company,
        insurance_number=payload.insurance_number or "",
        category=payload.category,
        cost=payload.cost or 0.0,
        payment_cycle=payload.payment_cycle or "monatlich",
        start_date=start_d,
        end_date=end_d,
        cancellation_date=canc_d,
        notes=payload.notes,
        sf_class=payload.sf_class,
        regional_class=payload.regional_class,
        type_class=payload.type_class,
        owner_id=current_user.id
    )
    db.add(new_insurance)
    db.commit()
    db.refresh(new_insurance)

    old_file_path = get_file_path_for_inbox_doc(doc)
    new_file_path = os.path.join(PERMANENT_DOCS_DIR, doc.filename)

    # Move file from inbox folder to permanent documents folder
    if os.path.exists(old_file_path) and old_file_path != new_file_path:
        try:
            shutil.move(old_file_path, new_file_path)
        except Exception as e:
            print(f"[Create Insurance Move Notice] {e}")

    doc.insurance_id = new_insurance.id
    doc.is_inbox = False
    doc.status = "assigned"
    db.commit()

    return {"msg": "Versicherung erstellt und Dokument zugewiesen!", "insurance_id": new_insurance.id, "document_id": doc.id}

@router.delete("/{doc_id}")
def delete_inbox_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.owner_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    file_path = get_file_path_for_inbox_doc(doc)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"[Delete Inbox File Notice] {e}")

    db.delete(doc)
    db.commit()
    return {"msg": "Dokument gelöscht."}

@router.get("/{doc_id}/file")
def get_inbox_document_file(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.owner_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    file_path = get_file_path_for_inbox_doc(doc)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Datei auf dem Server nicht gefunden.")

    return FileResponse(file_path, filename=doc.original_filename or doc.filename)
