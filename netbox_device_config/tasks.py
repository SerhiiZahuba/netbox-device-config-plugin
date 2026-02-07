from django_rq import job
from django.utils import timezone
from .models import DeviceCredential, DeviceBackupTask, BackupCommandSetting
from .git_utils import save_config_to_git
#from .scheduler_engine import run_scheduler

import paramiko
import time


# =====================================================
# SCHEDULER TICK (крутиться кожну хвилину)
# =====================================================

@job("default", timeout=300)
def scheduler_tick():
    run_scheduler()


# =====================================================
# MAIN BACKUP TASK
# =====================================================

@job("default", timeout=1800)   # 30 min max
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
    template = cred.template

    # =====================================================
    # TEMPLATE CHECK
    # =====================================================
    if not template:
        append_log("ERROR: No template assigned")
        task.status = "error"
        task.error_message = "No template assigned"
        task.save(update_fields=["status", "error_message"])
        return

    append_log(f"Using template: {template.vendor}")

    commands = [c.strip() for c in template.commands.splitlines() if c.strip()]

    append_log(f"Commands ({len(commands)}):")
    for c in commands:
        append_log(f"  - {c}")

    # =====================================================
    # SSH CONNECT
    # =====================================================
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

        append_log("SSH connected")

        transport = client.get_transport()

        output = ""

        # =====================================================
        # RUN COMMANDS
        # =====================================================
        for cmd in commands:

            append_log(f"Executing: {cmd}")

            channel = transport.open_session()
            channel.settimeout(60)
            channel.exec_command(cmd)

            chunk = b""
            start = time.time()

            while True:

                if channel.recv_ready():
                    chunk += channel.recv(65535)

                if channel.exit_status_ready():
                    break

                if time.time() - start > 120:
                    raise Exception(f"Timeout on command: {cmd}")

                time.sleep(0.5)

            decoded = chunk.decode(errors="ignore")

            append_log(f"Received {len(decoded)} bytes")

            output += f"\n\n# COMMAND: {cmd}\n{decoded}"

        client.close()

        # =====================================================
        # SAVE TO GIT
        # =====================================================
        append_log("Saving config to git")

        commit = save_config_to_git(task.device, output)

        append_log(f"Git commit: {commit}")

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
