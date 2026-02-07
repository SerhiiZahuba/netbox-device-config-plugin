from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label="Device Config Backup",
    groups=(
        ("Device Config", (
            PluginMenuItem(link='plugins:netbox_device_config:devicecredential_list', link_text='Device List'),
            PluginMenuItem(link='plugins:netbox_device_config:backup_templates_list', link_text='Templates'),
            PluginMenuItem(link="plugins:netbox_device_config:backup_statistics", link_text="Statistics"),
            PluginMenuItem(link='plugins:netbox_device_config:config_search', link_text='Search Configs',),
            PluginMenuItem(link='plugins:netbox_device_config:git_settings', link_text='Settings'       ),
            PluginMenuItem(link='plugins:netbox_device_config:schedule_list', link_text='Scheduler',),
        )),
    ),
)
