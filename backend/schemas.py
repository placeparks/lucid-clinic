"""Lucid Clinic — Pydantic request/response schemas."""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


# ── Patient ──────────────────────────────────────────────

class PatientOut(BaseModel):
    id: int
    account_id: str
    account_type: Optional[str] = None
    first_name: Optional[str] = None
    middle_initial: Optional[str] = None
    last_name: Optional[str] = None
    called_name: Optional[str] = None
    suffix: Optional[str] = None
    sex: Optional[str] = None
    marital: Optional[str] = None
    birthdate: Optional[str] = None
    account_created: Optional[str] = None
    last_appt: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    cell_phone: Optional[str] = None
    alt_phone: Optional[str] = None
    work_phone: Optional[str] = None
    email: Optional[str] = None
    is_dnc: bool = False
    pref_contact: Optional[str] = None
    ins_carrier: Optional[str] = None
    ins_plan_type: Optional[str] = None
    ins_group: Optional[str] = None
    ins_member_id: Optional[str] = None
    ins_code: Optional[str] = None
    balance: float = 0
    pat_balance: float = 0
    total_charges: float = 0
    total_receipts: float = 0
    total_visits: int = 0
    copay: float = 0
    ref_by: Optional[str] = None
    remarks: Optional[str] = None
    employment: Optional[str] = None
    reengagement_score: int = 0
    tier: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PatientSummary(BaseModel):
    """Lightweight patient for list views."""
    id: int
    account_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    called_name: Optional[str] = None
    cell_phone: Optional[str] = None
    email: Optional[str] = None
    last_appt: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    is_dnc: bool = False
    ins_carrier: Optional[str] = None
    total_visits: int = 0
    reengagement_score: int = 0
    tier: Optional[str] = None

    model_config = {"from_attributes": True}


class PatientListOut(BaseModel):
    patients: list[PatientSummary]
    total: int
    page: int
    per_page: int


class PatientUpdate(BaseModel):
    cell_phone: Optional[str] = None
    alt_phone: Optional[str] = None
    work_phone: Optional[str] = None
    email: Optional[str] = None
    pref_contact: Optional[str] = None
    remarks: Optional[str] = None


# ── Re-engagement Queue ─────────────────────────────────

class QueueItemOut(BaseModel):
    id: int
    patient_id: Optional[int] = None
    account_id: Optional[str] = None
    full_name: Optional[str] = None
    called_name: Optional[str] = None
    cell_phone: Optional[str] = None
    email: Optional[str] = None
    last_appt: Optional[str] = None
    days_since_appt: Optional[int] = None
    tier: Optional[str] = None
    score: int = 0
    has_insurance: Optional[bool] = None
    total_visits: int = 0
    city: Optional[str] = None
    state: Optional[str] = None
    status: str = "pending"
    contact_attempts: int = 0
    last_contacted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class QueueListOut(BaseModel):
    items: list[QueueItemOut]
    total: int
    page: int
    per_page: int


class QueueStatusUpdate(BaseModel):
    status: str  # pending / contacted / responded / booked / dead


# ── Analytics ────────────────────────────────────────────

class TierCount(BaseModel):
    tier: str
    count: int


class AnalyticsOverview(BaseModel):
    total_patients: int
    queue_size: int
    dnc_count: int
    has_email: int
    has_phone: int
    tiers: list[TierCount]


class ContactCoverage(BaseModel):
    has_both: int
    email_only: int
    phone_only: int
    no_contact: int


# ── Agent Sessions ───────────────────────────────────────

class TaskSubmit(BaseModel):
    task_type: str  # sync_patients / book_appointment / update_record
    params: dict = {}
    confirmed: bool = False


class TaskConfirm(BaseModel):
    pass  # No body needed, session_id is in URL


class SessionOut(BaseModel):
    id: int
    session_type: Optional[str] = None
    task_params: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: Optional[str] = None
    records_affected: int = 0
    screenshot_count: int = 0
    iterations_used: int = 0
    error_log: Optional[str] = None
    result_summary: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SessionListOut(BaseModel):
    sessions: list[SessionOut]
    total: int
    page: int
    per_page: int


class ScreenshotOut(BaseModel):
    filename: str
    path: str
    step: int
    action: str
    size_bytes: int
    timestamp: str


class AgentStatusOut(BaseModel):
    mock_mode: bool
    vnc_configured: bool
    api_key_configured: bool
    running_session_id: Optional[int] = None
    available_tasks: list[str]


# ── Campaigns ───────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str
    channel: str  # sms / email
    tier_filter: Optional[str] = None  # warm / cool / cold / dormant / None=all
    score_min: int = 0
    message_template: str
    subject: Optional[str] = None  # email only


class CampaignOut(BaseModel):
    id: int
    name: str
    channel: str
    tier_filter: Optional[str] = None
    score_min: int = 0
    message_template: str
    subject: Optional[str] = None
    status: str = "draft"
    total_recipients: int = 0
    sent_count: int = 0
    failed_count: int = 0
    responded_count: int = 0
    booked_count: int = 0
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CampaignListOut(BaseModel):
    campaigns: list[CampaignOut]
    total: int
    page: int
    per_page: int


class MessageOut(BaseModel):
    id: int
    campaign_id: int
    queue_item_id: Optional[int] = None
    patient_id: Optional[int] = None
    channel: Optional[str] = None
    recipient: Optional[str] = None
    message_body: Optional[str] = None
    subject: Optional[str] = None
    status: str = "pending"
    external_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    response_text: Optional[str] = None
    responded_at: Optional[datetime] = None
    is_opt_out: bool = False

    model_config = {"from_attributes": True}


class MessageListOut(BaseModel):
    messages: list[MessageOut]
    total: int
    page: int
    per_page: int


class CommsStatusOut(BaseModel):
    mock_mode: bool
    twilio_configured: bool
    resend_configured: bool
