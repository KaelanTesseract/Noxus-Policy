# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import os
import json
import datetime

import models, schemas, auth
from database import get_db
from learning import learn_from_feedback

router = APIRouter(prefix="/api/insurances", tags=["insurances"])

import re

def normalize_insurance_name(name: str) -> str:
    if not name:
        return name
    name = re.sub(r'\(Kfz\)$', '(Kfz-Versicherung)', name, flags=re.IGNORECASE)
    name = re.sub(r'\(Haftpflicht\)$', '(Haftpflichtversicherung)', name, flags=re.IGNORECASE)
    name = re.sub(r'\(Hausrat\)$', '(Hausratversicherung)', name, flags=re.IGNORECASE)
    name = re.sub(r'\(Leben\)$', '(Lebensversicherung)', name, flags=re.IGNORECASE)
    name = re.sub(r'\(Gesundheit\)$', '(Krankenversicherung)', name, flags=re.IGNORECASE)
    name = re.sub(r'\(Rechtsschutz\)$', '(Rechtsschutzversicherung)', name, flags=re.IGNORECASE)
    return name

def calc_annual_cost(cost: float, payment_cycle: str) -> float:
    if not cost:
        return 0.0
    c = str(payment_cycle or "jährlich").lower()
    if c == "monatlich": return cost * 12.0
    if c == "vierteljährlich": return cost * 4.0
    if c == "halbjährlich":    return cost * 2.0
    return cost

def record_premium_history_entry(
    db: Session,
    insurance_id: int,
    cost: float,
    payment_cycle: str = "jährlich",
    effective_date: Optional[datetime.date] = None,
    note: str = "Beitragsanpassung"
):
    if not cost or cost <= 0:
        return None

    eff_date = effective_date or datetime.date.today()
    cycle = payment_cycle or "jährlich"
    annual = calc_annual_cost(cost, cycle)

    existing = db.query(models.PremiumHistory).filter(
        models.PremiumHistory.insurance_id == insurance_id,
        models.PremiumHistory.cost == cost,
        models.PremiumHistory.effective_date == eff_date
    ).first()

    if not existing:
        h_entry = models.PremiumHistory(
            insurance_id=insurance_id,
            cost=cost,
            payment_cycle=cycle,
            annual_cost=annual,
            effective_date=eff_date,
            note=note
        )
        db.add(h_entry)
        db.commit()
        db.refresh(h_entry)
        return h_entry
    return existing

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

    history_list = []
    price_change_pct = None
    if hasattr(ins, "premium_history") and ins.premium_history:
        sorted_h = sorted(ins.premium_history, key=lambda x: x.effective_date or datetime.date(1970,1,1))
        for h in sorted_h:
            history_list.append({
                "id": h.id,
                "insurance_id": h.insurance_id,
                "cost": h.cost,
                "payment_cycle": h.payment_cycle,
                "annual_cost": h.annual_cost,
                "effective_date": h.effective_date,
                "note": h.note,
                "created_at": h.created_at
            })

        if len(history_list) >= 2:
            prev = history_list[-2]["annual_cost"]
            curr = history_list[-1]["annual_cost"]
            if prev > 0:
                price_change_pct = round(((curr - prev) / prev) * 100.0, 1)

    res = {
        "id": ins.id,
        "owner_id": ins.owner_id,
        "name": normalize_insurance_name(ins.name),
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
        "sf_class": ins.sf_class,
        "regional_class": ins.regional_class,
        "type_class": ins.type_class,
        "is_suspended": bool(ins.is_suspended),
        "suspension_reason": ins.suspension_reason,
        "claims": claims_list,
        "premium_history": history_list,
        "price_change_pct": price_change_pct
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

    # Initial Premium History entry if cost > 0
    if db_insurance.cost and db_insurance.cost > 0:
        annual = calc_annual_cost(db_insurance.cost, db_insurance.payment_cycle)
        h_entry = models.PremiumHistory(
            insurance_id=db_insurance.id,
            cost=db_insurance.cost,
            payment_cycle=db_insurance.payment_cycle or "jährlich",
            annual_cost=annual,
            effective_date=db_insurance.start_date or datetime.date.today(),
            note="Vertragsabschluss / Initialer Beitrag"
        )
        db.add(h_entry)
        db.commit()
        db.refresh(db_insurance)

    return format_insurance_dict(db_insurance)

from sqlalchemy.orm import Session, selectinload

@router.get("", response_model=List[schemas.InsuranceResponse])
def get_insurances(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    items = (
        db.query(models.Insurance)
        .options(selectinload(models.Insurance.claims), selectinload(models.Insurance.premium_history))
        .filter(models.Insurance.owner_id == current_user.id)
        .all()
    )
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
    
    old_cost = db_insurance.cost
    old_cycle = db_insurance.payment_cycle

    data = insurance.model_dump(exclude_unset=True)
    if "coverage_details" in data and isinstance(data["coverage_details"], list):
        data["coverage_details"] = json.dumps(data["coverage_details"])

    for key, value in data.items():
        setattr(db_insurance, key, value)
    
    # Auto-add PremiumHistory if cost changed
    if db_insurance.cost and (old_cost is None or abs(db_insurance.cost - old_cost) > 0.01 or old_cycle != db_insurance.payment_cycle):
        annual = calc_annual_cost(db_insurance.cost, db_insurance.payment_cycle)
        eff_date = data.get("start_date") or db_insurance.start_date or datetime.date.today()
        h_entry = models.PremiumHistory(
            insurance_id=db_insurance.id,
            cost=db_insurance.cost,
            payment_cycle=db_insurance.payment_cycle or "jährlich",
            annual_cost=annual,
            effective_date=eff_date,
            note="Beitragsanpassung / Aktualisierung"
        )
        db.add(h_entry)

    db.commit()
    db.refresh(db_insurance)

    # Trigger safe anonymized learning loop if insurance has attached document text (ZERO PII LEAK)
    if db_insurance.company and db_insurance.documents:
        for doc in db_insurance.documents:
            ocr_text = getattr(doc, "ocr_text", None)
            if not ocr_text and getattr(doc, "ai_data", None):
                try:
                    ocr_text = json.loads(doc.ai_data).get("extracted_text")
                except Exception:
                    pass
            if ocr_text:
                try:
                    learn_from_feedback(db_insurance.company, "Versicherung", ocr_text, {
                        "regional_class": db_insurance.regional_class,
                        "type_class": db_insurance.type_class,
                        "sf_class": db_insurance.sf_class
                    })
                except Exception as le:
                    print(f"[Learning Loop Notice] {le}")
                break

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
                        except Exception as file_err:
                            print(f"Error deleting physical file {filepath}: {file_err}")
        except Exception as file_err:
            print(f"Notice during file cleanup: {file_err}")

        # 2. Delete insurance (cascade deletes claims, documents, premium_history)
        db.delete(db_insurance)
        db.commit()
        return {"msg": "Insurance deleted successfully"}
    except Exception as e:
        print(f"Delete insurance exception: {e}")
        db.rollback()
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

@router.post("/{insurance_id}/premium-history", response_model=schemas.PremiumHistoryResponse)
def add_premium_history_entry(
    insurance_id: int,
    payload: schemas.PremiumHistoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_insurance = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not db_insurance:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden.")
    if db_insurance.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nicht berechtigt.")

    annual = calc_annual_cost(payload.cost, payload.payment_cycle or db_insurance.payment_cycle or "jährlich")
    new_entry = models.PremiumHistory(
        insurance_id=insurance_id,
        cost=payload.cost,
        payment_cycle=payload.payment_cycle or db_insurance.payment_cycle or "jährlich",
        annual_cost=annual,
        effective_date=payload.effective_date or datetime.date.today(),
        note=payload.note or "Beitragsanpassung"
    )
    db.add(new_entry)
    
    # Update main insurance cost to match latest adjustment
    db_insurance.cost = payload.cost
    if payload.payment_cycle:
        db_insurance.payment_cycle = payload.payment_cycle

    db.commit()
    db.refresh(new_entry)
    return new_entry

@router.delete("/{insurance_id}/premium-history/{history_id}")
def delete_premium_history_entry(
    insurance_id: int,
    history_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_entry = db.query(models.PremiumHistory).filter(models.PremiumHistory.id == history_id, models.PremiumHistory.insurance_id == insurance_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Beitragseintrag nicht gefunden.")

    db.delete(db_entry)
    db.commit()
    return {"msg": "Beitragseintrag gelöscht."}

@router.get("/{insurance_id}/calendar.ics")
def download_single_insurance_ics(
    insurance_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    ins = db.query(models.Insurance).filter(models.Insurance.id == insurance_id).first()
    if not ins:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden.")
    if ins.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nicht berechtigt.")

    deadline_date = ins.cancellation_date or ins.end_date
    if not deadline_date:
        raise HTTPException(status_code=400, detail="Für diese Versicherung ist keine Kündigungsfrist oder Vertragsende hinterlegt.")

    date_str = deadline_date.strftime("%Y%m%d")
    created_str = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    uid = f"noxus-policy-ins-{ins.id}-{date_str}@noxus-policy"

    title = f"⏰ Kündigungsfrist: {ins.name} ({ins.company or 'Unbekannt'})"
    desc_parts = [
        f"Versicherung: {ins.name}",
        f"Gesellschaft: {ins.company or 'Nicht angegeben'}",
        f"Schein-Nr: {ins.insurance_number or 'k.A.'}",
        f"Kategorie: {ins.category or 'Sonstige'}",
        f"Kosten: {ins.cost:.2f} € ({ins.payment_cycle or 'jährlich'})" if ins.cost else "Kosten: k.A."
    ]
    if ins.is_suspended:
        desc_parts.append(f"Status: ⏸️ Vertrag ruht ({ins.suspension_reason or 'Beitragsfrei'})")

    description = "\\n".join(desc_parts)

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Noxus Policy//Single Insurance Calendar//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{created_str}",
        f"DTSTART;VALUE=DATE:{date_str}",
        f"DTEND;VALUE=DATE:{date_str}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        "STATUS:CONFIRMED",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Erinnerung Kündigungsfrist in 14 Tagen",
        "TRIGGER:-P14D",
        "END:VALARM",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Eilige Erinnerung Kündigungsfrist in 7 Tagen",
        "TRIGGER:-P7D",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    ics_content = "\r\n".join(ics_lines)

    filename_safe = "".join(c if c.isalnum() else "_" for c in ins.name).strip("_")
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="kuendigungsfrist_{filename_safe}.ics"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )
