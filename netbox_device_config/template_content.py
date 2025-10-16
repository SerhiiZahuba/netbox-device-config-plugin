from netbox.plugins import PluginTemplateExtension
from dcim.models import Device
from .models import DeviceConfigHistory

class DeviceConfigTab(PluginTemplateExtension):
    model = "dcim.device"

    def right_page(self):
        device = self.context.get("object")

        if not isinstance(device, Device):
            return ""

        history = (
            DeviceConfigHistory.objects
            .filter(device=device)
            .order_by("-created_at")[:5]
        )

        return self.render(
            "netbox_device_config/inc/device_config_tab.html",
            extra_context={"device": device, "history": history},
        )

template_extensions = [DeviceConfigTab]
