#!/usr/bin/env python3

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from live_runtime_helper_lock import exclusive_helper_lock


CMD_APP_START = 1
CMD_DEVICE_QUERY = 22
CMD_GET_CHANNEL = 31
CMD_SET_CHANNEL = 32

RESP_CODE_OK = 0
RESP_CODE_SELF_INFO = 5
RESP_CODE_DEVICE_INFO = 13
RESP_CODE_CHANNEL_INFO = 18

EXPECTED_FIRMWARE_VER_CODE = 13
CHANNEL_NAME_BYTES = 32
CHANNEL_SECRET_BYTES = 16
DEFAULT_SYSTEMD_SERVICE = "meshcore-pi-live-runtime.service"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Get or set one persisted MeshCore group channel through the live Pi donor runtime."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5040)
    parser.add_argument("--channel-index", type=int, required=True)
    parser.add_argument(
        "--storage-root",
        default=os.environ.get("MESHCORE_PI_STORAGE_ROOT", "/var/lib/meshcore-pi-port"),
    )
    parser.add_argument(
        "--runtime-bin",
        default=os.environ.get("MESHCORE_PI_LIVE_RUNTIME_BIN"),
    )
    parser.add_argument("--app-name", default="pi-channel-config")
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--reply-timeout", type=float, default=5.0)
    parser.add_argument("--post-ready-delay", type=float, default=0.5)
    parser.add_argument("--name", help="Channel name to write")
    parser.add_argument("--secret-hex", help="16-byte channel secret as 32 hex chars")
    parser.add_argument(
        "--no-restore-serial-runtime",
        action="store_true",
        help="Leave the temporary runtime stopped instead of restoring the default serial runtime.",
    )
    parser.add_argument(
        "--systemd-service",
        default=os.environ.get("MESHCORE_PI_LIVE_RUNTIME_SERVICE", DEFAULT_SYSTEMD_SERVICE),
        help="Systemd unit name for the managed serial live runtime.",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def runtime_env(args: argparse.Namespace, endpoint: str) -> dict[str, str]:
    env = os.environ.copy()
    env["MESHCORE_PI_RUNTIME_ENDPOINT"] = endpoint
    env["MESHCORE_PI_STORAGE_ROOT"] = args.storage_root
    if args.runtime_bin:
        env["MESHCORE_PI_LIVE_RUNTIME_BIN"] = args.runtime_bin
    return env


def runtime_command(args: argparse.Namespace, endpoint: str, service_was_active: bool) -> list[str]:
    command = ["bash", "scripts/run-pi-live-runtime.sh"]
    if service_was_active and os.geteuid() != 0:
        env_prefix = [
            f"MESHCORE_PI_RUNTIME_ENDPOINT={endpoint}",
            f"MESHCORE_PI_STORAGE_ROOT={args.storage_root}",
        ]
        if args.runtime_bin:
            env_prefix.append(f"MESHCORE_PI_LIVE_RUNTIME_BIN={args.runtime_bin}")
        return ["sudo", "-n", "env", *env_prefix, *command]
    return command


def run_systemctl(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    if os.geteuid() == 0:
        command = ["systemctl", *args]
    else:
        command = ["sudo", "-n", "systemctl", *args]
    return subprocess.run(command, cwd=repo_root(), check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def is_service_active(service_name: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", service_name],
        cwd=repo_root(),
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def stop_managed_service(service_name: str) -> None:
    result = run_systemctl(["stop", service_name])
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            "managed runtime service is active, but it could not be stopped automatically; "
            f"run this script with sudo or stop {service_name} manually. {stderr}"
        )


def start_managed_service(service_name: str) -> None:
    result = run_systemctl(["start", service_name])
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"failed to restart managed runtime service {service_name}: {stderr}")


def recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("socket closed while reading response")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def wait_for_runtime_ready(status_path: Path, expected_endpoint: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if status_path.exists():
            content = status_path.read_text(encoding="utf-8")
            if (
                "live_runtime_ready=1" in content
                and "transport_enabled=1" in content
                and f"runtime_endpoint={expected_endpoint}" in content
            ):
                return
        time.sleep(0.2)
    raise TimeoutError(f"timed out waiting for runtime ready in {status_path} for {expected_endpoint}")


def recv_frame(sock: socket.socket, stage: str) -> bytes:
    try:
        header = recv_exact(sock, 3)
    except (TimeoutError, socket.timeout) as exc:
        raise TimeoutError(f"timed out waiting for {stage} frame header") from exc
    if header[0] != ord(">"): 
        raise RuntimeError(f"unexpected frame header byte: {header[0]!r}")
    payload_len = header[1] | (header[2] << 8)
    try:
        return recv_exact(sock, payload_len)
    except (TimeoutError, socket.timeout) as exc:
        raise TimeoutError(f"timed out waiting for {stage} frame payload") from exc


def send_frame(sock: socket.socket, payload: bytes) -> None:
    header = bytes((ord("<"), len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
    sock.sendall(header + payload)


def expect_device_query(sock: socket.socket) -> None:
    send_frame(sock, bytes((CMD_DEVICE_QUERY, EXPECTED_FIRMWARE_VER_CODE)))
    payload = recv_frame(sock, "DEVICE_QUERY reply")
    if len(payload) != 82 or payload[0] != RESP_CODE_DEVICE_INFO:
        raise RuntimeError(f"unexpected DEVICE_QUERY reply: len={len(payload)} code={payload[:1].hex()}")


def expect_app_start(sock: socket.socket, app_name: str) -> None:
    payload = bytes((CMD_APP_START, 0, 0, 0, 0, 0, 0, 0)) + app_name.encode("utf-8")
    send_frame(sock, payload)
    response = recv_frame(sock, "APP_START reply")
    if len(response) < 2 or response[0] != RESP_CODE_SELF_INFO:
        raise RuntimeError(f"unexpected APP_START reply: len={len(response)} code={response[:1].hex()}")


def get_channel(sock: socket.socket, channel_index: int) -> dict:
    send_frame(sock, bytes((CMD_GET_CHANNEL, channel_index)))
    response = recv_frame(sock, "GET_CHANNEL reply")
    if len(response) == 2 and response[0] != RESP_CODE_CHANNEL_INFO:
        raise RuntimeError(f"get channel failed with error code {response[1]}")
    if len(response) < 2 + CHANNEL_NAME_BYTES + CHANNEL_SECRET_BYTES or response[0] != RESP_CODE_CHANNEL_INFO:
        raise RuntimeError(f"unexpected GET_CHANNEL reply: len={len(response)} code={response[:1].hex()}")
    if response[1] != channel_index:
        raise RuntimeError(f"GET_CHANNEL returned wrong index: expected {channel_index}, got {response[1]}")
    name = response[2:34].split(b"\0", 1)[0].decode("utf-8", "replace")
    secret_hex = response[34:50].hex()
    return {"index": channel_index, "name": name, "secret_hex": secret_hex}


def set_channel(sock: socket.socket, channel_index: int, name: str, secret_hex: str) -> None:
    if len(secret_hex) != CHANNEL_SECRET_BYTES * 2:
        raise ValueError("secret hex must be exactly 32 hex characters")
    secret = bytes.fromhex(secret_hex)
    name_bytes = name.encode("utf-8")[: CHANNEL_NAME_BYTES - 1]
    padded_name = name_bytes + (b"\0" * (CHANNEL_NAME_BYTES - len(name_bytes)))
    payload = bytes((CMD_SET_CHANNEL, channel_index)) + padded_name + secret
    send_frame(sock, payload)
    response = recv_frame(sock, "SET_CHANNEL reply")
    if len(response) != 1 or response[0] != RESP_CODE_OK:
        raise RuntimeError(f"unexpected SET_CHANNEL reply: len={len(response)} code={response[:1].hex()}")


def terminate_runtime(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    process.kill()
    process.wait(timeout=5)


def restore_serial_runtime(args: argparse.Namespace) -> None:
    if args.no_restore_serial_runtime:
        return
    if service_unit_exists(args.systemd_service):
        start_managed_service(args.systemd_service)
        return
    restore_log_path = f"/tmp/pi-live-runtime-restore-{os.geteuid()}.log"
    restore_command = (
        "nohup env "
        f"MESHCORE_PI_STORAGE_ROOT={args.storage_root} "
        "bash scripts/run-pi-live-runtime.sh "
        f">{restore_log_path} 2>&1 </dev/null &"
    )
    subprocess.run(["bash", "-lc", restore_command], cwd=repo_root(), check=True)
    time.sleep(2)


def main() -> int:
    args = parse_args()
    endpoint = f"tcp://{args.host}:{args.port}"
    runtime_process: subprocess.Popen[bytes] | None = None
    server_socket: socket.socket | None = None
    client_socket: socket.socket | None = None
    service_was_active = False
    status_path = Path(args.storage_root) / "state" / "runtime-bridge.status"

    with exclusive_helper_lock():
        try:
            service_was_active = is_service_active(args.systemd_service)
            if service_was_active:
                stop_managed_service(args.systemd_service)

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((args.host, args.port))
            server_socket.listen(1)
            server_socket.settimeout(args.connect_timeout)

            runtime_process = subprocess.Popen(
                runtime_command(args, endpoint, service_was_active),
                cwd=repo_root(),
                env=runtime_env(args, endpoint),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )

            try:
                client_socket, _ = server_socket.accept()
            except TimeoutError as exc:
                raise TimeoutError(f"timed out waiting for TCP companion connection on {endpoint}") from exc
            client_socket.settimeout(args.reply_timeout)

            wait_for_runtime_ready(status_path, endpoint, args.connect_timeout)
            time.sleep(args.post_ready_delay)

            expect_device_query(client_socket)
            expect_app_start(client_socket, args.app_name)

            if args.name is None and args.secret_hex is None:
                print(get_channel(client_socket, args.channel_index))
            else:
                if args.name is None or args.secret_hex is None:
                    raise ValueError("both --name and --secret-hex are required when writing a channel")
                set_channel(client_socket, args.channel_index, args.name, args.secret_hex)
                print(get_channel(client_socket, args.channel_index))
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        finally:
            if client_socket is not None:
                client_socket.close()
            if server_socket is not None:
                server_socket.close()
            if runtime_process is not None:
                terminate_runtime(runtime_process)
            try:
                if service_was_active:
                    start_managed_service(args.systemd_service)
                else:
                    restore_serial_runtime(args)
            except Exception as exc:
                print(f"WARNING: failed to restore serial live runtime: {exc}", file=sys.stderr)

if __name__ == "__main__":
    raise SystemExit(main())