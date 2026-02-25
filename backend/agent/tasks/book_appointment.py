"""
Lucid Clinic — Book Appointment Task
Books an appointment for a patient in EZBIS scheduler.

Per CLAUDE.md Section 7:
- WRITE operation — requires confirmation
- DNC patients are blocked (checked by TaskRunner)
- Agent must verify the booking before confirming
"""

from agent.tasks.base import BaseTask


class BookAppointmentTask(BaseTask):
    task_type = "book_appointment"
    requires_confirmation = True
    description = "Book an appointment for a patient in EZBIS"

    system_prompt = BaseTask.system_prompt + (
        "\n## TASK CONTEXT: Appointment Booking\n"
        "You are booking an appointment in the EZBIS scheduling system.\n\n"
        "Steps:\n"
        "1. Open the EZBIS scheduler/appointment book\n"
        "2. Navigate to the requested date\n"
        "3. Find the patient by account ID or name\n"
        "4. Select an available time slot\n"
        "5. Fill in the appointment details\n"
        "6. VERIFY the details are correct before saving\n"
        "7. Save the appointment\n"
        "8. Take a final screenshot confirming the booking\n\n"
        "IMPORTANT:\n"
        "- Double-check the patient name and date before saving\n"
        "- If the requested time slot is not available, report back with alternatives\n"
        "- Do NOT book if you are unsure about any details\n"
        "- Report the confirmed date, time, and provider when done\n"
    )

    def build_prompt(self, params: dict) -> str:
        patient_id = params.get("patient_account_id", "UNKNOWN")
        patient_name = params.get("patient_name", "")
        date = params.get("date", "")
        time = params.get("time", "")
        provider = params.get("provider", "")

        prompt = (
            f"Please book an appointment in EZBIS for the following patient:\n\n"
            f"- Patient Account ID: {patient_id}\n"
            f"- Patient Name: {patient_name}\n"
            f"- Requested Date: {date}\n"
        )

        if time:
            prompt += f"- Requested Time: {time}\n"
        else:
            prompt += "- Time: First available slot\n"

        if provider:
            prompt += f"- Provider: {provider}\n"

        prompt += (
            "\nStart by taking a screenshot to see the current state. "
            "Then navigate to the EZBIS scheduler and book this appointment. "
            "Verify all details before saving."
        )

        return prompt

    def validate_params(self, params: dict) -> tuple[bool, str]:
        if not params.get("patient_account_id"):
            return False, "patient_account_id is required"
        if not params.get("date"):
            return False, "date is required"
        return True, ""

    def parse_result(self, agent_result: dict) -> dict:
        base = super().parse_result(agent_result)
        base["task_type"] = self.task_type
        base["booked"] = agent_result.get("status") == "success"
        return base
