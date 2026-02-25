"""Lucid Clinic — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS, ENVIRONMENT
from database import engine, Base
from routers import patients, queue, analytics, agent, campaigns

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Lucid Clinic API",
    description="Agentic CRM for chiropractic clinics",
    version="0.1.0",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router)
app.include_router(queue.router)
app.include_router(analytics.router)
app.include_router(agent.router)
app.include_router(campaigns.router)
app.include_router(campaigns.webhook_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "lucid-clinic"}
