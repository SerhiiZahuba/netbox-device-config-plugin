from . import tplink, ciscosmb, mikrotik, ciscoios


PLATFORM_DRIVER_MAP = {

    # TP-Link
    "tplink-jetstream": "tplink",
    "tplink": "tplink",

    # Cisco
    "cisco-ios": "ciscoios",
    "cisco-iosxe": "ciscoios",
    "cisco-smb": "ciscosmb",

    # MikroTik
    "mikrotik-routeros": "mikrotik",
    "routeros": "mikrotik",
    "mikrotik": "mikrotik",
    "ros-mikrotik": "mikrotik",
}


def detect_driver(target, template_vendor=None):
    """
    target = Device або VirtualMachine
    """

    slug = None

    # Device
    if getattr(target, "platform", None):
        slug = getattr(target.platform, "slug", None)

    # VM — платформа може бути тут
    if not slug and hasattr(target, "platform"):
        slug = getattr(target.platform, "slug", None)

    if slug:
        driver = PLATFORM_DRIVER_MAP.get(slug)
        if driver:
            return driver

    # fallback — по template.vendor
    vendor = (template_vendor or "").lower()

    if "tplink" in vendor:
        return "tplink"

    if "cisco" in vendor:
        return "ciscoios"

    if "mikrotik" in vendor:
        return "mikrotik"

    return None



def run_driver(target, template_vendor, cred, commands, append_log):
    """
    target = Device або VirtualMachine
    """

    driver = detect_driver(target, template_vendor)

    append_log(f"Selected driver: {driver}")

    if not driver:
        raise Exception(
            f"No driver matched. target={target}, template_vendor={template_vendor}"
        )

    # ==============================
    # TP-LINK
    # ==============================
    if driver == "tplink":
        return tplink.run_backup(cred, append_log)

    # ==============================
    # CISCO IOS
    # ==============================
    if driver == "ciscoios":
        return ciscoios.run_backup(cred, commands, append_log)

    # ==============================
    # CISCO SMB
    # ==============================
    if driver == "ciscosmb":
        return ciscosmb.run_backup(cred, commands, append_log)

    # ==============================
    # MIKROTIK
    # ==============================
    if driver == "mikrotik":
        return mikrotik.run_backup(cred, commands, append_log)

    raise Exception(f"Driver {driver} not implemented")
