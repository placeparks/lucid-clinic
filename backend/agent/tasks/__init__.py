"""Lucid Clinic — Agent Task Definitions."""

from agent.tasks.sync_patients import SyncPatientsTask
from agent.tasks.book_appointment import BookAppointmentTask
from agent.tasks.update_record import UpdateRecordTask

TASK_REGISTRY = {
    "sync_patients": SyncPatientsTask,
    "book_appointment": BookAppointmentTask,
    "update_record": UpdateRecordTask,
}
