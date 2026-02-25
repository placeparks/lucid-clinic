"""Lucid Clinic — SQLAlchemy ORM models matching CLAUDE.md Section 5 schema."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
)
from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, unique=True, nullable=False, index=True)
    account_type = Column(String)
    first_name = Column(String)
    middle_initial = Column(String)
    last_name = Column(String)
    called_name = Column(String)
    suffix = Column(String)
    sex = Column(String)
    marital = Column(String)
    birthdate = Column(String)
    account_created = Column(String)
    last_appt = Column(String, index=True)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip = Column(String)
    cell_phone = Column(String)
    alt_phone = Column(String)
    work_phone = Column(String)
    email = Column(String, index=True)
    is_dnc = Column(Boolean, default=False)
    pref_contact = Column(String)
    appt_reminders = Column(String)
    ins_carrier = Column(String)
    ins_plan_type = Column(String)
    ins_group = Column(String)
    ins_member_id = Column(String)
    ins_code = Column(String)
    ins_notes = Column(Text)
    balance = Column(Float, default=0)
    pat_balance = Column(Float, default=0)
    total_charges = Column(Float, default=0)
    total_receipts = Column(Float, default=0)
    total_visits = Column(Integer, default=0)
    copay = Column(Float, default=0)
    ref_by = Column(String)
    remarks = Column(Text)
    employment = Column(String)
    reengagement_score = Column(Integer, default=0, index=True)
    tier = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReengagementQueue(Base):
    __tablename__ = "reengagement_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    account_id = Column(String)
    full_name = Column(String)
    called_name = Column(String)
    cell_phone = Column(String)
    email = Column(String)
    last_appt = Column(String)
    days_since_appt = Column(Integer)
    tier = Column(String)
    score = Column(Integer, index=True)
    has_insurance = Column(Boolean)
    total_visits = Column(Integer)
    city = Column(String)
    state = Column(String)
    status = Column(String, default="pending")
    contact_attempts = Column(Integer, default=0)
    last_contacted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_type = Column(String)  # sync_patients / book_appointment / update_record
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=True)
    task_params = Column(Text)  # JSON string of task parameters
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    status = Column(String)  # pending / running / awaiting_confirmation / success / failed / cancelled
    records_affected = Column(Integer, default=0)
    screenshots_path = Column(String)
    screenshot_count = Column(Integer, default=0)
    iterations_used = Column(Integer, default=0)
    error_log = Column(Text)
    result_summary = Column(Text)  # JSON string of task results
    created_at = Column(DateTime, default=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    channel = Column(String, nullable=False)  # sms / email
    tier_filter = Column(String)  # warm / cool / cold / dormant / null=all
    score_min = Column(Integer, default=0)
    message_template = Column(Text, nullable=False)
    subject = Column(String)  # email only
    status = Column(String, default="draft")  # draft / sending / sent / failed
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    responded_count = Column(Integer, default=0)
    booked_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    queue_item_id = Column(Integer, ForeignKey("reengagement_queue.id"))
    patient_id = Column(Integer, ForeignKey("patients.id"))
    channel = Column(String)  # sms / email
    recipient = Column(String)  # phone number or email address
    message_body = Column(Text)
    subject = Column(String)  # email only
    status = Column(String, default="pending")  # pending / sent / delivered / failed / bounced
    external_id = Column(String)  # Twilio SID or Resend ID
    error_message = Column(Text)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    response_text = Column(Text)
    responded_at = Column(DateTime)
    is_opt_out = Column(Boolean, default=False)


class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    owner_name = Column(String)
    owner_email = Column(String)
    tailscale_node_id = Column(String)
    vnc_host = Column(String)
    vnc_port = Column(Integer, default=5900)
    software = Column(String, default="ezbis")
    timezone = Column(String, default="America/Chicago")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
