from django.db import models
from dcim.models import Device

class DeviceCredential(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=22)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.device.name} ({self.username}@{self.host}:{self.port})"


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

