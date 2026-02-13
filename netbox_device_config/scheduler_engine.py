from django.utils import timezone
from datetime import timedelta
from .models import BackupSchedule, DeviceCredential, DeviceBackupTask
from .tasks import run_backup_task


def should_run(schedule):

    now = timezone.now()

    if not schedule.enabled:
        return False

    if not schedule.last_run:
        return True

    delta = now - schedule.last_run

    if schedule.schedule_type == "minutely":
        return delta > timedelta(minutes=1)

    if schedule.schedule_type == "hourly":
        return delta > timedelta(hours=1)

    if schedule.schedule_type == "12h":
        return delta > timedelta(hours=12)

    if schedule.schedule_type == "daily":
        return delta > timedelta(days=1)

    if schedule.schedule_type == "weekly":
        return delta > timedelta(days=7)

    if schedule.schedule_type == "monthly":
        return delta > timedelta(days=30)

    return False


def run_scheduler():

    schedules = BackupSchedule.objects.filter(enabled=True)

    for s in schedules:

        if not should_run(s):
            continue

        # -------------------------------------------------
        # ВИБІР CREDENTIALS
        # -------------------------------------------------
        if s.device:
            creds = DeviceCredential.objects.filter(device=s.device)
        else:
            creds = DeviceCredential.objects.all()

        # -------------------------------------------------
        # CREATE TASK FOR EACH
        # -------------------------------------------------
        for cred in creds:

            task = DeviceBackupTask.objects.create(
                device=cred.device,
                virtual_machine=cred.virtual_machine,
                credential=cred,
                status="queued",
                queued_at=timezone.now(),
            )

            run_backup_task.delay(task.id)

        # -------------------------------------------------
        # LAST RUN
        # -------------------------------------------------
        s.last_run = timezone.now()
        s.save()
