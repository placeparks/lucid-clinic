"""
Lucid Clinic — Agent API endpoints.
Submit tasks, view sessions, audit screenshots.
"""

import base64
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import AgentSession
from schemas import (
    TaskSubmit, SessionOut, SessionListOut,
    ScreenshotOut, AgentStatusOut,
)
from agent.task_runner import TaskRunner, _running_session_id, _running_lock
from agent.tasks import TASK_REGISTRY
from agent.screenshot_logger import ScreenshotLogger
import config

router = APIRouter(prefix="/api/agent", tags=["agent"])


def get_screenshot_logger():
    return ScreenshotLogger(config.SCREENSHOTS_DIR)


# ── Agent Status ────────────────────────────────────────

@router.get("/status", response_model=AgentStatusOut)
def get_agent_status():
    """Get agent system status — mock mode, VNC config, running tasks."""
    with _running_lock:
        running = _running_session_id

    return AgentStatusOut(
        mock_mode=config.AGENT_MOCK_MODE,
        vnc_configured=bool(config.VNC_HOST),
        api_key_configured=bool(config.ANTHROPIC_API_KEY),
        running_session_id=running,
        available_tasks=list(TASK_REGISTRY.keys()),
    )


# ── Task Submission ─────────────────────────────────────

@router.post("/tasks", response_model=SessionOut)
def submit_task(body: TaskSubmit, db: Session = Depends(get_db)):
    """
    Submit a new agent task.
    Write operations (book_appointment, update_record) require confirmed=true.
    """
    runner = TaskRunner(db)
    try:
        session = runner.submit_task(body.task_type, body.params, body.confirmed)
        return SessionOut.model_validate(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/tasks/{session_id}/confirm", response_model=SessionOut)
def confirm_task(session_id: int, db: Session = Depends(get_db)):
    """Confirm a pending write operation and start execution."""
    runner = TaskRunner(db)
    try:
        session = runner.confirm_task(session_id)
        return SessionOut.model_validate(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/{session_id}/cancel", response_model=SessionOut)
def cancel_task(session_id: int, db: Session = Depends(get_db)):
    """Cancel a running or pending task."""
    runner = TaskRunner(db)
    try:
        session = runner.cancel_task(session_id)
        return SessionOut.model_validate(session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Session History ─────────────────────────────────────

@router.get("/sessions", response_model=SessionListOut)
def list_sessions(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all agent sessions with optional filters."""
    q = db.query(AgentSession)

    if status:
        q = q.filter(AgentSession.status == status)
    if task_type:
        q = q.filter(AgentSession.session_type == task_type)

    total = q.count()
    sessions = q.order_by(AgentSession.id.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return SessionListOut(
        sessions=[SessionOut.model_validate(s) for s in sessions],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a single session detail."""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut.model_validate(session)


# ── Screenshots ─────────────────────────────────────────

@router.get("/sessions/{session_id}/screenshots", response_model=list[ScreenshotOut])
def list_screenshots(session_id: int, db: Session = Depends(get_db)):
    """List all screenshots for a session (audit trail)."""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    logger = get_screenshot_logger()
    screenshots = logger.get_session_screenshots(session_id)
    return [ScreenshotOut(**s) for s in screenshots]


@router.get("/sessions/{session_id}/screenshots/{filename}")
def get_screenshot(session_id: int, filename: str, db: Session = Depends(get_db)):
    """Serve a specific screenshot image."""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    logger = get_screenshot_logger()
    png_bytes = logger.get_screenshot_bytes(session_id, filename)
    if not png_bytes:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return Response(content=png_bytes, media_type="image/png")
