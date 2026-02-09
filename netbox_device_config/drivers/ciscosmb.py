import paramiko
import time


def run_backup(cred, commands, append_log):

    append_log("Driver: Cisco SMB exec mode")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(
        hostname=cred.host,
        port=int(cred.port),
        username=cred.username,
        password=cred.password,
        timeout=30,
        look_for_keys=False,
        allow_agent=False
    )

    transport = client.get_transport()

    output = ""

    for cmd in commands:

        append_log(f"Executing: {cmd}")

        channel = transport.open_session()
        channel.settimeout(120)
        channel.exec_command(cmd)

        chunk = b""
        start = time.time()

        while True:

            if channel.recv_ready():
                chunk += channel.recv(65535)

            if channel.exit_status_ready():
                break

            if time.time() - start > 180:
                raise Exception(f"Timeout on command: {cmd}")

            time.sleep(0.5)

        decoded = chunk.decode(errors="ignore")

        append_log(f"Received {len(decoded)} bytes")
        output += f"\n\n# COMMAND: {cmd}\n{decoded}"

    client.close()

    return output
