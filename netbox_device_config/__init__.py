from netbox.plugins import PluginConfig

class DeviceConfigPluginConfig(PluginConfig):
    name = 'netbox_device_config'
    verbose_name = 'Device Config Backup'
    description = 'Fetch and store MikroTik configs using Netmiko'
    version = '1.0.0'
    author = 'Serhii Zahuba'
    author_email = 'dev@cre.com'
    base_url = 'device-config'
    required_settings = []
    default_settings = {}

    def ready(self):
        super().ready()
        from . import template_content, navigation


config = DeviceConfigPluginConfig
