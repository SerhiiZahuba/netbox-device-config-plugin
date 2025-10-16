from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label="Device Config Backup",
    groups=(
        ("Device Config", (
            PluginMenuItem(link='plugins:netbox_device_config:devicecredential_list', link_text='Credentials'),
            PluginMenuItem(link='plugins:netbox_device_config:backup_settings_list', link_text='Settings'),
            PluginMenuItem(link="plugins:netbox_device_config:backup_statistics", link_text="Statistics"),
        )),
    ),
)
