from netbox.plugins import PluginTemplateExtension

class DeviceConfigTab(PluginTemplateExtension):
    model = "dcim.device"

    def right_page(self):
        return ""

template_extensions = [DeviceConfigTab]
