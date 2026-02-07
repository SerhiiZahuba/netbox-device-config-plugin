from netbox.jobs import JobRunner, system_job
from django.utils import timezone
from .models import BackupSchedule, DeviceCredential, DeviceBackupTask
from .tasks import run_backup_task


@system_job(interval=1)  # кожну хвилину
class SchedulerRunner(JobRunner):

    class Meta:
        name = "Device backup scheduler"

    def run(self, *args, **kwargs):

        now = timezone.now()
        schedules = BackupSchedule.objects.filter(enabled=True)

        for s in schedules:

            if not s.last_run:
                should_run = True
            else:
                delta = now - s.last_run

                if s.schedule_type == "minutely":
                    should_run = delta.total_seconds() > 60
                elif s.schedule_type == "hourly":
                    should_run = delta.total_seconds() > 3600
                elif s.schedule_type == "12h":
                    should_run = delta.total_seconds() > 43200
                elif s.schedule_type == "daily":
                    should_run = delta.total_seconds() > 86400
                elif s.schedule_type == "weekly":
                    should_run = delta.total_seconds() > 604800
                elif s.schedule_type == "monthly":
                    should_run = delta.total_seconds() > 2592000
                else:
                    should_run = False

            if not should_run:
                continue

            if s.device:
                creds = DeviceCredential.objects.filter(device=s.device)
            else:
                creds = DeviceCredential.objects.all()

            for cred in creds:
                task = DeviceBackupTask.objects.create(
                    device=cred.device,
                    credential=cred,
                    status="queued",
                    queued_at=timezone.now(),
                )

                run_backup_task.delay(task.id)

            s.last_run = now
            s.save()

        return "Scheduler finished"
