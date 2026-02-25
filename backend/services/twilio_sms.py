"""Lucid Clinic — Twilio SMS Service with mock mode."""

import re
import uuid
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class SMSService:
    """Send SMS via Twilio. Falls back to mock mode when COMMS_MOCK_MODE=true."""

    def __init__(self):
        self.mock_mode = config.COMMS_MOCK_MODE
        self.from_number = config.TWILIO_FROM_NUMBER
        self._client = None

    def _get_client(self):
        """Lazy-load Twilio client only when needed."""
        if self._client is None and not self.mock_mode:
            from twilio.rest import Client
            self._client = Client(
                config.TWILIO_ACCOUNT_SID,
                config.TWILIO_AUTH_TOKEN,
            )
        return self._client

    @staticmethod
    def validate_phone(phone: str) -> str | None:
        """Validate and normalize US phone number. Returns E.164 or None."""
        if not phone:
            return None
        digits = re.sub(r"[^\d]", "", phone)
        if len(digits) == 10:
            digits = "1" + digits
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        return None

    def send(self, to: str, body: str, is_dnc: bool = False) -> dict:
        """
        Send an SMS message.

        Args:
            to: Phone number (any format — will be normalized)
            body: Message text
            is_dnc: DNC flag — hard block if True

        Returns:
            dict with 'sid', 'status', 'error' keys
        """
        # DNC hard block — NEVER contact flagged patients
        if is_dnc:
            logger.warning("DNC hard block: refusing to send SMS")
            return {"sid": None, "status": "blocked", "error": "DNC patient — contact blocked"}

        normalized = self.validate_phone(to)
        if not normalized:
            return {"sid": None, "status": "failed", "error": f"Invalid phone number: {to}"}

        if self.mock_mode:
            fake_sid = f"SM_mock_{uuid.uuid4().hex[:16]}"
            logger.info(f"[MOCK SMS] To: {normalized} | Body: {body[:50]}... | SID: {fake_sid}")
            return {"sid": fake_sid, "status": "sent", "error": None}

        # Live Twilio send
        try:
            client = self._get_client()
            message = client.messages.create(
                to=normalized,
                from_=self.from_number,
                body=body,
            )
            logger.info(f"SMS sent: SID={message.sid}, status={message.status}")
            return {"sid": message.sid, "status": message.status, "error": None}
        except Exception as e:
            logger.error(f"Twilio send failed: {e}")
            return {"sid": None, "status": "failed", "error": str(e)}
