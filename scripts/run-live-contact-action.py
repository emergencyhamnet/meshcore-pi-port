#!/usr/bin/env python3

import argparse
import json
import os
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

from live_runtime_helper_lock import exclusive_helper_lock


CMD_APP_START = 1
CMD_SEND_TXT_MSG = 2
CMD_DEVICE_QUERY = 22
CMD_REMOVE_CONTACT = 15
CMD_SEND_TELEMETRY_REQ = 39

RESP_CODE_OK = 0
RESP_CODE_SELF_INFO = 5
RESP_CODE_SENT = 6
RESP_CODE_DEVICE_INFO = 13

PUSH_CODE_TELEMETRY_RESPONSE = 0x8B
TXT_TYPE_PLAIN = 0
EXPECTED_FIRMWARE_VER_CODE = 13
PUB_KEY_SIZE = 32
PUB_KEY_PREFIX_SIZE = 6
DEFAULT_SYSTEMD_SERVICE = "meshcore-pi-live-runtime.service"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run donor-backed direct contact actions through a temporary localhost TCP endpoint."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5040)
    parser.add_argument(
        "--storage-root",
        default=os.environ.get("MESHCORE_PI_STORAGE_ROOT", "/var/lib/meshcore-pi-port"),
    )
    parser.add_argument(
        "--runtime-bin",
        default=os.environ.get("MESHCORE_PI_LIVE_RUNTIME_BIN"),
    )
    parser.add_argument(
        "--app-name",
        default="pi-contact-action",
    )
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
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--reply-timeout", type=float, default=5.0)
    parser.add_argument("--post-ready-delay", type=float, default=0.5)

    subparsers = parser.add_subparsers(dest="action", required=True)

    send_text = subparsers.add_parser("send-text", help="Send a direct text message to an existing contact")
    send_text.add_argument("recipient_pub_key", help="Full 32-byte contact public key as 64 hex characters")
    send_text.add_argument("message", help="UTF-8 direct message text")
    send_text.add_argument("--attempt", type=int, default=0)
    send_text.add_argument("--post-send-delay", type=float, default=0.5)

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


def service_unit_exists(service_name: str) -> bool:
    result = subprocess.run(
        ["systemctl", "show", service_name, "--property=LoadState", "--value"],
        cwd=repo_root(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    load_state = result.stdout.decode("utf-8", errors="replace").strip()
    return result.returncode == 0 and load_state not in {"", "not-found", "masked"}


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


def validate_pub_key_hex(value: str) -> str:
    clean = str(value or "").strip().lower()
    if len(clean) != PUB_KEY_SIZE * 2:
        raise ValueError("recipient_pub_key must be exactly 64 hex characters")
    if any(ch not in "0123456789abcdef" for ch in clean):
        raise ValueError("recipient_pub_key must contain only hex characters")
    return clean


def send_direct_text(sock: socket.socket, recipient_pub_key_hex: str, message: str, attempt: int) -> dict:
    text = message.encode("utf-8")
    timestamp = int(time.time())
    pub_key_prefix = bytes.fromhex(recipient_pub_key_hex[: PUB_KEY_PREFIX_SIZE * 2])
    payload = bytes((CMD_SEND_TXT_MSG, TXT_TYPE_PLAIN, attempt & 0xFF))
    payload += struct.pack("<I", timestamp)
    payload += pub_key_prefix
    payload += text
    send_frame(sock, payload)
    response = recv_frame(sock, "CMD_SEND_TXT_MSG reply")
    if len(response) != 10 or response[0] != RESP_CODE_SENT:
        raise RuntimeError(f"unexpected CMD_SEND_TXT_MSG reply: len={len(response)} code={response[:1].hex()}")
    return {
        "flood": response[1] == 1,
        "expected_ack": struct.unpack_from("<I", response, 2)[0],
        "est_timeout_ms": struct.unpack_from("<I", response, 6)[0],
        "recipient_prefix": recipient_pub_key_hex[: PUB_KEY_PREFIX_SIZE * 2],
        "recipient_pub_key": recipient_pub_key_hex,
        "text_bytes": len(text),
    }


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

    try:
        args.recipient_pub_key = validate_pub_key_hex(args.recipient_pub_key)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

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
            action_result = send_direct_text(client_socket, args.recipient_pub_key, args.message, args.attempt)
            time.sleep(args.post_send_delay)

            print(json.dumps({"ok": True, "action": args.action, "endpoint": endpoint, **action_result}))
            return 0
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}))
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
                print(json.dumps({"ok": False, "warning": f"failed to restore serial live runtime: {exc}"}), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
