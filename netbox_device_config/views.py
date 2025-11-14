from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from .models import DeviceCredential, BackupCommandSetting
from dcim.models import Device, Platform
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
import time
from .models import DeviceBackupTask
from .tasks import run_backup_task



class BackupTasksListView(View):
    def get(self, request):
        results = TaskResult.objects.filter(task_name="netbox_device_config.tasks.run_device_backup")\
                                    .order_by("-date_created")[:50]

        tasks = []
        for r in results:
            data = r.result or "{}"
            try:
                data = eval(data)
            except:
                data = {"status": "unknown"}

            tasks.append({
                "status": data.get("status", r.status),
                "device": data.get("device", "-"),
                "host": data.get("host", "-"),
                "error": data.get("error", None),
            })

        return render(request, "netbox_device_config/tasks_list.html", {"tasks": tasks})


def run_multicommand_backup(cred):
    commands = cred.template.commands.splitlines()
    output = ""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=cred.host,
        port=cred.port,
        username=cred.username,
        password=cred.password,
        timeout=10
    )

    # interactive shell
    chan = client.invoke_shell()
    time.sleep(0.7)  # give device time to open channel

    # run commands sequentially
    for cmd in commands:
        if not cmd.strip():
            continue
        chan.send(cmd + "\n")
        time.sleep(1.0)

    # read all output
    time.sleep(1.5)
    while chan.recv_ready():
        output += chan.recv(999999).decode("utf-8", errors="ignore")

    chan.close()
    client.close()

    return output



class BackupTemplatesListView(View):
    """Show all vendor backup commands"""
    def get(self, request):
        settings = BackupCommandSetting.objects.all().order_by("vendor")
        return render(request, "netbox_device_config/templates/templates_list.html", {"settings": settings})


class BackupTemplatesCreateView(View):
    """Add new vendor command template"""
    def get(self, request):
        return render(request, "netbox_device_config/templates/templates_add.html")

    def post(self, request):
        vendor = request.POST.get("vendor", "").strip()
        commands = request.POST.get("commands", "").strip()
        notes = request.POST.get("notes", "").strip()

        if not vendor or not commands:
            messages.error(request, "Vendor and commands are required.")
            return redirect("plugins:netbox_device_config:backup_templates_add")

        BackupCommandSetting.objects.create(
            vendor=vendor,
            commands=commands,   # <----- FIXED
            notes=notes if notes else None,
        )

        messages.success(request, f"Added backup commands for {vendor}")
        return redirect("plugins:netbox_device_config:backup_templates_list")


class BackupTemplatesEditView(View):
    """Edit existing vendor command template"""
    def get(self, request, pk):
        setting = get_object_or_404(BackupCommandSetting, pk=pk)
        return render(request, "netbox_device_config/templates/templates_edit.html", {
            "setting": setting
        })

    def post(self, request, pk):
        setting = get_object_or_404(BackupCommandSetting, pk=pk)

        setting.vendor = request.POST.get("vendor", "").strip()
        setting.commands = request.POST.get("commands", "").strip()   # <----- FIXED
        setting.notes = request.POST.get("notes", "").strip()

        if not setting.vendor or not setting.commands:
            messages.error(request, "Vendor and commands are required.")
            return redirect("plugins:netbox_device_config:backup_templates_edit", pk=pk)

        setting.save()

        messages.success(request, f"Updated backup commands for {setting.vendor}")
        return redirect("plugins:netbox_device_config:backup_templates_list")



class BackupTemplatesDeleteView(View):
    """Delete vendor command"""
    def post(self, request, pk):
        setting = get_object_or_404(BackupCommandSetting, pk=pk)
        messages.success(request, f"Deleted {setting.vendor}")
        setting.delete()
        return redirect("plugins:netbox_device_config:backup_templates_list")

        

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


class BackupTaskListView(View):
    def get(self, request):
        tasks = DeviceBackupTask.objects.order_by("-queued_at")[:200]
        return render(request, "netbox_device_config/task_history.html", {
            "tasks": tasks
        })

class BackupTaskDetailView(View):
    def get(self, request, pk):
        task = get_object_or_404(DeviceBackupTask, pk=pk)
        return render(request, "netbox_device_config/task_detail.html", {
            "task": task
        })


class DeviceCredentialBackupView(View):
    def get(self, request, pk):

        cred = DeviceCredential.objects.get(pk=pk)

        task = DeviceBackupTask.objects.create(
            device=cred.device,
            credential=cred,
            status="queued"
        )

        run_backup_task.delay(task.id)

        messages.success(request, "Backup queued!")
        return redirect("plugins:netbox_device_config:task_history")




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
        templates = BackupCommandSetting.objects.all().order_by("vendor")
        return render(request, "netbox_device_config/credential_add.html", {
            "devices": devices,
            "templates": templates,
        })

    def post(self, request):
        device_id = request.POST.get("device")
        host = request.POST.get("host")
        port = request.POST.get("port")
        username = request.POST.get("username")
        password = request.POST.get("password")
        template_id = request.POST.get("template")

        DeviceCredential.objects.create(
            device_id=device_id,
            host=host,
            port=port,
            username=username,
            password=password,
            template_id=template_id if template_id else None,
        )
        return redirect("plugins:netbox_device_config:devicecredential_list")

class DeviceCredentialEditView(View):
    """
    Edit existing device credential
    """
    def get(self, request, pk):
        cred = get_object_or_404(DeviceCredential, pk=pk)
        devices = Device.objects.all().order_by("name")
        templates = BackupCommandSetting.objects.all().order_by("vendor")

        return render(request, "netbox_device_config/credential_edit.html", {
            "cred": cred,
            "devices": devices,
            "templates": templates,
        })

    def post(self, request, pk):
        cred = get_object_or_404(DeviceCredential, pk=pk)

        cred.device_id = request.POST.get("device")
        cred.host = request.POST.get("host")
        cred.port = request.POST.get("port")
        cred.username = request.POST.get("username")
        cred.password = request.POST.get("password")

        
        template_id = request.POST.get("template")
        cred.template_id = template_id or None

        cred.save()

        messages.success(request, f"Updated credentials for {cred.device.name}")
        return redirect("plugins:netbox_device_config:devicecredential_list")


class DeviceCredentialListView(View):
    """
    Show all stored device credentials.
    """
    def get(self, request):
        creds = DeviceCredential.objects.all()
        return render(request, 'netbox_device_config/device_list.html', {
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
