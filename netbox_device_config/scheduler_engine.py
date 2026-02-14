from django.utils import timezone
from datetime import timedelta
from .models import BackupSchedule, DeviceCredential, DeviceBackupTask
from .tasks import run_backup_task
from django.db.models import Q



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

        elif s.virtual_machine:
            creds = DeviceCredential.objects.filter(virtual_machine=s.virtual_machine)

        else:
            creds = DeviceCredential.objects.all()




        # -------------------------------------------------
        # CREATE TASK FOR EACH
        # -------------------------------------------------
        for cred in creds:

            print("DEBUG cred id:", cred.id)
            print("DEBUG device:", cred.device)
            print("DEBUG vm:", cred.virtual_machine)

            task = DeviceBackupTask.objects.create(
                device_id=cred.device_id,
                virtual_machine_id=cred.virtual_machine_id,
                credential=cred,
                status="queued",
                queued_at=timezone.now(),
            )



        # -------------------------------------------------
        # LAST RUN
        # -------------------------------------------------
        s.last_run = timezone.now()
        s.save()
