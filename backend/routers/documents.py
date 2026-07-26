# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import json

import models, schemas, auth, ocr
from database import get_db

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = "documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/ai-config")
def get_ai_config(db: Session = Depends(get_db)):
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "use_ai_ocr").first()
    use_ai = True
    if setting and setting.value is not None:
        use_ai = setting.value.lower() in ["true", "1", "yes"]
    return {"use_ai": use_ai}

@router.post("/ai-config")
def set_ai_config(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen die KI-Einstellungen ändern.")

    use_ai = bool(payload.get("use_ai", True))
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "use_ai_ocr").first()
    if not setting:
        setting = models.SystemSetting(key="use_ai_ocr", value="true" if use_ai else "false")
        db.add(setting)
    else:
        setting.value = "true" if use_ai else "false"
    db.commit()

    return {"msg": f"KI-Dokumentenanalyse wurde {'aktiviert' if use_ai else 'deaktiviert (nur klassische OCR)'}!", "use_ai": use_ai}

@router.post("/extract", response_model=schemas.ExtractionResult)
def extract_document_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    temp_filepath = os.path.join(UPLOAD_DIR, f"temp_{file.filename}")
    with open(temp_filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    text = ocr.extract_text_from_file(temp_filepath)
    extracted_data = ocr.extract_insurance_data(text, db=db)
    extracted_data["extracted_text"] = text
    
    if os.path.exists(temp_filepath):
        try:
            os.remove(temp_filepath)
        except:
            pass
            
    return extracted_data

@router.post("", response_model=schemas.DocumentResponse)
def create_document(
    insurance_id: int,
    original_filename: str,
    custom_name: str = Form(None),
    doc_type: str = Form(None),
    file: UploadFile = File(...),
    document_date: str = None,
    category_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id, models.Insurance.owner_id == current_user.id).first()
    if db_insurance is None:
        raise HTTPException(status_code=404, detail="Insurance not found")
        
    file_extension = os.path.splitext(original_filename)[1]
    db_doc = models.Document(
        original_filename=original_filename,
        custom_name=custom_name or original_filename,
        doc_type=doc_type or "Vertragsschreiben",
        insurance_id=insurance_id,
        category_id=category_id,
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    saved_filename = f"doc_{db_doc.id}{file_extension}"
    db_doc.filename = saved_filename
    db.commit()
    
    filepath = os.path.join(UPLOAD_DIR, saved_filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return db_doc

@router.post("/{document_id}/reanalyze")
def reanalyze_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")
        
    if doc.insurance and doc.insurance.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Keine Berechtigung.")

    filepath = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Physikalische Datei nicht mehr auf dem Server vorhanden.")

    text = ocr.extract_text_from_file(filepath)
    extracted = ocr.extract_insurance_data(text, db=db)

    # Update parent insurance metadata if available
    ins = doc.insurance
    if ins:
        if extracted.get("company"):
            ins.company = extracted["company"]
        if extracted.get("insurance_number"):
            ins.insurance_number = extracted["insurance_number"]
        if extracted.get("category"):
            ins.category = extracted["category"]
        if extracted.get("cost"):
            ins.cost = extracted["cost"]
        if extracted.get("payment_cycle"):
            ins.payment_cycle = extracted["payment_cycle"]
        if extracted.get("start_date"):
            ins.start_date = extracted["start_date"]
        if extracted.get("end_date"):
            ins.end_date = extracted["end_date"]
        if extracted.get("cancellation_date"):
            ins.cancellation_date = extracted["cancellation_date"]

        # Update coverage details with clean formatted AI items
        new_items = extracted.get("coverage_details") or []
        if new_items:
            ins.coverage_details = json.dumps(new_items)

    if extracted.get("doc_type"):
        doc.doc_type = extracted["doc_type"]
    if extracted.get("suggested_title") and not doc.custom_name:
        doc.custom_name = extracted["suggested_title"]

    db.commit()

    return {
        "message": "Dokument erfolgreich erneut analysiert und Versicherungsdaten aktualisiert!",
        "extracted": extracted
    }

@router.put("/{document_id}", response_model=schemas.DocumentResponse)
def update_document(
    document_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.insurance and doc.insurance.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    if "custom_name" in payload:
        doc.custom_name = payload["custom_name"]
    if "doc_type" in payload:
        doc.doc_type = payload["doc_type"]

    db.commit()
    db.refresh(doc)
    return doc

@router.get("/{document_id}/view")
def view_document(document_id: int, token: str = None, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    filepath = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File missing")
        
    ext = os.path.splitext(doc.original_filename)[1].lower()
    media_type = "application/pdf" if ext == ".pdf" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png" if ext == ".png" else "application/octet-stream"

    return FileResponse(
        filepath,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename=\"{doc.original_filename}\""}
    )

@router.get("/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    filepath = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File missing")
        
    return FileResponse(
        filepath,
        filename=doc.original_filename,
        headers={"Content-Disposition": f"attachment; filename=\"{doc.original_filename}\""}
    )

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.insurance and doc.insurance.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    if doc.filename:
        filepath = os.path.join(UPLOAD_DIR, doc.filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error removing file {filepath}: {e}")

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}

@router.get("/insurance/{insurance_id}", response_model=List[schemas.DocumentResponse])
def get_documents_by_insurance(insurance_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id, models.Insurance.owner_id == current_user.id).first()
    if db_insurance is None:
        raise HTTPException(status_code=404, detail="Insurance not found")
        
    return db_insurance.documents
