from django_rq import job
from .models import DeviceCredential, DeviceConfigHistory, DeviceBackupTask
import paramiko
from datetime import datetime
from django.utils import timezone


@job("default")
def run_backup_task(task_id):
    task = DeviceBackupTask.objects.get(id=task_id)
    task.started_at = timezone.now()
    task.status = "running"
    task.save()

    cred = task.credential

    try:
        # SSH connect
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=cred.host,
            port=cred.port,
            username=cred.username,
            password=cred.password,
            timeout=10
        )

        stdin, stdout, stderr = client.exec_command("export")
        config = stdout.read().decode(errors="ignore")
        client.close()

        DeviceConfigHistory.objects.create(
            device=task.device,
            config=config,
            created_at=timezone.now()
        )

        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.status = "success"
        task.save()

        return {"status": "success"}

    except Exception as e:
        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.status = "error"
        task.error_message = str(e)
        task.save()

        return {"status": "error", "error": str(e)}
