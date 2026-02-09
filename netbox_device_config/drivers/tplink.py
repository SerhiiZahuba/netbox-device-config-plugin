from netmiko import ConnectHandler
import time


def run_backup(cred, append_log):

    append_log("Driver: TP-Link JetStream")

    device = {
        "device_type": "tplink_jetstream",
        "host": cred.host,
        "username": cred.username,
        "password": cred.password,
        "port": int(cred.port),
        "fast_cli": False,
    }

    net_connect = ConnectHandler(**device)
    append_log("SSH connected")

    net_connect.enable()
    append_log("Entered enable mode")

    net_connect.send_command_timing("terminal length 0")

    append_log("Executing: show running-config")

    output = net_connect.send_command_timing(
        "show running-config",
        delay_factor=8
    )

    time.sleep(5)
    output += net_connect.read_channel()

    net_connect.disconnect()

    append_log(f"Received {len(output)} bytes")

    return output
