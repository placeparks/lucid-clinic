"""Lucid Clinic — Dashboard analytics endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from database import get_db
from models import Patient, ReengagementQueue
from schemas import AnalyticsOverview, TierCount, ContactCoverage

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(db: Session = Depends(get_db)):
    total = db.query(func.count(Patient.id)).scalar()
    queue_size = db.query(func.count(ReengagementQueue.id)).scalar()
    dnc_count = db.query(func.count(Patient.id)).filter(Patient.is_dnc == True).scalar()
    has_email = db.query(func.count(Patient.id)).filter(
        Patient.email.isnot(None), Patient.email != ""
    ).scalar()
    has_phone = db.query(func.count(Patient.id)).filter(
        Patient.cell_phone.isnot(None)
    ).scalar()

    tiers = []
    for tier_name in ["active", "warm", "cool", "cold", "dormant", "unknown"]:
        count = db.query(func.count(Patient.id)).filter(Patient.tier == tier_name).scalar()
        tiers.append(TierCount(tier=tier_name, count=count))

    return AnalyticsOverview(
        total_patients=total,
        queue_size=queue_size,
        dnc_count=dnc_count,
        has_email=has_email,
        has_phone=has_phone,
        tiers=tiers,
    )


@router.get("/contact-coverage", response_model=ContactCoverage)
def get_contact_coverage(db: Session = Depends(get_db)):
    has_email = and_(Patient.email.isnot(None), Patient.email != "")
    has_phone = Patient.cell_phone.isnot(None)

    both = db.query(func.count(Patient.id)).filter(has_email, has_phone).scalar()
    email_only = db.query(func.count(Patient.id)).filter(
        has_email, or_(Patient.cell_phone.is_(None))
    ).scalar()
    phone_only = db.query(func.count(Patient.id)).filter(
        has_phone, or_(Patient.email.is_(None), Patient.email == "")
    ).scalar()
    no_contact = db.query(func.count(Patient.id)).filter(
        or_(Patient.email.is_(None), Patient.email == ""),
        Patient.cell_phone.is_(None),
    ).scalar()

    return ContactCoverage(
        has_both=both,
        email_only=email_only,
        phone_only=phone_only,
        no_contact=no_contact,
    )
