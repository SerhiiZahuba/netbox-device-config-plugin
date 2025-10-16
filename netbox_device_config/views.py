from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from .models import DeviceCredential
from dcim.models import Device
import paramiko
from django.contrib import messages
from django.utils import timezone
from .models import DeviceCredential, DeviceConfigHistory, DeviceConfigHistory
import difflib
from datetime import datetime
from django.http import HttpResponse
from .models import DeviceConfigHistory
from django.db.models import Sum, Count
from django.utils.timezone import now, localdate
from django.http import HttpResponse
from netbox.views import generic
from utilities.views import ViewTab, register_model_view

@register_model_view(Device, name="config", path="config")
class DeviceConfigTabView(generic.ObjectView):
    """
    Tab "Config"
    """
    queryset = Device.objects.all()

    tab = ViewTab(
        label="Config",
        badge=lambda obj: DeviceConfigHistory.objects.filter(device=obj).count(),
        permission="netbox_device_config.view_deviceconfighistory",
    )

    def get(self, request, *args, **kwargs):
        device = get_object_or_404(Device, pk=kwargs.get("pk"))
        history = (
            DeviceConfigHistory.objects.filter(device=device)
            .order_by("-created_at")[:20]
        )

        return render(
            request,
            "netbox_device_config/device_config_tab.html",
            {
                "object": device,
                "tab": self.tab,
                "history": history,
            },
        )

def _human_size(num):
    if num < 1024:
        return f"{num} B"
    elif num < 1024 * 1024:
        return f"{num / 1024:.1f} KB"
    elif num < 1024 * 1024 * 1024:
        return f"{num / (1024 * 1024):.1f} MB"
    else:
        return f"{num / (1024 * 1024 * 1024):.2f} GB"

class BackupStatisticsView(View):
    def get(self, request):
        today = localdate(now())

        total_backups = DeviceConfigHistory.objects.count()
        today_backups = DeviceConfigHistory.objects.filter(created_at__date=today).count()
        total_size_raw = DeviceConfigHistory.objects.aggregate(total_size=Sum("size"))["total_size"] or 0

        total_size = _human_size(total_size_raw)

        failed_backups = 0

        return render(request, "netbox_device_config/statistics.html", {
            "today_backups": today_backups,
            "total_backups": total_backups,
            "total_size": total_size,
            "failed_backups": failed_backups,
        })


def download_config(request, config_id):
    conf = get_object_or_404(DeviceConfigHistory, id=config_id)
    filename = f"{conf.device.name}_{conf.created_at.strftime('%Y%m%d_%H%M%S')}.rsc"

    response = HttpResponse(conf.config, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response



def backup_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    config_data = f"# dummy backup {datetime.now()}\ninterface ether1\n ip address=10.0.0.1/24"
    DeviceConfigHistory.objects.create(device=device, config=config_data)
    return redirect(device.get_absolute_url())

def view_config(request, config_id):
    conf = get_object_or_404(DeviceConfigHistory, id=config_id)
    return render(request, "netbox_device_config/config_content.html", {"conf": conf})


def compare_config(request, config_id):
    conf_new = get_object_or_404(DeviceConfigHistory, id=config_id)
    conf_old = (
        DeviceConfigHistory.objects
        .filter(device=conf_new.device, created_at__lt=conf_new.created_at)
        .order_by('-created_at')
        .first()
    )
    diff = ''
    if conf_old:
        diff = '\n'.join(difflib.unified_diff(
            conf_old.config.splitlines(),
            conf_new.config.splitlines(),
            fromfile=str(conf_old.created_at),
            tofile=str(conf_new.created_at),
            lineterm=''
        ))
    return render(request, 'netbox_device_config/compare_config.html', {
        'device': conf_new.device,
        'diff': diff or 'No previous config found',
    })

class DeviceCredentialBackupView(View):
    """
    Connect to MikroTik via SSH and run 'export compact'
    """
    def get(self, request, pk):
        cred = DeviceCredential.objects.get(pk=pk)
        output = ""

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=cred.host,
                port=cred.port,
                username=cred.username,
                password=cred.password,
                timeout=10
            )

            stdin, stdout, stderr = client.exec_command("export compact")
            output = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")

            if not output.strip() and err:
                raise Exception(err.strip())

            # save to history
            DeviceConfigHistory.objects.create(
                device=cred.device,
                config=output,
                size=len(output.encode("utf-8")),
                created_at=timezone.now(),
            )

            messages.success(request, f"Backup successful for {cred.device.name} ({cred.host})")
        except Exception as e:
            messages.error(request, f"Backup failed: {e}")
        finally:
            try:
                client.close()
            except:
                pass

        return redirect("plugins:netbox_device_config:devicecredential_list")

class DeviceCredentialTestView(View):
    """
    Test SSH connectivity for given credential
    """
    def get(self, request, pk):
        cred = DeviceCredential.objects.get(pk=pk)

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=cred.host,
                port=cred.port,
                username=cred.username,
                password=cred.password,
                timeout=5
            )
            client.close()
            messages.success(request, f"SSH connection to {cred.host} successful!")
        except Exception as e:
            messages.error(request, f"SSH connection failed: {e}")

        return redirect("plugins:netbox_device_config:devicecredential_list")


class DeviceCredentialCreateView(View):
    """
    Create new device credential
    """
    def get(self, request):
        devices = Device.objects.all().order_by("name")
        return render(request, "netbox_device_config/credential_add.html", {"devices": devices})

    def post(self, request):
        device_id = request.POST.get("device")
        host = request.POST.get("host")
        port = request.POST.get("port")
        username = request.POST.get("username")
        password = request.POST.get("password")

        DeviceCredential.objects.create(
            device_id=device_id,
            host=host,
            port=port,
            username=username,
            password=password,
        )
        return redirect("plugins:netbox_device_config:devicecredential_list")

class DeviceCredentialEditView(View):
    """
    Edit existing credential
    """
    def get(self, request, pk):
        cred = DeviceCredential.objects.get(pk=pk)
        devices = Device.objects.all().order_by("name")
        return render(request, "netbox_device_config/credential_edit.html", {
            "cred": cred,
            "devices": devices,
        })

    def post(self, request, pk):
        cred = DeviceCredential.objects.get(pk=pk)
        cred.device_id = request.POST.get("device")
        cred.host = request.POST.get("host")
        cred.port = request.POST.get("port")
        cred.username = request.POST.get("username")
        cred.password = request.POST.get("password")
        cred.save()
        return redirect("plugins:netbox_device_config:devicecredential_list")

class DeviceCredentialListView(View):
    """
    Show all stored device credentials.
    """
    def get(self, request):
        creds = DeviceCredential.objects.all()
        return render(request, 'netbox_device_config/credentials_list.html', {
            'table': creds,
        })

class DeviceConfigHistoryListView(View):
    """
    Show configuration history for all devices.
    """
    def get(self, request):
        history = DeviceConfigHistory.objects.all()
        return render(request, 'netbox_device_config/history_list.html', {
            'table': history,
        })
