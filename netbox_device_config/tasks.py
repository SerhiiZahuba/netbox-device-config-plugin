from django_rq import job
from .models import DeviceCredential, DeviceConfigHistory, DeviceBackupTask
import paramiko
from datetime import datetime
from django.utils import timezone



@job("default", timeout=1200)
def run_backup_task(task_id):

    task = DeviceBackupTask.objects.get(id=task_id)

    # Internal logging helper
    def append_log(text):
        task.log = (task.log or "") + f"{timezone.now()} - {text}\n"
        task.save(update_fields=["log"])

    # Task started
    append_log("Task started")
    task.started_at = timezone.now()
    task.status = "running"
    task.save(update_fields=["started_at", "status"])

    # Credential
    cred = task.credential

    try:
        append_log(f"Connecting to {cred.host}:{cred.port} as {cred.username}")

        # SSH client init
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=cred.host,
            port=cred.port,
            username=cred.username,
            password=cred.password,
            timeout=30
        )

        append_log("SSH connection established")
        append_log("Executing backup command: export")

        # Execute command
        stdin, stdout, stderr = client.exec_command("export")
        config_data = stdout.read().decode(errors="ignore")
        client.close()

        append_log(f"Downloaded {len(config_data)} bytes of config")

        # Save config
        DeviceConfigHistory.objects.create(
            device=task.device,
            config=config_data,
            created_at=timezone.now()
        )

        # Mark success
        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.status = "success"
        task.save(update_fields=["finished_at", "duration", "status"])

        append_log("Backup completed successfully")

    except Exception as e:

        append_log(f"ERROR: {str(e)}")

        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.status = "error"
        task.error_message = str(e)
        task.save(update_fields=["finished_at", "duration", "status", "error_message"])




