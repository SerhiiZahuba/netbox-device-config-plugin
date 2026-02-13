import time
import subprocess
import difflib
import paramiko

from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from .models import DeviceCredential, BackupCommandSetting, GitSettings
from dcim.models import Device, Platform
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponse
from django.db.models import Sum, Count, Max, Q, F, Value
from django.utils.timezone import now, localdate, timedelta
from netbox.views import generic
from utilities.views import ViewTab, register_model_view
from .models import DeviceBackupTask
from .tasks import run_backup_task
from .models import BackupSchedule
from django.core.paginator import Paginator
from django.db.models import Q
from .git_utils import save_config_to_git, get_latest_config, get_config_size_map, get_config_by_commit
from virtualization.models import VirtualMachine
from django.db.models.functions import Coalesce



#from django.shortcuts import render, get_object_or_404
#from dcim.models import Device

#from .models import DeviceBackupTask
#from .git_utils import get_latest_config



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

    queryset = Device.objects.all()

    tab = ViewTab(
        label="Config",
        badge=None,
        permission="dcim.view_device",
    )



    def get(self, request, *args, **kwargs):
        device = get_object_or_404(Device, pk=kwargs.get("pk"))

        history_qs = (
            DeviceBackupTask.objects
            .filter(device=device, status="success")
            .order_by("-finished_at")
        )

        paginator = Paginator(history_qs, 10)

        page_number = request.GET.get("page")
        history_page = paginator.get_page(page_number)

        latest = history_qs.first()

        conf_size_map = get_config_size_map(device)

        for conf in history_page:
            conf.size = conf_size_map.get(conf.git_commit, 0)

        selected_commit = request.GET.get("commit")

        if selected_commit:
            selected = history_qs.filter(git_commit=selected_commit).first()
        else:
            selected = latest

        if selected and selected.git_commit:
            selected_config = get_config_by_commit(device, selected.git_commit)
        else:
            selected_config = None

        latest_config = get_latest_config(device)

        return render(
            request,
            "netbox_device_config/device_config_tab/device_config_tab.html",
            {
                "object": device,
                "tab": self.tab,
                "latest": latest,
                "history": history_page,
                "selected": selected,
                "selected_config": selected_config,
                "latest_config": latest_config,
            },
        )







class BackupStatisticsView(View):

    def get(self, request):

        today = now().date()
        yesterday = now() - timedelta(days=1)

        total_devices = Device.objects.count()

        total_backups = DeviceBackupTask.objects.filter(status="success").count()

        today_backups = (
            DeviceBackupTask.objects
            .filter(status="success", finished_at__date=today)
            .count()
        )

        failed_backups = DeviceBackupTask.objects.filter(status="error").count()

        # last backup per device
        last_backups = (
            DeviceBackupTask.objects
            .filter(status="success")
            .values("device")
            .annotate(last_time=Max("finished_at"))
        )

        devices_with_backup = last_backups.count()
        devices_without_backup = total_devices - devices_with_backup

        # no backup >24h
        stale_devices = Device.objects.exclude(
            id__in=DeviceBackupTask.objects.filter(
                status="success",
                finished_at__gte=yesterday
            ).values_list("device_id", flat=True)
        ).count()

        # ===== FILTERS =====
        filter_status = request.GET.get("status")

        tasks_qs = (
            DeviceBackupTask.objects
            .select_related("device")
            .order_by("-id")
        )

        if filter_status == "fail":
            tasks_qs = tasks_qs.filter(status="error")

        elif filter_status == "ok":
            tasks_qs = tasks_qs.filter(status="success")

        last_tasks = tasks_qs[:50]

        return render(request, "netbox_device_config/statistics/statistics.html", {
            "total_devices": total_devices,
            "total_backups": total_backups,
            "today_backups": today_backups,
            "failed_backups": failed_backups,
            "devices_without_backup": devices_without_backup,
            "stale_devices": stale_devices,
            "last_tasks": last_tasks,
            "filter_status": filter_status,
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

        per_page = request.GET.get("per_page", 10)

        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10

        if per_page not in [10, 25, 50, 100]:
            per_page = 10

        tasks_qs = DeviceBackupTask.objects.order_by("-queued_at")

        paginator = Paginator(tasks_qs, per_page)

        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(request, "netbox_device_config/task/task_history.html", {
            "tasks": page_obj,
            "page_obj": page_obj,
            "per_page": per_page,
        })

class BackupTaskDetailView(View):
    def get(self, request, pk):

        task = get_object_or_404(DeviceBackupTask, pk=pk)

        target = task.device or task.virtual_machine

        return render(
            request,
            "netbox_device_config/task/task_detail.html",
            {
                "task": task,
                "target": target,
            }
        )



class DeviceCredentialBackupView(View):
    def get(self, request, pk):

        cred = DeviceCredential.objects.get(pk=pk)

        if not cred.device and not cred.virtual_machine:
                    messages.error(request, "Credential has no device or VM")
                    return redirect("plugins:netbox_device_config:devicecredential_list")

        task = DeviceBackupTask.objects.create(
                   device=cred.device if cred.device else None,
                   virtual_machine=cred.virtual_machine if cred.virtual_machine else None,
                   credential=cred,
                   status="queued",
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
    Create new device
    """
    def get(self, request):
            devices = Device.objects.all().order_by("name")
            vms = VirtualMachine.objects.all().order_by("name")
            templates = BackupCommandSetting.objects.all().order_by("vendor")

            return render(
                request,
                "netbox_device_config/device/device_add.html",
                {
                    "devices": devices,
                    "vms": vms,
                    "templates": templates,
                },
            )

    def post(self, request):
        target = request.POST.get("device")
        host = request.POST.get("host")
        port = request.POST.get("port")
        username = request.POST.get("username")
        password = request.POST.get("password")
        template_id = request.POST.get("template")

        device = None
        vm = None

        if target:
            obj_type, obj_id = target.split(":")

            if obj_type == "device":
                device = Device.objects.get(id=obj_id)

            elif obj_type == "vm":
                vm = VirtualMachine.objects.get(id=obj_id)

        DeviceCredential.objects.create(
            device=device,
            virtual_machine=vm,   # ← нове поле
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

        return render(request, "netbox_device_config/device/device_edit.html", {
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

        # 🔽 SNMP
        cred.snmp_community = request.POST.get("snmp_community") or "public"
        cred.snmp_enable = bool(request.POST.get("snmp_enable"))

        cred.save()

        messages.success(request, f"Updated credentials for {cred.device.name}")
        return redirect("plugins:netbox_device_config:devicecredential_list")











class DeviceCredentialListView(View):

    def get(self, request):

        search = request.GET.get("q", "")
        per_page = request.GET.get("per_page", 10)

        try:
            per_page = int(per_page)
        except:
            per_page = 10

        if per_page not in [10, 25, 50, 100]:
            per_page = 10

        # -------------------------------------------------
        # QUERY
        # -------------------------------------------------
        creds = (
            DeviceCredential.objects
            .select_related("device", "virtual_machine", "template")

            .annotate(
                target_name=Coalesce(
                    F("device__name"),
                    F("virtual_machine__name"),
                    Value("")
                )
            )
            .order_by("target_name")
        )

        # -------------------------------------------------
        # SEARCH
        # -------------------------------------------------
        if search:
            creds = creds.filter(
                Q(device__name__icontains=search) |
                Q(device__id__icontains=search) |
                Q(virtual_machine__name__icontains=search) |
                Q(virtual_machine__id__icontains=search) |
                Q(host__icontains=search)
            )

        # -------------------------------------------------
        # PAGINATION
        # -------------------------------------------------
        paginator = Paginator(creds, per_page)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(
            request,
            "netbox_device_config/device/device_list.html",
            {
                "table": page_obj,
                "page_obj": page_obj,
                "search": search,
                "per_page": per_page,
            }
        )



class DeviceConfigHistoryListView(View):
    """
    Show configuration history for all devices.
    """
    def get(self, request):
        history = DeviceConfigHistory.objects.all()
        return render(request, 'netbox_device_config/history_list.html', {
            'table': history,
        })





class ConfigSearchView(View):

    def get(self, request):

        q = request.GET.get("q", "").strip()
        results = []

        if q:

            backups = (
                DeviceConfigHistory.objects
                .select_related("device")
                .order_by("-created_at")[:500]
            )

            for b in backups:

                lines = b.config.splitlines()

                for i, line in enumerate(lines):

                    if q.lower() in line.lower():

                        start = max(i - 2, 0)
                        end = min(i + 3, len(lines))

                        snippet = "\n".join(lines[start:end])

                        results.append({
                            "device": b.device,
                            "backup_id": b.id,
                            "date": b.created_at,
                            "snippet": snippet,
                        })

        return render(request, "netbox_device_config/config_search.html", {
            "q": q,
            "results": results[:200],
        })


class GitSettingsView(View):

    def get(self, request):
        settings = GitSettings.objects.first()
        return render(request, "netbox_device_config/git/git_settings.html", {
            "settings": settings
        })

    def post(self, request):
        obj, _ = GitSettings.objects.get_or_create(id=1)

        obj.repo_url = request.POST.get("repo_url")
        obj.branch = request.POST.get("branch")
        obj.local_path = request.POST.get("local_path")
        obj.ssh_key_path = request.POST.get("ssh_key_path")
        obj.enabled = bool(request.POST.get("enabled"))

        obj.save()

        messages.success(request, "Git settings saved")
        return redirect("plugins:netbox_device_config:git_settings")




class DeviceGitDiffView(View):

    def get(self, request, device_id):

        device = get_object_or_404(Device, id=device_id)
        settings = GitSettings.objects.first()

        repo = settings.local_path
        filename = f"{device.name}.cfg"

        try:
            diff = subprocess.check_output(
                f"git diff HEAD~1 {filename}",
                shell=True,
                cwd=repo
            ).decode(errors="ignore")
        except Exception:
            diff = "No previous diff available"

        return render(request, "netbox_device_config/git/git_diff.html", {
            "device": device,
            "diff": diff
        })


class DeviceGitShowView(View):

    def get(self, request, device_id):

        device = get_object_or_404(Device, id=device_id)
        settings = GitSettings.objects.first()

        path = f"{settings.local_path}/{device.name}.cfg"

        try:
            with open(path) as f:
                data = f.read()
        except:
            data = "Config not found in git repo"

        return render(
            request,
            "netbox_device_config/git/git_config_view.html",
            {
                "device": device,
                "config": data,
            },
        )



class BackupScheduleListView(View):

    def get(self, request):
        schedules = BackupSchedule.objects.all().order_by("name")

        return render(
            request,
            "netbox_device_config/schedule_list.html",
            {"schedules": schedules}
        )

class BackupScheduleCreateView(View):

    def get(self, request):
        from dcim.models import Device
        devices = Device.objects.filter(
            id__in=DeviceCredential.objects.values_list("device_id", flat=True)
        ).order_by("name")

        return render(
            request,
            "netbox_device_config/schedule_add.html",
            {"devices": devices}
        )

    def post(self, request):

        BackupSchedule.objects.create(
            name=request.POST.get("name"),
            device_id=request.POST.get("device") or None,
            schedule_type=request.POST.get("schedule_type"),
            time_of_day=request.POST.get("time_of_day") or None,
            enabled=True
        )

        return redirect("plugins:netbox_device_config:schedule_list")
