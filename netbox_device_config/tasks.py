from django_rq import job
from django.utils import timezone
from .models import DeviceCredential, DeviceBackupTask, BackupCommandSetting
from .git_utils import save_config_to_git
from .drivers.factory import run_driver



# =====================================================
# SCHEDULER TICK
# =====================================================

@job("default", timeout=300)
def scheduler_tick():
    run_scheduler()


# =====================================================
# MAIN BACKUP TASK
# =====================================================

@job("default", timeout=1800)
def run_backup_task(task_id):

    task = DeviceBackupTask.objects.get(id=task_id)

    def append_log(msg):
        task.log = (task.log or "") + f"{timezone.now()} - {msg}\n"
        task.save(update_fields=["log"])

    try:

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

        platform_slug = getattr(getattr(task.device, "platform", None), "slug", None)
        append_log(f"Platform slug: {platform_slug}")


        # =====================================================
        # RUN DRIVER
        # =====================================================
        append_log("Starting driver")

        output = run_driver(
            device=task.device,
            template_vendor=template.vendor,
            cred=cred,
            commands=commands,
            append_log=append_log,
        )


        if not output:
            raise Exception("Empty config received from device")

        append_log(f"Driver completed, received {len(output)} bytes")

        # =====================================================
        # SAVE TO GIT
        # =====================================================
        append_log("Saving config to git")

        commit = save_config_to_git(task.device, output)

        if commit:
            append_log(f"Git commit: {commit}")
            task.status = "success"
            task.git_commit = commit
        else:
            append_log("No config changes detected")
            task.status = "no_changes"

        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.save()

        append_log("Backup completed successfully")

    except Exception as e:

        append_log(f"ERROR: {str(e)}")

        task.finished_at = timezone.now()
        task.duration = (task.finished_at - task.started_at).total_seconds()
        task.status = "error"
        task.error_message = str(e)
        task.save(update_fields=["finished_at", "duration", "status", "error_message"])
