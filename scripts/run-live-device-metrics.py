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


CMD_DEVICE_QUERY = 22
CMD_GET_BATT_AND_STORAGE = 20
CMD_GET_STATS = 56

RESP_CODE_DEVICE_INFO = 13
RESP_CODE_BATT_AND_STORAGE = 12
RESP_CODE_STATS = 24

STATS_TYPE_CORE = 0
STATS_TYPE_RADIO = 1
STATS_TYPE_PACKETS = 2

EXPECTED_FIRMWARE_VER_CODE = 13
DEFAULT_SYSTEMD_SERVICE = "meshcore-pi-live-runtime.service"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read live MeshCore device-query, battery/storage, and stats replies through a temporary localhost TCP endpoint."
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
    parser.add_argument("--no-restore-serial-runtime", action="store_true")
    parser.add_argument(
        "--systemd-service",
        default=os.environ.get("MESHCORE_PI_LIVE_RUNTIME_SERVICE", DEFAULT_SYSTEMD_SERVICE),
    )
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--reply-timeout", type=float, default=5.0)
    parser.add_argument("--post-ready-delay", type=float, default=0.5)
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


def connect_to_existing_runtime(host: str, port: int, timeout: float) -> socket.socket:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            sock = socket.create_connection((host, port), timeout=1.0)
            return sock
        except OSError as exc:
            last_error = exc
            time.sleep(0.2)
    raise TimeoutError(f"timed out connecting to existing companion bridge on tcp://{host}:{port}") from last_error


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


def wait_for_managed_runtime_ready(status_path: Path, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if status_path.exists():
            content = status_path.read_text(encoding="utf-8")
            if "live_runtime_ready=1" in content and "transport_enabled=1" in content:
                return
        time.sleep(0.2)
    raise TimeoutError(f"timed out waiting for managed runtime ready in {status_path}")


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


def parse_device_query(payload: bytes) -> dict[str, object]:
    if len(payload) < 82 or payload[0] != RESP_CODE_DEVICE_INFO:
        raise RuntimeError(f"unexpected DEVICE_QUERY reply: len={len(payload)} code={payload[:1].hex()}")
    return {
        "firmware_version_code": payload[1],
        "max_contacts_raw": payload[2],
        "max_contacts": payload[2] * 2,
        "max_channels": payload[3],
        "ble_pin": struct.unpack_from("<I", payload, 4)[0],
        "firmware_build": payload[8:20].decode("utf-8", "replace").rstrip("\x00").strip(),
        "model": payload[20:60].decode("utf-8", "replace").rstrip("\x00").strip(),
        "version": payload[60:80].decode("utf-8", "replace").rstrip("\x00").strip(),
        "client_repeat": payload[80],
        "path_hash_mode": payload[81],
    }


def parse_battery_storage(payload: bytes) -> dict[str, object]:
    if len(payload) < 11 or payload[0] != RESP_CODE_BATT_AND_STORAGE:
        raise RuntimeError(f"unexpected battery/storage reply: len={len(payload)} code={payload[:1].hex()}")
    battery_mv, used_kb, total_kb = struct.unpack("<HII", payload[1:11])
    return {"battery_mv": battery_mv, "used_kb": used_kb, "total_kb": total_kb}


def parse_stats(payload: bytes, stats_type: int) -> dict[str, object]:
    if len(payload) < 2 or payload[0] != RESP_CODE_STATS or payload[1] != stats_type:
        raise RuntimeError(f"unexpected stats reply type={stats_type}: len={len(payload)} code={payload[:2].hex()}")
    if stats_type == STATS_TYPE_CORE:
        _, _, battery_mv, uptime_secs, errors, queue_len = struct.unpack("<BBHIHB", payload)
        return {"battery_mv": battery_mv, "uptime_secs": uptime_secs, "errors": errors, "queue_len": queue_len}
    if stats_type == STATS_TYPE_RADIO:
        _, _, noise_floor, last_rssi, last_snr, tx_air_secs, rx_air_secs = struct.unpack("<BBhbbII", payload)
        return {
            "noise_floor": noise_floor,
            "last_rssi": last_rssi,
            "last_snr": last_snr / 4.0,
            "tx_air_secs": tx_air_secs,
            "rx_air_secs": rx_air_secs,
        }
    if stats_type == STATS_TYPE_PACKETS:
        if len(payload) < 26:
            raise RuntimeError(f"unexpected packets stats reply len={len(payload)}")
        _, _, recv, sent, flood_tx, direct_tx, flood_rx, direct_rx = struct.unpack("<BBIIIIII", payload[:26])
        result = {
            "recv": recv,
            "sent": sent,
            "flood_tx": flood_tx,
            "direct_tx": direct_tx,
            "flood_rx": flood_rx,
            "direct_rx": direct_rx,
        }
        if len(payload) >= 30:
            (recv_errors,) = struct.unpack("<I", payload[26:30])
            result["recv_errors"] = recv_errors
        return result
    raise RuntimeError(f"unsupported stats type {stats_type}")


def query_stats(sock: socket.socket, stats_type: int) -> dict[str, object]:
    send_frame(sock, bytes((CMD_GET_STATS, stats_type)))
    return parse_stats(recv_frame(sock, f"GET_STATS {stats_type} reply"), stats_type)


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
                wait_for_managed_runtime_ready(status_path, args.connect_timeout)
                client_socket = connect_to_existing_runtime(args.host, args.port, args.connect_timeout)
            else:
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
                wait_for_runtime_ready(status_path, endpoint, args.connect_timeout)

            client_socket.settimeout(args.reply_timeout)
            time.sleep(args.post_ready_delay)

            send_frame(client_socket, bytes((CMD_DEVICE_QUERY, EXPECTED_FIRMWARE_VER_CODE)))
            device_query = parse_device_query(recv_frame(client_socket, "DEVICE_QUERY reply"))

            send_frame(client_socket, bytes((CMD_GET_BATT_AND_STORAGE,)))
            battery = parse_battery_storage(recv_frame(client_socket, "GET_BATT_AND_STORAGE reply"))

            stats = {
                "core": query_stats(client_socket, STATS_TYPE_CORE),
                "radio": query_stats(client_socket, STATS_TYPE_RADIO),
                "packets": query_stats(client_socket, STATS_TYPE_PACKETS),
            }

            print(json.dumps({"ok": True, "endpoint": endpoint, "device_query": device_query, "battery": battery, "stats": stats}))
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
                if not service_was_active:
                    restore_serial_runtime(args)
            except Exception as exc:
                print(json.dumps({"ok": False, "warning": f"failed to restore serial live runtime: {exc}"}), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())