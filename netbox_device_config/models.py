from django.db import models
from dcim.models import Device
from dcim.models import Platform


class DeviceBackupTask(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("success", "Success"),
        ("error", "Error"),
    ]

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="backup_tasks"
    )

    credential = models.ForeignKey(
        "DeviceCredential",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    duration = models.FloatField(null=True, blank=True)

    error_message = models.TextField(blank=True, null=True)
    log = models.TextField(blank=True, null=True)

    git_commit = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"Backup {self.device} ({self.status})"


class BackupCommandSetting(models.Model):
    vendor = models.CharField(
        max_length=100,
        unique=True,
        help_text="Device type or vendor name, e.g. Mikrotik, Cisco, Juniper"
    )
    commands = models.TextField(
        help_text="One or more backup commands, separated by new lines."
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.vendor}"

    def get_command_list(self):
        """Return list of commands (split by newlines, ignoring empty lines)."""
        return [cmd.strip() for cmd in self.commands.splitlines() if cmd.strip()]


class DeviceCredential(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=22)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=255)


    template = models.ForeignKey(
        BackupCommandSetting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credentials',
        help_text="Backup command template to use for this device"
    )

    def __str__(self):
        return f"{self.device.name} ({self.host})"






class GitSettings(models.Model):
    repo_url = models.CharField(max_length=500)
    branch = models.CharField(max_length=100, default="main")

    local_path = models.CharField(
        max_length=300,
        default="/opt/netbox/git-configs"
    )

    ssh_key_path = models.CharField(
        max_length=300,
        default="/opt/netbox/.ssh/id_rsa"
    )

    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.repo_url

class BackupSchedule(models.Model):

    SCHEDULE_CHOICES = [
        ("minutely", "Minutely"),
        ("hourly", "Hourly"),
        ("12h", "Every 12 hours"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Every 30 days"),
    ]

    name = models.CharField(max_length=100)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_CHOICES)
    time_of_day = models.TimeField(null=True, blank=True)
    day_of_week = models.IntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.schedule_type})"
