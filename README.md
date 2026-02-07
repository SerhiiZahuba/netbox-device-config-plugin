# 🧩 NetBox Device Config Plugin

A **NetBox plugin** that enables network device configuration backups directly from the NetBox interface.  
The plugin uses **Paramiko (SSH)** to connect to devices and retrieve configurations — currently tested with **MikroTik** and **Cisco** devices.

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
- 📤 Push configurations to **Git repositories** (GitLab, GitHub, Gitea)
- 🧩 Full multi-vendor command and connection handling

---

## ⚙️ Installation

```bash
cd /opt/netbox/netbox/
source ../venv/bin/activate
python3 -m pip install paramiko


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

sudo systemctl restart netbox

🖥️ Usage

Navigate to Plugins → Device Config Backup in the NetBox navigation menu.

Add command templates for each vendor or device type.

Assign a template to a device and initiate a manual backup.

View stored configurations and backup history directly in the plugin interface.

🧠 Requirements

NetBox 4.x or newer

Python 3.10+

Paramiko library (installed automatically)

SSH access to target devices

---

## 🤖 Development & Code Quality

This project uses automated code review and revision agents to maintain high code quality.

### Code Review Agent

Every Pull Request is automatically reviewed by our code review agent that checks for:
- 🔍 **Code Style**: PEP 8 compliance and Django best practices
- 🔐 **Security**: SQL injection, XSS, hardcoded secrets detection
- ⚡ **Performance**: Database query optimization, N+1 queries
- 🐛 **Logic**: Error handling, dead code, null pointer issues
- ✅ **Tests**: Test coverage and quality
- 📚 **Documentation**: Docstrings and documentation updates

For more details, see [.github/agents/README.md](.github/agents/README.md)
