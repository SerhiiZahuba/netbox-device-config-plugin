**NetBox Device Config Plugin**

A NetBox plugin that enables network device configuration backups directly from the NetBox interface.
The plugin uses Paramiko (SSH) to connect to devices and retrieve configurations, currently tested with MikroTik and Cisco devices.

🔧 **Features**
✅ What the plugin can do now

Manual backup of device configurations from the NetBox UI

Command templates for different device types (e.g., MikroTik, Cisco)

Backup history display inside NetBox

Storage of backups in the database for easy access and versioning

🚀 **Roadmap / Future Plans**

Automated scheduled backups (cron-based or NetBox jobs integration)

Support for additional device vendors (Juniper, Fortinet, etc.)

Push configurations to Git repositories (e.g., GitLab, GitHub, or Gitea)

Full multi-vendor command and connection handling


**Installation**
cd /opt/netbox/netbox/
source ../venv/bin/activate



Add the plugin to your NetBox configuration (configuration.py):

PLUGINS = [
    "netbox_device_config",
]

PLUGINS_CONFIG = {
    "netbox_device_config": {
        "enable_backup": True,
    }
}


Then apply migrations:

python3 manage.py migrate netbox_device_config


Restart NetBox:

```sudo systemctl restart netbox```


Usage

Go to Plugins → Device Config Backup in the NetBox navigation menu.

Add command templates for each vendor or device type.

Assign a template to a device and initiate a manual backup.

View stored configurations and backup history from the plugin’s interface.

🧠 Requirements

NetBox 4.x or newer

Python 3.10+

Paramiko library (installed automatically)

SSH access to target devices
