# 🧩 NetBox Device Config Plugin

A **NetBox plugin** that enables network device configuration backups directly from the NetBox interface.  
The plugin uses **Paramiko (SSH)**  and **Netmiko (SSH)** to connect to devices and retrieve configurations — currently tested with **MikroTik** and **Cisco** devices.

---

## 🔧 Features

### ✅ Current Capabilities
- Manual backup of device configurations from the **NetBox UI**
- Command templates for different device types (e.g., MikroTik, Cisco)
- Backup history display inside NetBox
- Storage of backups in the **database** for easy access and versioning

---

## 🚀 Roadmap / Future Plans
- 🔁 Automated scheduled backups (cron-based or NetBox jobs integration)
- 🌐 Support for additional device vendors (Juniper, Fortinet, etc.)
- 📤 Push configurations to **Git repositories** (GitLab, GitHub)
- 🧩 Multi-vendor command and connection handling

---

## ⚙️ Installation

```bash
cd /opt/netbox/netbox/
source ../venv/bin/activate
python3 -m pip install paramiko netmiko


Add the plugin to your NetBox configuration file (configuration.py):

PLUGINS = [
    "netbox_device_config",
]

PLUGINS_CONFIG = {
    "netbox_device_config": {
        "enable_backup": True,
    }
}
```

Then apply migrations:

python3 manage.py migrate netbox_device_config


Restart NetBox:

sudo systemctl restart netbox netbox-rq

🖥️ Usage

Navigate to Plugins → Device Config Backup in the NetBox navigation menu.

Add command templates for each vendor or device type.

Assign a template to a device and initiate a manual backup.

View stored configurations and backup history directly in the plugin interface.

🧠 Requirements

NetBox 4.x or newer

Python 3.10+

Paramiko and Netmiko library

SSH access to target devices
