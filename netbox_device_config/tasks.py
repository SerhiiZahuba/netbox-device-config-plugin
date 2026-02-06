from django_rq import job
from django.utils import timezone
#from .models import DeviceCredential, DeviceConfigHistory, DeviceBackupTask, BackupCommandSetting
from .models import DeviceCredential, DeviceBackupTask, BackupCommandSetting
from .git_utils import save_config_to_git

import paramiko
import time


@job("default", timeout=1200)
def run_backup_task(task_id):

    task = DeviceBackupTask.objects.get(id=task_id)

    def append_log(msg):
        task.log = (task.log or "") + f"{timezone.now()} - {msg}\n"
        task.save(update_fields=["log"])

    append_log("Task started")

    task.started_at = timezone.now()
    task.status = "running"
    task.save(update_fields=["started_at", "status"])

    cred = task.credential
    template = cred.template  # FK to BackupCommandSetting

    # --- ЛОГУЄМО ШАБЛОН ---
    if template:
        append_log(f"Using template: {template.vendor}")
        commands = [cmd.strip() for cmd in template.commands.splitlines() if cmd.strip()]
        append_log(f"Commands ({len(commands)}):")
        for cmd in commands:
            append_log(f"  - {cmd}")
    else:
        append_log("ERROR: No template assigned to credential")
        task.status = "error"
        task.error_message = "Device credential has no assigned template"
        task.save(update_fields=["status", "error_message"])
        return

    try:
        append_log(f"Connecting to {cred.host}:{cred.port} as {cred.username}")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=cred.host,
            port=int(cred.port),
            username=cred.username,
            password=cred.password,
            timeout=20,
            banner_timeout=20,
            auth_timeout=20,
            look_for_keys=False,
            allow_agent=False
        )


        append_log("SSH connection established, starting session")

        transport = client.get_transport()

        output = ""
        for cmd in commands:
            append_log(f"Executing: {cmd}")

            channel = transport.open_session()
            channel.settimeout(20)
            channel.exec_command(cmd)

            chunk = b""
            start = time.time()

            while True:
                if channel.recv_ready():
                    chunk += channel.recv(65535)

                if channel.exit_status_ready():
                    break

                if time.time() - start > 60:
                    append_log(f"ERROR: Command timeout after 60 seconds: {cmd}")
                    raise Exception(f"Timeout on command: {cmd}")

                time.sleep(1)

            decoded = chunk.decode(errors="ignore")
            append_log(f"Received {len(decoded)} bytes")
            output += f"# COMMAND: {cmd}\n{decoded}\n\n"

        client.close()

        config_data = output

        append_log("Saving config to git")

        commit = save_config_to_git(task.device, config_data)

        append_log(f"Committed to git: {commit}")

        task.git_commit = commit
        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.status = "success"
        task.save()

        append_log("Backup completed successfully")

    except Exception as e:
        append_log(f"ERROR: {str(e)}")

        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.status = "error"
        task.error_message = str(e)
        task.save(update_fields=["finished_at", "duration", "status", "error_message"])

