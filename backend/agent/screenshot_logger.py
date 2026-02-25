"""
Lucid Clinic — Screenshot Logger
Saves and manages screenshots for agent session audit trail.
Per CLAUDE.md Section 7: screenshot every action, 30-day retention.
"""

import os
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger("lucid.agent.screenshots")


class ScreenshotLogger:
    """Manages screenshot storage for agent sessions."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: int) -> Path:
        d = self.base_dir / str(session_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def log_screenshot(
        self,
        session_id: int,
        step: int,
        png_bytes: bytes,
        action_desc: str = "",
    ) -> str:
        """
        Save a screenshot to disk.

        Returns:
            Relative path from screenshots base dir (e.g., '42/0001_click.png')
        """
        safe_action = "".join(c if c.isalnum() or c in "-_" else "_" for c in action_desc)[:30]
        filename = f"{step:04d}_{safe_action}.png"
        session_dir = self._session_dir(session_id)
        filepath = session_dir / filename

        filepath.write_bytes(png_bytes)
        logger.info("Screenshot saved: %s (%d bytes)", filepath, len(png_bytes))

        return f"{session_id}/{filename}"

    def get_session_screenshots(self, session_id: int) -> list[dict]:
        """Get all screenshots for a session, ordered by step."""
        session_dir = self._session_dir(session_id)
        screenshots = []

        for f in sorted(session_dir.glob("*.png")):
            parts = f.stem.split("_", 1)
            step = int(parts[0]) if parts[0].isdigit() else 0
            action = parts[1] if len(parts) > 1 else ""
            screenshots.append({
                "filename": f.name,
                "path": f"{session_id}/{f.name}",
                "step": step,
                "action": action,
                "size_bytes": f.stat().st_size,
                "timestamp": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

        return screenshots

    def get_screenshot_count(self, session_id: int) -> int:
        """Count screenshots for a session."""
        session_dir = self.base_dir / str(session_id)
        if not session_dir.exists():
            return 0
        return len(list(session_dir.glob("*.png")))

    def get_screenshot_bytes(self, session_id: int, filename: str) -> bytes | None:
        """Read a specific screenshot file."""
        filepath = self.base_dir / str(session_id) / filename
        if filepath.exists():
            return filepath.read_bytes()
        return None

    def cleanup_old(self, days: int = 30):
        """Delete screenshot directories older than N days."""
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0

        for d in self.base_dir.iterdir():
            if d.is_dir() and d.name.isdigit():
                # Check modification time of directory
                mtime = datetime.fromtimestamp(d.stat().st_mtime)
                if mtime < cutoff:
                    shutil.rmtree(d)
                    removed += 1

        if removed:
            logger.info("Cleaned up %d old screenshot directories (>%d days)", removed, days)
        return removed
