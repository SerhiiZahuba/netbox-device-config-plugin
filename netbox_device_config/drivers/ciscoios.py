import paramiko
import time


def run_backup(cred, commands, append_log):

    append_log("Driver: Cisco IOS paramiko")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(
        hostname=cred.host,
        port=int(cred.port),
        username=cred.username,
        password=cred.password,
        timeout=30,
        banner_timeout=20,
        auth_timeout=30,
        look_for_keys=False,
        allow_agent=False
    )

    append_log("SSH connected")

    shell = client.invoke_shell()
    time.sleep(1)

    if shell.recv_ready():
        shell.recv(65535)

    output = ""

    for cmd in commands:
        append_log(f"Executing: {cmd}")
        shell.send(cmd + "\n")
        time.sleep(2)

    start = time.time()

    while True:
        if shell.recv_ready():
            chunk = shell.recv(65535).decode(errors="ignore")
            output += chunk

        if "#" in output[-50:] or ">" in output[-50:]:
            break

        if time.time() - start > 300:
            raise Exception("Cisco output timeout")

        time.sleep(1)

    client.close()

    append_log(f"Received {len(output)} bytes")

    return output
