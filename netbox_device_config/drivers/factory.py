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


def detect_driver(device, template_vendor=None):


    slug = None
    if getattr(device, "platform", None):
        slug = getattr(device.platform, "slug", None)

    if slug:
        driver = PLATFORM_DRIVER_MAP.get(slug)
        if driver:
            return driver


    vendor = (template_vendor or "").lower()

    if "tplink" in vendor:
        return "tplink"

    if "cisco" in vendor:
        return "ciscoios"

    if "mikrotik" in vendor:
        return "mikrotik"

    return None


def run_driver(device, template_vendor, cred, commands, append_log):

    driver = detect_driver(device, template_vendor)

    append_log(f"Selected driver: {driver}")

    if driver == "tplink":
        return tplink.run_backup(cred, append_log)

    if driver == "ciscoios":
        return ciscoios.run_backup(cred, commands, append_log)

    if driver == "ciscosmb":
        return ciscosmb.run_backup(cred, commands, append_log)

    if driver == "mikrotik":
        return mikrotik.run_backup(cred, commands, append_log)

    slug = getattr(getattr(device, "platform", None), "slug", None)
    raise Exception(f"No driver matched. platform.slug={slug!r}, template_vendor={template_vendor!r}")
