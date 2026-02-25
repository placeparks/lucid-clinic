"""Lucid Clinic — Patient CRUD + search/filter endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional

from database import get_db
from models import Patient
from schemas import PatientOut, PatientSummary, PatientListOut, PatientUpdate

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=PatientListOut)
def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    tier: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    has_insurance: Optional[bool] = None,
    is_dnc: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = Query("reengagement_score", pattern="^(reengagement_score|last_name|last_appt|total_visits)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    q = db.query(Patient)

    if tier:
        q = q.filter(Patient.tier == tier)
    if score_min is not None:
        q = q.filter(Patient.reengagement_score >= score_min)
    if score_max is not None:
        q = q.filter(Patient.reengagement_score <= score_max)
    if city:
        q = q.filter(func.lower(Patient.city) == city.lower())
    if state:
        q = q.filter(func.upper(Patient.state) == state.upper())
    if has_insurance is True:
        q = q.filter(Patient.ins_carrier.isnot(None), Patient.ins_carrier != "")
    elif has_insurance is False:
        q = q.filter(or_(Patient.ins_carrier.is_(None), Patient.ins_carrier == ""))
    if is_dnc is not None:
        q = q.filter(Patient.is_dnc == is_dnc)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
                Patient.called_name.ilike(term),
                Patient.email.ilike(term),
                Patient.cell_phone.ilike(term),
                Patient.account_id.ilike(term),
            )
        )

    total = q.count()

    col = getattr(Patient, sort_by)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())

    patients = q.offset((page - 1) * per_page).limit(per_page).all()

    return PatientListOut(
        patients=[PatientSummary.model_validate(p) for p in patients],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientOut.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    update: PatientUpdate,
    db: Session = Depends(get_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return PatientOut.model_validate(patient)
