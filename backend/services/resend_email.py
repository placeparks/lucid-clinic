"""Lucid Clinic — Resend Email Service with mock mode."""

import re
import uuid
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class EmailService:
    """Send email via Resend. Falls back to mock mode when COMMS_MOCK_MODE=true."""

    def __init__(self):
        self.mock_mode = config.COMMS_MOCK_MODE
        self.from_email = config.RESEND_FROM_EMAIL
        self._client_initialized = False

    def _init_client(self):
        """Initialize Resend API key once."""
        if not self._client_initialized and not self.mock_mode:
            import resend
            resend.api_key = config.RESEND_API_KEY
            self._client_initialized = True

    @staticmethod
    def validate_email(email: str) -> str | None:
        """Validate email format. Returns cleaned email or None."""
        if not email:
            return None
        email = email.strip().lower()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(pattern, email):
            return email
        return None

    def send(self, to: str, subject: str, html_body: str, is_dnc: bool = False) -> dict:
        """
        Send an email message.

        Args:
            to: Email address
            subject: Email subject line
            html_body: HTML email body
            is_dnc: DNC flag — hard block if True

        Returns:
            dict with 'id', 'status', 'error' keys
        """
        # DNC hard block — NEVER contact flagged patients
        if is_dnc:
            logger.warning("DNC hard block: refusing to send email")
            return {"id": None, "status": "blocked", "error": "DNC patient — contact blocked"}

        validated = self.validate_email(to)
        if not validated:
            return {"id": None, "status": "failed", "error": f"Invalid email address: {to}"}

        if self.mock_mode:
            fake_id = f"email_mock_{uuid.uuid4().hex[:16]}"
            logger.info(f"[MOCK EMAIL] To: {validated} | Subject: {subject} | ID: {fake_id}")
            return {"id": fake_id, "status": "sent", "error": None}

        # Live Resend send
        try:
            self._init_client()
            import resend

            params = {
                "from": self.from_email,
                "to": [validated],
                "subject": subject,
                "html": html_body,
            }
            response = resend.Emails.send(params)
            email_id = response.get("id", str(uuid.uuid4()))
            logger.info(f"Email sent: ID={email_id}")
            return {"id": email_id, "status": "sent", "error": None}
        except Exception as e:
            logger.error(f"Resend send failed: {e}")
            return {"id": None, "status": "failed", "error": str(e)}
