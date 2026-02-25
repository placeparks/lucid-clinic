"""
Lucid Clinic — Task Runner
Orchestrates agent tasks with governance, safety checks, and session management.

Per CLAUDE.md Section 7 — Agent Governance:
1. Every session is logged with timestamps, actions, screenshots
2. No autonomous operation without human-approved task queue
3. Confirmation required before any write operation
4. DNC flag is hard block
5. Detect and halt on unexpected screens
6. Max session: 30 minutes
7. Screenshot every action
8. Failsafe on low confidence
"""

import json
import logging
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from agent.vnc_controller import create_vnc_controller
from agent.computer_use import ComputerUseAgent, MockComputerUseAgent
from agent.screenshot_logger import ScreenshotLogger
from agent.tasks import TASK_REGISTRY
from models import AgentSession, Patient
import config

logger = logging.getLogger("lucid.agent.runner")

# Track running tasks to prevent concurrent execution
_running_lock = threading.Lock()
_running_session_id: int | None = None


class TaskRunner:
    """
    Validates, executes, and logs agent tasks.
    Enforces all governance rules from CLAUDE.md Section 7.
    """

    def __init__(self, db: Session):
        self.db = db
        self.screenshot_logger = ScreenshotLogger(config.SCREENSHOTS_DIR)

    def submit_task(self, task_type: str, params: dict, confirmed: bool = False) -> AgentSession:
        """
        Submit a new agent task for execution.

        Args:
            task_type: One of sync_patients, book_appointment, update_record
            params: Task-specific parameters
            confirmed: Whether write operations have been confirmed by user

        Returns:
            AgentSession record
        """
        global _running_session_id

        # 1. Validate task type
        if task_type not in TASK_REGISTRY:
            raise ValueError(f"Unknown task type: {task_type}. Valid: {', '.join(TASK_REGISTRY.keys())}")

        task_cls = TASK_REGISTRY[task_type]
        task = task_cls()

        # 2. Validate parameters
        is_valid, error_msg = task.validate_params(params)
        if not is_valid:
            raise ValueError(f"Invalid parameters: {error_msg}")

        # 3. DNC check — HARD BLOCK (CLAUDE.md Section 7.4)
        patient_account_id = params.get("patient_account_id")
        if patient_account_id:
            patient = self.db.query(Patient).filter(
                Patient.account_id == patient_account_id
            ).first()
            if patient and patient.is_dnc:
                raise PermissionError(
                    f"BLOCKED: Patient {patient_account_id} has DNC flag. "
                    "Cannot perform any agent operations on DNC patients."
                )
            # Add patient name to params for the prompt if found
            if patient:
                params["patient_name"] = f"{patient.first_name} {patient.last_name}".strip()

        # 4. Confirmation check for write operations
        if task.requires_confirmation and not confirmed:
            # Create session in awaiting_confirmation status
            session = AgentSession(
                session_type=task_type,
                task_params=json.dumps(params),
                started_at=datetime.utcnow(),
                status="awaiting_confirmation",
                screenshots_path=str(config.SCREENSHOTS_DIR),
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            logger.info(
                "Task %s (session %d) awaiting confirmation — write operation",
                task_type, session.id
            )
            return session

        # 5. Check no other task is running (single task at a time)
        with _running_lock:
            if _running_session_id is not None:
                raise RuntimeError(
                    f"Another task is already running (session {_running_session_id}). "
                    "Wait for it to complete or cancel it."
                )

        # 6. Create session record
        session = AgentSession(
            session_type=task_type,
            task_params=json.dumps(params),
            started_at=datetime.utcnow(),
            status="running",
            screenshots_path=str(config.SCREENSHOTS_DIR),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # 7. Launch task in background thread
        thread = threading.Thread(
            target=self._execute_task,
            args=(session.id, task, params),
            daemon=True,
        )
        thread.start()

        logger.info("Task %s started (session %d)", task_type, session.id)
        return session

    def confirm_task(self, session_id: int) -> AgentSession:
        """Confirm a pending write operation and start execution."""
        session = self.db.query(AgentSession).filter(AgentSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session.status != "awaiting_confirmation":
            raise ValueError(f"Session {session_id} is not awaiting confirmation (status: {session.status})")

        task_type = session.session_type
        params = json.loads(session.task_params or "{}")

        task_cls = TASK_REGISTRY[task_type]
        task = task_cls()

        # Update session to running
        session.status = "running"
        self.db.commit()

        # Launch in background
        thread = threading.Thread(
            target=self._execute_task,
            args=(session.id, task, params),
            daemon=True,
        )
        thread.start()

        logger.info("Task %s confirmed and started (session %d)", task_type, session.id)
        return session

    def cancel_task(self, session_id: int) -> AgentSession:
        """Cancel a running or pending task."""
        global _running_session_id

        session = self.db.query(AgentSession).filter(AgentSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status in ("success", "failed", "cancelled"):
            raise ValueError(f"Session {session_id} already completed (status: {session.status})")

        session.status = "cancelled"
        session.ended_at = datetime.utcnow()
        self.db.commit()

        with _running_lock:
            if _running_session_id == session_id:
                _running_session_id = None

        logger.info("Task cancelled (session %d)", session_id)
        return session

    def _execute_task(self, session_id: int, task, params: dict):
        """Execute task in background thread. Updates session record on completion."""
        global _running_session_id

        with _running_lock:
            _running_session_id = session_id

        # Need a fresh DB session for this thread
        from database import SessionLocal
        db = SessionLocal()

        try:
            session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
            if not session or session.status == "cancelled":
                return

            # Create VNC controller
            vnc = create_vnc_controller(
                mock_mode=config.AGENT_MOCK_MODE,
                host=config.VNC_HOST,
                port=config.VNC_PORT,
                password=config.VNC_PASSWORD,
            )
            vnc.connect()

            try:
                # Create agent (mock or live based on API key availability)
                if config.AGENT_MOCK_MODE or not config.ANTHROPIC_API_KEY:
                    agent = MockComputerUseAgent(
                        vnc=vnc,
                        screenshot_logger=self.screenshot_logger,
                        session_id=session_id,
                    )
                else:
                    agent = ComputerUseAgent(
                        api_key=config.ANTHROPIC_API_KEY,
                        vnc=vnc,
                        screenshot_logger=self.screenshot_logger,
                        session_id=session_id,
                        max_iterations=config.AGENT_MAX_ITERATIONS,
                        max_minutes=config.AGENT_MAX_SESSION_MINUTES,
                    )

                # Build prompt and run
                task_prompt = task.build_prompt(params)
                result = agent.run(task.system_prompt, task_prompt)

                # Parse results
                parsed = task.parse_result(result)

                # Update session
                session.status = result.get("status", "failed")
                if session.status == "max_iterations":
                    session.status = "partial"
                session.ended_at = datetime.utcnow()
                session.iterations_used = result.get("iterations", 0)
                session.screenshot_count = self.screenshot_logger.get_screenshot_count(session_id)
                session.result_summary = json.dumps(parsed)
                session.error_log = result.get("error")

                if result.get("status") == "success":
                    session.records_affected = parsed.get("records_synced", 0) or (1 if parsed.get("booked") or parsed.get("updated") else 0)

                db.commit()
                logger.info(
                    "Task completed (session %d): status=%s, iterations=%d",
                    session_id, session.status, session.iterations_used
                )

            finally:
                vnc.disconnect()

        except Exception as e:
            logger.error("Task execution failed (session %d): %s", session_id, str(e), exc_info=True)
            try:
                session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
                if session:
                    session.status = "failed"
                    session.ended_at = datetime.utcnow()
                    session.error_log = str(e)
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
            with _running_lock:
                if _running_session_id == session_id:
                    _running_session_id = None
