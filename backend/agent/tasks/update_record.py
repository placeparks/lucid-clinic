"""
Lucid Clinic — Update Patient Record Task
Updates patient contact information in EZBIS.

Per CLAUDE.md Section 7:
- WRITE operation — requires confirmation
- DNC patients are blocked (checked by TaskRunner)
- Only contact info fields can be updated (phone, email, address)
"""

from agent.tasks.base import BaseTask

ALLOWED_FIELDS = {"cell_phone", "alt_phone", "work_phone", "email", "address", "city", "state", "zip"}


class UpdateRecordTask(BaseTask):
    task_type = "update_record"
    requires_confirmation = True
    description = "Update patient contact information in EZBIS"

    system_prompt = BaseTask.system_prompt + (
        "\n## TASK CONTEXT: Patient Record Update\n"
        "You are updating a patient's contact information in EZBIS.\n\n"
        "Steps:\n"
        "1. Open the patient record by account ID\n"
        "2. Navigate to the contact information section\n"
        "3. Update ONLY the specified fields\n"
        "4. VERIFY the changes are correct before saving\n"
        "5. Save the record\n"
        "6. Take a final screenshot confirming the update\n\n"
        "IMPORTANT:\n"
        "- Only update the fields specified — do NOT change anything else\n"
        "- Do NOT modify clinical data, billing, or insurance information\n"
        "- Verify the patient account ID matches before making changes\n"
        "- Report exactly what was changed when done\n"
    )

    def build_prompt(self, params: dict) -> str:
        patient_id = params.get("patient_account_id", "UNKNOWN")
        patient_name = params.get("patient_name", "")
        fields = params.get("fields", {})

        prompt = (
            f"Please update the following contact information in EZBIS "
            f"for patient account {patient_id}"
        )
        if patient_name:
            prompt += f" ({patient_name})"
        prompt += ":\n\n"

        for field, value in fields.items():
            prompt += f"- {field}: {value}\n"

        prompt += (
            "\nStart by taking a screenshot to see the current state. "
            "Then open this patient's record and update only the fields listed above. "
            "Verify the changes before saving."
        )

        return prompt

    def validate_params(self, params: dict) -> tuple[bool, str]:
        if not params.get("patient_account_id"):
            return False, "patient_account_id is required"

        fields = params.get("fields", {})
        if not fields:
            return False, "fields dict is required with at least one field to update"

        invalid = set(fields.keys()) - ALLOWED_FIELDS
        if invalid:
            return False, f"Cannot update restricted fields: {', '.join(invalid)}. Allowed: {', '.join(sorted(ALLOWED_FIELDS))}"

        return True, ""

    def parse_result(self, agent_result: dict) -> dict:
        base = super().parse_result(agent_result)
        base["task_type"] = self.task_type
        base["updated"] = agent_result.get("status") == "success"
        return base
