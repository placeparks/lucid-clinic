"""Lucid Clinic — Configuration via environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(Path(__file__).resolve().parent / ".env")

# Database (Supabase Postgres)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# CORS
_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS_ORIGINS = [
    origin.strip().rstrip("/") 
    for origin in _cors_env.split(",") 
    if origin.strip()
]

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Agent — Computer Use
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
VNC_HOST = os.getenv("VNC_HOST", "")
VNC_PORT = int(os.getenv("VNC_PORT", "5900"))
VNC_PASSWORD = os.getenv("VNC_PASSWORD", "")
AGENT_MOCK_MODE = os.getenv("AGENT_MOCK_MODE", "true").lower() == "true"
AGENT_MAX_SESSION_MINUTES = int(os.getenv("AGENT_MAX_SESSION_MINUTES", "30"))
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "20"))
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", str(BASE_DIR / "data" / "screenshots"))

# Communications — SMS + Email
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "noreply@lucidclinic.com")
COMMS_MOCK_MODE = os.getenv("COMMS_MOCK_MODE", "true").lower() == "true"
