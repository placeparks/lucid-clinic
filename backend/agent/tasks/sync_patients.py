"""
Lucid Clinic — Sync Patients Task
Auto-syncs patient data from EZBIS into the Lucid database.
Replaces the manual CSV export workflow.

Per CLAUDE.md: This is a READ-ONLY operation — no confirmation required.
"""

from agent.tasks.base import BaseTask


class SyncPatientsTask(BaseTask):
    task_type = "sync_patients"
    requires_confirmation = False
    description = "Sync patient data from EZBIS to Lucid database"

    system_prompt = BaseTask.system_prompt + (
        "\n## TASK CONTEXT: Patient Data Sync\n"
        "You are syncing patient data from EZBIS. This is a READ-ONLY operation.\n\n"
        "EZBIS Survey Generator is the tool used to export patient data:\n"
        "1. From the EZBIS main menu, click 'Reports' or 'Survey Generator'\n"
        "2. In Survey Generator, select 'All Patients' or the appropriate filter\n"
        "3. Click the export/generate button to create the data file\n"
        "4. The export file (EZMERGE.DAT) will be saved to the configured location\n\n"
        "IMPORTANT:\n"
        "- Do NOT modify any patient records during this process\n"
        "- Do NOT change any EZBIS settings\n"
        "- If you encounter any errors, take a screenshot and report them\n"
        "- Report the number of records exported when complete\n"
    )

    def build_prompt(self, params: dict) -> str:
        prompt = (
            "Please sync patient data from EZBIS by exporting via the Survey Generator. "
            "Start by taking a screenshot to see the current state of the screen. "
            "Then navigate to the Survey Generator in EZBIS and export all patient data. "
            "Report back when the export is complete, including the number of records exported."
        )

        if params.get("filter_tier"):
            prompt += f"\nOnly export patients in the '{params['filter_tier']}' tier."

        return prompt

    def validate_params(self, params: dict) -> tuple[bool, str]:
        # Sync has no required params
        allowed_tiers = {"active", "warm", "cool", "cold", "dormant", None}
        if params.get("filter_tier") and params["filter_tier"] not in allowed_tiers:
            return False, f"Invalid tier filter: {params.get('filter_tier')}"
        return True, ""

    def parse_result(self, agent_result: dict) -> dict:
        base = super().parse_result(agent_result)
        base["task_type"] = self.task_type
        base["records_synced"] = 0  # Will be parsed from final_text in production
        return base
