from django.db import models
from dcim.models import Device
from dcim.models import Platform



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


class DeviceConfigHistory(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    config = models.TextField()
    size = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.device.name} ({self.created_at})"

    def human_size(self):
        
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.1f} MB"

