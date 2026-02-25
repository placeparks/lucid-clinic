"""
Lucid Clinic — Base Task Definition
All agent tasks inherit from this class.
"""

from abc import ABC, abstractmethod


class BaseTask(ABC):
    """Base class for all agent tasks."""

    task_type: str = ""
    requires_confirmation: bool = False
    description: str = ""

    # System prompt gives Claude EZBIS-specific context
    system_prompt: str = (
        "You are an AI agent operating EZBIS chiropractic clinic software via screen control. "
        "You can see the screen, click, type, and use keyboard shortcuts. "
        "EZBIS is a Windows desktop application for patient management.\n\n"
        "RULES:\n"
        "- Always take a screenshot first to see the current state\n"
        "- After clicking or typing, take a screenshot to verify the result\n"
        "- If you see an unexpected screen or dialog, STOP and report it\n"
        "- Never delete any patient records\n"
        "- Never access billing or insurance claims screens\n"
        "- If you are unsure about any action, STOP and describe what you see\n"
        "- Report completion clearly when the task is done\n"
    )

    @abstractmethod
    def build_prompt(self, params: dict) -> str:
        """Build the task-specific prompt for Claude."""
        pass

    @abstractmethod
    def validate_params(self, params: dict) -> tuple[bool, str]:
        """
        Validate task parameters before execution.
        Returns (is_valid, error_message).
        """
        pass

    def parse_result(self, agent_result: dict) -> dict:
        """
        Extract structured results from the agent conversation.
        Override in subclasses for task-specific parsing.
        """
        return {
            "final_text": agent_result.get("final_text", ""),
            "iterations": agent_result.get("iterations", 0),
            "steps": agent_result.get("steps", 0),
        }
