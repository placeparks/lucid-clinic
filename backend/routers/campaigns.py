"""
Lucid Clinic — Campaign API endpoints.
Create campaigns, send messages, view message logs, handle webhooks.
"""

import time
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Campaign, OutreachMessage, ReengagementQueue, Patient
from schemas import (
    CampaignCreate, CampaignOut, CampaignListOut,
    MessageOut, MessageListOut, CommsStatusOut,
)
from services.twilio_sms import SMSService
from services.resend_email import EmailService
import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

# Webhook router (separate prefix for Twilio/Resend callbacks)
webhook_router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _render_template(template: str, patient: Patient, queue_item: ReengagementQueue) -> str:
    """Render message template with patient placeholders."""
    msg = template
    msg = msg.replace("{first_name}", patient.first_name or "")
    msg = msg.replace("{called_name}", queue_item.called_name or patient.called_name or patient.first_name or "")
    msg = msg.replace("{last_name}", patient.last_name or "")
    return msg


def _mask_recipient(recipient: str, channel: str) -> str:
    """Mask PII for display — show only last 4 chars of phone, domain of email."""
    if not recipient:
        return "***"
    if channel == "sms":
        return f"***{recipient[-4:]}" if len(recipient) > 4 else "***"
    if channel == "email" and "@" in recipient:
        parts = recipient.split("@")
        return f"{parts[0][:2]}***@{parts[1]}"
    return "***"


# ── Comms Status ──────────────────────────────────────────

@router.get("/status", response_model=CommsStatusOut)
def get_comms_status():
    """Get communications system status."""
    return CommsStatusOut(
        mock_mode=config.COMMS_MOCK_MODE,
        twilio_configured=bool(config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN),
        resend_configured=bool(config.RESEND_API_KEY),
    )


# ── Campaign CRUD ─────────────────────────────────────────

@router.post("", response_model=CampaignOut)
def create_campaign(body: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign (status=draft)."""
    if body.channel not in ("sms", "email"):
        raise HTTPException(status_code=400, detail="Channel must be 'sms' or 'email'")

    if body.channel == "email" and not body.subject:
        raise HTTPException(status_code=400, detail="Email campaigns require a subject line")

    if body.tier_filter and body.tier_filter not in ("warm", "cool", "cold", "dormant"):
        raise HTTPException(status_code=400, detail="tier_filter must be warm, cool, cold, or dormant")

    # Count eligible recipients
    q = db.query(ReengagementQueue).join(
        Patient, ReengagementQueue.patient_id == Patient.id
    ).filter(
        Patient.is_dnc == False,
        ReengagementQueue.status.in_(["pending", "contacted"]),
    )

    if body.tier_filter:
        q = q.filter(ReengagementQueue.tier == body.tier_filter)
    if body.score_min > 0:
        q = q.filter(ReengagementQueue.score >= body.score_min)

    if body.channel == "sms":
        q = q.filter(ReengagementQueue.cell_phone.isnot(None), ReengagementQueue.cell_phone != "")
    elif body.channel == "email":
        q = q.filter(ReengagementQueue.email.isnot(None), ReengagementQueue.email != "")

    total_eligible = q.count()

    campaign = Campaign(
        name=body.name,
        channel=body.channel,
        tier_filter=body.tier_filter,
        score_min=body.score_min,
        message_template=body.message_template,
        subject=body.subject,
        status="draft",
        total_recipients=total_eligible,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return CampaignOut.model_validate(campaign)


@router.get("", response_model=CampaignListOut)
def list_campaigns(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    channel: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all campaigns with optional filters."""
    q = db.query(Campaign)

    if status:
        q = q.filter(Campaign.status == status)
    if channel:
        q = q.filter(Campaign.channel == channel)

    total = q.count()
    campaigns = q.order_by(Campaign.id.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return CampaignListOut(
        campaigns=[CampaignOut.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get a single campaign detail."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignOut.model_validate(campaign)


# ── Send Campaign ─────────────────────────────────────────

@router.post("/{campaign_id}/send", response_model=CampaignOut)
def send_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Execute a campaign — send all messages to eligible recipients."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Campaign is '{campaign.status}' — only draft campaigns can be sent"
        )

    # Set to sending
    campaign.status = "sending"
    campaign.sent_at = datetime.utcnow()
    db.commit()

    # Initialize services
    sms_service = SMSService()
    email_service = EmailService()

    # Query eligible recipients
    q = db.query(ReengagementQueue).join(
        Patient, ReengagementQueue.patient_id == Patient.id
    ).filter(
        Patient.is_dnc == False,
        ReengagementQueue.status.in_(["pending", "contacted"]),
    )

    if campaign.tier_filter:
        q = q.filter(ReengagementQueue.tier == campaign.tier_filter)
    if campaign.score_min > 0:
        q = q.filter(ReengagementQueue.score >= campaign.score_min)

    if campaign.channel == "sms":
        q = q.filter(ReengagementQueue.cell_phone.isnot(None), ReengagementQueue.cell_phone != "")
    elif campaign.channel == "email":
        q = q.filter(ReengagementQueue.email.isnot(None), ReengagementQueue.email != "")

    recipients = q.all()

    sent_count = 0
    failed_count = 0

    for queue_item in recipients:
        patient = db.query(Patient).filter(Patient.id == queue_item.patient_id).first()
        if not patient:
            continue

        # DNC double-check at send time
        if patient.is_dnc:
            continue

        # Render template
        rendered_body = _render_template(campaign.message_template, patient, queue_item)

        # Determine recipient contact
        if campaign.channel == "sms":
            recipient_contact = queue_item.cell_phone or ""
        else:
            recipient_contact = queue_item.email or ""

        # Create outreach message record
        message = OutreachMessage(
            campaign_id=campaign.id,
            queue_item_id=queue_item.id,
            patient_id=queue_item.patient_id,
            channel=campaign.channel,
            recipient=recipient_contact,
            message_body=rendered_body,
            subject=campaign.subject if campaign.channel == "email" else None,
            status="pending",
        )
        db.add(message)
        db.flush()  # Get the message ID

        # Send via service
        if campaign.channel == "sms":
            result = sms_service.send(
                to=recipient_contact,
                body=rendered_body,
                is_dnc=patient.is_dnc,
            )
            message.external_id = result.get("sid")
        else:
            html_body = f"<div style='font-family: sans-serif; max-width: 600px;'><p>{rendered_body}</p></div>"
            result = email_service.send(
                to=recipient_contact,
                subject=campaign.subject or "Message from Lucid Clinic",
                html_body=html_body,
                is_dnc=patient.is_dnc,
            )
            message.external_id = result.get("id")

        if result.get("status") in ("sent", "queued"):
            message.status = "sent"
            message.sent_at = datetime.utcnow()
            sent_count += 1
        elif result.get("status") == "blocked":
            message.status = "failed"
            message.error_message = result.get("error", "DNC blocked")
            failed_count += 1
        else:
            message.status = "failed"
            message.error_message = result.get("error", "Unknown error")
            failed_count += 1

        # Update queue item
        queue_item.status = "contacted"
        queue_item.contact_attempts = (queue_item.contact_attempts or 0) + 1
        queue_item.last_contacted_at = datetime.utcnow()

        db.commit()

        # 100ms delay between sends to avoid throttling
        time.sleep(0.1)

    # Final campaign stats
    campaign.sent_count = sent_count
    campaign.failed_count = failed_count
    campaign.total_recipients = sent_count + failed_count
    campaign.status = "sent" if sent_count > 0 else "failed"
    db.commit()
    db.refresh(campaign)

    logger.info(f"Campaign {campaign.id} complete: {sent_count} sent, {failed_count} failed")
    return CampaignOut.model_validate(campaign)


# ── Message Log ───────────────────────────────────────────

@router.get("/{campaign_id}/messages", response_model=MessageListOut)
def list_messages(
    campaign_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List messages for a campaign (audit log)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    q = db.query(OutreachMessage).filter(OutreachMessage.campaign_id == campaign_id)

    if status:
        q = q.filter(OutreachMessage.status == status)

    total = q.count()
    messages = q.order_by(OutreachMessage.id.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    # Mask PII in recipient field before returning
    result_messages = []
    for msg in messages:
        out = MessageOut.model_validate(msg)
        out.recipient = _mask_recipient(msg.recipient, msg.channel or "")
        result_messages.append(out)

    return MessageListOut(
        messages=result_messages,
        total=total,
        page=page,
        per_page=per_page,
    )


# ── Webhooks ──────────────────────────────────────────────

@webhook_router.post("/twilio")
async def twilio_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Twilio delivery status + inbound reply webhook.
    Handles: delivered, undelivered, failed statuses.
    Handles: STOP/UNSUBSCRIBE replies → sets is_dnc=true.
    """
    form_data = await request.form()
    message_sid = form_data.get("MessageSid", "")
    message_status = form_data.get("MessageStatus", "")
    from_number = form_data.get("From", "")
    body = form_data.get("Body", "")

    # Handle delivery status updates
    if message_sid and message_status:
        msg = db.query(OutreachMessage).filter(
            OutreachMessage.external_id == message_sid
        ).first()

        if msg:
            if message_status == "delivered":
                msg.status = "delivered"
                msg.delivered_at = datetime.utcnow()
            elif message_status in ("undelivered", "failed"):
                msg.status = "failed"
                msg.error_message = f"Twilio status: {message_status}"

    # Handle inbound replies (STOP/UNSUBSCRIBE)
    if body:
        body_upper = body.strip().upper()
        if body_upper in ("STOP", "UNSUBSCRIBE", "CANCEL", "QUIT", "END"):
            # Find patient by phone number and set DNC
            patient = db.query(Patient).filter(
                Patient.cell_phone.contains(from_number[-10:]) if len(from_number) >= 10 else Patient.cell_phone == from_number
            ).first()
            if patient:
                patient.is_dnc = True
                logger.info(f"Patient {patient.account_id} opted out via SMS STOP")

            # Also mark the last outreach message
            if message_sid:
                msg = db.query(OutreachMessage).filter(
                    OutreachMessage.external_id == message_sid
                ).first()
                if msg:
                    msg.is_opt_out = True
                    msg.response_text = body
                    msg.responded_at = datetime.utcnow()
        else:
            # Regular reply — log it
            recent_msg = db.query(OutreachMessage).filter(
                OutreachMessage.recipient.contains(from_number[-10:]) if len(from_number) >= 10 else OutreachMessage.recipient == from_number
            ).order_by(OutreachMessage.id.desc()).first()
            if recent_msg:
                recent_msg.response_text = body
                recent_msg.responded_at = datetime.utcnow()
                # Update campaign responded count
                campaign = db.query(Campaign).filter(Campaign.id == recent_msg.campaign_id).first()
                if campaign:
                    campaign.responded_count = (campaign.responded_count or 0) + 1

    db.commit()
    return {"status": "ok"}


@webhook_router.post("/resend")
async def resend_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Resend delivery webhook.
    Handles: delivered, bounced events.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "detail": "Invalid JSON"}

    event_type = payload.get("type", "")
    data = payload.get("data", {})
    email_id = data.get("email_id", "")

    if not email_id:
        return {"status": "ok"}

    msg = db.query(OutreachMessage).filter(
        OutreachMessage.external_id == email_id
    ).first()

    if msg:
        if event_type == "email.delivered":
            msg.status = "delivered"
            msg.delivered_at = datetime.utcnow()
        elif event_type == "email.bounced":
            msg.status = "bounced"
            msg.error_message = "Email bounced"
        elif event_type == "email.complained":
            msg.status = "failed"
            msg.error_message = "Spam complaint"
            # Set DNC on spam complaints
            if msg.patient_id:
                patient = db.query(Patient).filter(Patient.id == msg.patient_id).first()
                if patient:
                    patient.is_dnc = True
                    logger.info(f"Patient {patient.account_id} set DNC via spam complaint")

        db.commit()

    return {"status": "ok"}
