from django.db import models
from dcim.models import Device
from dcim.models import Platform
from virtualization.models import VirtualMachine




class DeviceBackupTask(models.Model):

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    virtual_machine = models.ForeignKey(
        VirtualMachine,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    credential = models.ForeignKey(
        "DeviceCredential",
        on_delete=models.CASCADE
    )

    status = models.CharField(max_length=20, default="queued")
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    duration = models.FloatField(null=True, blank=True)
    log = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    git_commit = models.CharField(max_length=64, null=True, blank=True)


    def __str__(self):
        return f"Backup {self.device} ({self.status})"

    @property
    def target(self):
        return self.device or self.virtual_machine

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

    device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    virtual_machine = models.ForeignKey(
        VirtualMachine,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    host = models.CharField(max_length=255)
    port = models.IntegerField(default=22)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    template = models.ForeignKey(
        BackupCommandSetting,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )



    snmp_community = models.CharField(
        max_length=100,
        default="public",
        help_text="SNMP community string"
    )

    snmp_enable = models.BooleanField(
        default=False,
        help_text="Enable SNMP usage for this device"
    )

    def __str__(self):
        target = self.device or self.virtual_machine
        return f"{target} ({self.host})"








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
    virtual_machine = models.ForeignKey(
            VirtualMachine,
            null=True,
            blank=True,
            on_delete=models.CASCADE
        )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.schedule_type})"

