"""Lucid Clinic — Re-engagement queue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime

from database import get_db
from models import ReengagementQueue
from schemas import QueueItemOut, QueueListOut, QueueStatusUpdate

router = APIRouter(prefix="/api/queue", tags=["queue"])

VALID_STATUSES = {"pending", "contacted", "responded", "booked", "dead"}


@router.get("", response_model=QueueListOut)
def list_queue(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    tier: Optional[str] = None,
    status: Optional[str] = None,
    score_min: Optional[int] = None,
    sort_by: str = Query("score", pattern="^(score|days_since_appt|full_name)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    q = db.query(ReengagementQueue)

    if tier:
        q = q.filter(ReengagementQueue.tier == tier)
    if status:
        q = q.filter(ReengagementQueue.status == status)
    if score_min is not None:
        q = q.filter(ReengagementQueue.score >= score_min)

    total = q.count()

    col = getattr(ReengagementQueue, sort_by)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())

    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return QueueListOut(
        items=[QueueItemOut.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/{queue_id}/status", response_model=QueueItemOut)
def update_queue_status(
    queue_id: int,
    body: QueueStatusUpdate,
    db: Session = Depends(get_db),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    item = db.query(ReengagementQueue).filter(ReengagementQueue.id == queue_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    item.status = body.status
    if body.status == "contacted":
        item.contact_attempts = (item.contact_attempts or 0) + 1
        item.last_contacted_at = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return QueueItemOut.model_validate(item)
