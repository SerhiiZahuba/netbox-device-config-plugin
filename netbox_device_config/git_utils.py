import os
import subprocess
from .models import GitSettings


# -------------------------------------------------
# helper
# -------------------------------------------------

def run(cmd, cwd=None):
    return subprocess.check_output(cmd, shell=True, cwd=cwd).decode().strip()


# -------------------------------------------------
# repo
# -------------------------------------------------

def ensure_repo():

    settings = GitSettings.objects.first()
    path = settings.local_path

    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

    # clone якщо нема
    if not os.path.exists(os.path.join(path, ".git")):
        run(f"git clone {settings.repo_url} {path}")

    # branch
    run(f"git checkout {settings.branch}", cwd=path)

    # pull
    run("git pull", cwd=path)

    return path


# -------------------------------------------------
# SAVE CONFIG
# -------------------------------------------------

def save_config_to_git(device, config_text):

    repo = ensure_repo()
    filename = f"{device.name}.cfg"
    fullpath = os.path.join(repo, filename)

    # save file
    with open(fullpath, "w") as f:
        f.write(config_text)

    subprocess.run("git add .", shell=True, cwd=repo)

    # перевірка змін
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo
    )

    if diff.returncode == 0:
        # змін нема
        return None

    # commit
    run(
        f'git commit -m "backup {device.name} from netbox"',
        cwd=repo
    )

    run("git push", cwd=repo)

    # hash
    commit = run("git rev-parse HEAD", cwd=repo)

    return commit


# -------------------------------------------------
# GET LATEST CONFIG
# -------------------------------------------------

def get_latest_config(device):
    repo = ensure_repo()
    filename = f"{device.name}.cfg"

    try:
        output = run(f"git show HEAD:{filename}", cwd=repo)
        return output
    except Exception:
        return "No config found in repository"


# -------------------------------------------------
# GET CONFIG BY COMMIT
# -------------------------------------------------

def get_config_by_commit(device, commit):
    repo = ensure_repo()
    filename = f"{device.name}.cfg"

    try:
        return run(f"git show {commit}:{filename}", cwd=repo)
    except Exception:
        return "Config not found in this commit"


# -------------------------------------------------
# HISTORY
# -------------------------------------------------

def get_config_history(device):
    repo = ensure_repo()
    filename = f"{device.name}.cfg"

    output = run(
        f'git log --pretty=format:"%H|%ad|%s" --date=iso -- {filename}',
        cwd=repo
    )

    history = []

    for line in output.splitlines():
        commit, date, msg = line.split("|", 2)
        history.append({
            "commit": commit,
            "date": date,
            "msg": msg
        })

    return history


# -------------------------------------------------
# SIZE MAP
# -------------------------------------------------

def get_config_size_map(device):
    repo = ensure_repo()
    filename = f"{device.name}.cfg"

    size_map = {}

    commits = run(
        f"git log --pretty=format:%H -- {filename}",
        cwd=repo
    ).splitlines()

    for commit in commits:
        try:
            content = run(f"git show {commit}:{filename}", cwd=repo)
            size_map[commit] = len(content.encode())
        except Exception:
            size_map[commit] = 0

    return size_map
