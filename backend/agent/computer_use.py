"""
Lucid Clinic — Claude Computer Use Agent Loop
Core integration with Anthropic's Computer Use API.
Sends tasks to Claude, executes tool actions on VNC, returns results.

Per CLAUDE.md Section 7:
- Max session: 30 minutes
- Screenshot every action
- Failsafe on low confidence
"""

import base64
import time
import logging
from datetime import datetime, timedelta

from agent.vnc_controller import BaseVNCController
from agent.screenshot_logger import ScreenshotLogger

logger = logging.getLogger("lucid.agent.computer_use")

# Computer Use tool definition for the API
COMPUTER_TOOL = {
    "type": "computer_20250124",
    "name": "computer",
    "display_width_px": 1024,
    "display_height_px": 768,
    "display_number": 1,
}

BETA_HEADER = "computer-use-2025-01-24"
MODEL = "claude-sonnet-4-5-20241022"


class ComputerUseAgent:
    """
    Agent loop for Claude Computer Use.
    Sends tasks → gets tool_use → executes on VNC → returns tool_result → repeats.
    """

    def __init__(
        self,
        api_key: str,
        vnc: BaseVNCController,
        screenshot_logger: ScreenshotLogger,
        session_id: int,
        max_iterations: int = 20,
        max_minutes: int = 30,
        model: str = MODEL,
    ):
        self.api_key = api_key
        self.vnc = vnc
        self.screenshot_logger = screenshot_logger
        self.session_id = session_id
        self.max_iterations = max_iterations
        self.max_minutes = max_minutes
        self.model = model
        self._step = 0
        self._iterations = 0
        self._start_time: datetime | None = None

    def _check_timeout(self):
        """Enforce max session duration."""
        if self._start_time:
            elapsed = datetime.now() - self._start_time
            if elapsed > timedelta(minutes=self.max_minutes):
                raise TimeoutError(
                    f"Agent session exceeded {self.max_minutes} minute limit "
                    f"({elapsed.total_seconds():.0f}s elapsed)"
                )

    def _execute_action(self, action_input: dict) -> list[dict]:
        """
        Execute a computer use action and return tool_result content.
        Screenshots are logged after every action.
        """
        action = action_input.get("action", "")
        self._step += 1

        logger.info("Step %d: Executing action '%s'", self._step, action)

        if action == "screenshot":
            png_bytes = self.vnc.screenshot()
            self.screenshot_logger.log_screenshot(
                self.session_id, self._step, png_bytes, "screenshot"
            )
            b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
            return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}]

        elif action == "left_click":
            coord = action_input.get("coordinate", [0, 0])
            self.vnc.click(int(coord[0]), int(coord[1]))

        elif action == "double_click":
            coord = action_input.get("coordinate", [0, 0])
            self.vnc.double_click(int(coord[0]), int(coord[1]))

        elif action == "right_click":
            coord = action_input.get("coordinate", [0, 0])
            self.vnc.right_click(int(coord[0]), int(coord[1]))

        elif action == "type":
            text = action_input.get("text", "")
            self.vnc.type_text(text)

        elif action == "key":
            text = action_input.get("text", "")
            self.vnc.key(text)

        elif action == "mouse_move":
            coord = action_input.get("coordinate", [0, 0])
            self.vnc.mouse_move(int(coord[0]), int(coord[1]))

        elif action == "scroll":
            coord = action_input.get("coordinate", [0, 0])
            direction = action_input.get("scroll_direction", "down")
            amount = action_input.get("scroll_amount", 3)
            self.vnc.scroll(int(coord[0]), int(coord[1]), direction, amount)

        else:
            logger.warning("Unknown action: %s", action)
            return [{"type": "text", "text": f"Unknown action: {action}"}]

        # Take a follow-up screenshot after every non-screenshot action
        time.sleep(0.5)  # Brief pause for UI to update
        png_bytes = self.vnc.screenshot()
        self.screenshot_logger.log_screenshot(
            self.session_id, self._step, png_bytes, action
        )
        b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}]

    def run(self, system_prompt: str, task_prompt: str) -> dict:
        """
        Run the agent loop.

        Returns:
            {
                "status": "success" | "failed" | "timeout" | "max_iterations",
                "iterations": int,
                "steps": int,
                "messages": list,  # Full conversation history
                "final_text": str,  # Claude's final text response
                "error": str | None,
            }
        """
        self._start_time = datetime.now()
        self._step = 0
        self._iterations = 0

        # Import anthropic here to allow mock mode without the dependency
        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed")
            return {
                "status": "failed",
                "iterations": 0,
                "steps": 0,
                "messages": [],
                "final_text": "",
                "error": "anthropic package not installed. Run: pip install anthropic",
            }

        client = anthropic.Anthropic(api_key=self.api_key)

        messages = [{"role": "user", "content": task_prompt}]
        final_text = ""

        try:
            while self._iterations < self.max_iterations:
                self._iterations += 1
                self._check_timeout()

                logger.info("Iteration %d/%d", self._iterations, self.max_iterations)

                response = client.beta.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=[COMPUTER_TOOL],
                    messages=messages,
                    betas=[BETA_HEADER],
                )

                # Add assistant response to history
                response_content = []
                tool_uses = []

                for block in response.content:
                    if hasattr(block, "text"):
                        response_content.append({"type": "text", "text": block.text})
                        final_text = block.text
                    elif block.type == "tool_use":
                        response_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                        tool_uses.append(block)

                messages.append({"role": "assistant", "content": response_content})

                # If no tool uses, Claude is done
                if not tool_uses:
                    logger.info("Agent completed — no more tool requests")
                    return {
                        "status": "success",
                        "iterations": self._iterations,
                        "steps": self._step,
                        "messages": messages,
                        "final_text": final_text,
                        "error": None,
                    }

                # Execute each tool use and collect results
                tool_results = []
                for tool_use in tool_uses:
                    try:
                        result_content = self._execute_action(tool_use.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result_content,
                        })
                    except Exception as e:
                        logger.error("Action failed: %s", str(e))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                            "is_error": True,
                        })

                messages.append({"role": "user", "content": tool_results})

            # Max iterations reached
            logger.warning("Max iterations (%d) reached", self.max_iterations)
            return {
                "status": "max_iterations",
                "iterations": self._iterations,
                "steps": self._step,
                "messages": messages,
                "final_text": final_text,
                "error": f"Reached max iterations ({self.max_iterations})",
            }

        except TimeoutError as e:
            logger.warning("Session timeout: %s", str(e))
            return {
                "status": "timeout",
                "iterations": self._iterations,
                "steps": self._step,
                "messages": messages,
                "final_text": final_text,
                "error": str(e),
            }
        except Exception as e:
            logger.error("Agent error: %s", str(e), exc_info=True)
            return {
                "status": "failed",
                "iterations": self._iterations,
                "steps": self._step,
                "messages": messages,
                "final_text": final_text,
                "error": str(e),
            }


class MockComputerUseAgent:
    """
    Mock agent for development without Anthropic API.
    Simulates a successful agent run with mock data.
    """

    def __init__(self, vnc: BaseVNCController, screenshot_logger: ScreenshotLogger,
                 session_id: int, **kwargs):
        self.vnc = vnc
        self.screenshot_logger = screenshot_logger
        self.session_id = session_id

    def run(self, system_prompt: str, task_prompt: str) -> dict:
        logger.info("[MOCK AGENT] Running task: %s", task_prompt[:100])

        # Simulate 3 steps
        for step in range(1, 4):
            png_bytes = self.vnc.screenshot()
            self.screenshot_logger.log_screenshot(
                self.session_id, step, png_bytes, f"mock_step_{step}"
            )
            time.sleep(0.1)

        return {
            "status": "success",
            "iterations": 3,
            "steps": 3,
            "messages": [
                {"role": "user", "content": task_prompt},
                {"role": "assistant", "content": [{"type": "text", "text": "[MOCK] Task completed successfully. This is a simulated response."}]},
            ],
            "final_text": "[MOCK] Task completed successfully. Simulated 3 steps of EZBIS interaction.",
            "error": None,
        }
