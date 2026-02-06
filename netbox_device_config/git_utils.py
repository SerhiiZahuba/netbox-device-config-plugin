import os
import subprocess
from .models import GitSettings


def run(cmd, cwd=None):
    return subprocess.check_output(cmd, shell=True, cwd=cwd).decode().strip()


def ensure_repo():

    settings = GitSettings.objects.first()
    path = settings.local_path

    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

    # якщо нема .git → clone
    if not os.path.exists(os.path.join(path, ".git")):
        run(f"git clone {settings.repo_url} {path}")

    # checkout branch
    run(f"git checkout {settings.branch}", cwd=path)

    # pull
    run("git pull", cwd=path)

    return path

def save_config_to_git(device, config_text):

    settings = GitSettings.objects.first()
    repo = ensure_repo()

    filename = f"{device.name}.cfg"
    fullpath = os.path.join(repo, filename)


    with open(fullpath, "w") as f:
        f.write(config_text)

    run("git add .", cwd=repo)

    run(
        f'git commit -m "backup {device.name} from netbox"',
        cwd=repo
    )

    run("git push", cwd=repo)

    commit = run("git rev-parse HEAD", cwd=repo)

    return commit
