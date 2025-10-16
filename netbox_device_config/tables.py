import django_tables2 as tables
from .models import DeviceCredential, DeviceConfigHistory

class DeviceCredentialTable(tables.Table):
    class Meta:
        model = DeviceCredential
        fields = ('device', 'host', 'port', 'username')

class DeviceConfigHistoryTable(tables.Table):
    class Meta:
        model = DeviceConfigHistory
        fields = ('device', 'created_at')
