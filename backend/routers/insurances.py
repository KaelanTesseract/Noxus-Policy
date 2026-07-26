from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import os
import json
import datetime

import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/insurances", tags=["insurances"])

def format_insurance_dict(ins: models.Insurance) -> dict:
    claims_list = []
    if hasattr(ins, "claims") and ins.claims:
        for c in ins.claims:
            claims_list.append({
                "id": c.id,
                "insurance_id": c.insurance_id,
                "claim_number": c.claim_number,
                "claim_date": c.claim_date,
                "amount": c.amount,
                "status": c.status,
                "description": c.description
            })

    res = {
        "id": ins.id,
        "owner_id": ins.owner_id,
        "name": ins.name,
        "company": ins.company,
        "insurance_number": ins.insurance_number,
        "category": ins.category,
        "cost": ins.cost,
        "payment_cycle": ins.payment_cycle,
        "start_date": ins.start_date,
        "end_date": ins.end_date,
        "cancellation_date": ins.cancellation_date,
        "contact_info": ins.contact_info,
        "coverage_details": [],
        "notes": ins.notes,
        "claims": claims_list
    }
    if ins.coverage_details:
        try:
            res["coverage_details"] = json.loads(ins.coverage_details)
        except Exception:
            res["coverage_details"] = [ins.coverage_details]
    return res

@router.post("", response_model=schemas.InsuranceResponse)
def create_insurance(insurance: schemas.InsuranceCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    data = insurance.model_dump()
    if isinstance(data.get("coverage_details"), list):
        data["coverage_details"] = json.dumps(data["coverage_details"])
    
    db_insurance = models.Insurance(**data, owner_id=current_user.id)
    db.add(db_insurance)
    db.commit()
    db.refresh(db_insurance)
    return format_insurance_dict(db_insurance)

@router.get("", response_model=List[schemas.InsuranceResponse])
def get_insurances(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    items = db.query(models.Insurance).filter(models.Insurance.owner_id == current_user.id).all()
    return [format_insurance_dict(ins) for ins in items]

@router.get("/{insurance_id}", response_model=schemas.InsuranceResponse)
def get_insurance(insurance_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id, models.Insurance.owner_id == current_user.id).first()
    if db_insurance is None:
        raise HTTPException(status_code=404, detail="Insurance not found")
    return format_insurance_dict(db_insurance)

@router.put("/{insurance_id}", response_model=schemas.InsuranceResponse)
def update_insurance(insurance_id: int, insurance: schemas.InsuranceUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id, models.Insurance.owner_id == current_user.id).first()
    if db_insurance is None:
        raise HTTPException(status_code=404, detail="Insurance not found")
    
    data = insurance.model_dump(exclude_unset=True)
    if "coverage_details" in data and isinstance(data["coverage_details"], list):
        data["coverage_details"] = json.dumps(data["coverage_details"])

    for key, value in data.items():
        setattr(db_insurance, key, value)
    db.commit()
    db.refresh(db_insurance)
    return format_insurance_dict(db_insurance)

@router.delete("/{insurance_id}")
def delete_insurance(insurance_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    try:
        db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
        if db_insurance is None:
            raise HTTPException(status_code=404, detail="Insurance not found")

        if db_insurance.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Forbidden")

        # 1. Fetch physical filenames with raw SQL to prevent schema column mismatch
        try:
            doc_rows = db.execute(text("SELECT filename FROM documents WHERE insurance_id = :iid"), {"iid": insurance_id}).fetchall()
            for r in doc_rows:
                fname = r[0]
                if fname:
                    filepath = os.path.join("documents", fname)
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            print(f"Error deleting physical file {filepath}: {e}")
        except Exception as file_err:
            print(f"Notice during file cleanup: {file_err}")

        # 2. Execute direct SQL deletions to bypass ORM cascade/foreign key locks
        db.execute(text("DELETE FROM claims WHERE insurance_id = :iid"), {"iid": insurance_id})
        db.execute(text("DELETE FROM documents WHERE insurance_id = :iid"), {"iid": insurance_id})
        db.execute(text("DELETE FROM insurances WHERE id = :iid"), {"iid": insurance_id})
        db.commit()

        return {"msg": "Deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"Delete insurance exception: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Löschen: {str(e)}")

class NotesUpdatePayload(BaseModel):
    notes: Optional[str] = None

@router.put("/{insurance_id}/notes")
def update_insurance_notes(
    insurance_id: int,
    payload: NotesUpdatePayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not db_insurance:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden.")
    if db_insurance.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nicht berechtigt.")

    db_insurance.notes = payload.notes
    db.commit()
    return {"msg": "Notizen erfolgreich gespeichert.", "notes": db_insurance.notes}

@router.post("/{insurance_id}/claims", response_model=schemas.ClaimResponse)
def add_claim(
    insurance_id: int,
    payload: schemas.ClaimCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not db_insurance:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden.")
    if db_insurance.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nicht berechtigt.")

    new_claim = models.Claim(
        insurance_id=insurance_id,
        claim_number=payload.claim_number or f"SCH-{datetime.date.today().strftime('%Y%m%d')}-{db_insurance.id}",
        claim_date=payload.claim_date or datetime.date.today(),
        amount=payload.amount,
        status=payload.status or "In Bearbeitung",
        description=payload.description
    )
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    return new_claim

@router.delete("/{insurance_id}/claims/{claim_id}")
def delete_claim(
    insurance_id: int,
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_claim = db.query(models.Claim).filter(models.Claim.id == claim_id, models.Claim.insurance_id == insurance_id).first()
    if not db_claim:
        raise HTTPException(status_code=404, detail="Schadensmeldung nicht gefunden.")

    db.delete(db_claim)
    db.commit()
    return {"msg": "Schadensmeldung gelöscht."}
