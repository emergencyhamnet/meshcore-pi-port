#!/usr/bin/env python3

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from live_runtime_helper_lock import exclusive_helper_lock


CMD_APP_START = 1
CMD_SYNC_NEXT_MESSAGE = 10
CMD_DEVICE_QUERY = 22

RESP_CODE_NO_MORE_MESSAGES = 10
RESP_CODE_DEVICE_INFO = 13
RESP_CODE_SELF_INFO = 5
RESP_CODE_CONTACT_MSG_RECV_V3 = 16
RESP_CODE_CHANNEL_MSG_RECV_V3 = 17
PUSH_CODE_ADVERT = 0x80
PUSH_CODE_MSG_WAITING = 0x83
PUSH_CODE_NEW_ADVERT = 0x8A
PUSH_CODE_TELEMETRY_RESPONSE = 0x8B

LPP_GENERIC_SENSOR = 100
LPP_TEMPERATURE = 103
LPP_RELATIVE_HUMIDITY = 104
LPP_BAROMETRIC_PRESSURE = 115
LPP_VOLTAGE = 116
LPP_CURRENT = 117
LPP_PERCENTAGE = 120
LPP_ALTITUDE = 121
LPP_CONCENTRATION = 125
LPP_POWER = 128
LPP_DIRECTION = 132
LPP_GPS = 136

PUSH_CODE_NAMES = {
    PUSH_CODE_ADVERT: "advert",
    PUSH_CODE_MSG_WAITING: "message_waiting",
    PUSH_CODE_NEW_ADVERT: "new_advert",
    PUSH_CODE_TELEMETRY_RESPONSE: "telemetry_response",
}

EXPECTED_FIRMWARE_VER_CODE = 13
TXT_TYPE_PLAIN = 0
DEFAULT_SYSTEMD_SERVICE = "meshcore-pi-live-runtime.service"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for live channel messages through the live Pi donor runtime via a temporary localhost TCP endpoint."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5040)
    parser.add_argument("--channel-index", type=int, default=-1, help="Channel to match; use -1 to accept all channels")
    parser.add_argument("--expect-text", help="Optional substring that must appear in the received text")
    parser.add_argument(
        "--storage-root",
        default=os.environ.get("MESHCORE_PI_STORAGE_ROOT", "/var/lib/meshcore-pi-port"),
    )
    parser.add_argument(
        "--runtime-bin",
        default=os.environ.get("MESHCORE_PI_LIVE_RUNTIME_BIN"),
    )
    parser.add_argument("--app-name", default="pi-public-recv")
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--reply-timeout", type=float, default=5.0)
    parser.add_argument("--post-ready-delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument(
        "--burst-drain-seconds",
        type=float,
        default=1.5,
        help="After the first matching message arrives, keep polling briefly to drain the rest of a burst.",
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


def decode_signed_value(raw: bytes, multiplier: int) -> float:
    return int.from_bytes(raw, "big", signed=True) / multiplier


def decode_unsigned_value(raw: bytes, multiplier: int) -> float:
    return int.from_bytes(raw, "big", signed=False) / multiplier


def decode_lpp_payload(payload: bytes) -> dict:
    pos = 0
    readings = []
    summary_parts = []

    while pos + 1 < len(payload):
        channel = payload[pos]
        field_type = payload[pos + 1]
        pos += 2
        if channel == 0:
            break

        entry = {"channel": channel, "type": field_type}
        label = None
        value_text = None

        if field_type == LPP_GPS and pos + 9 <= len(payload):
            lat = decode_signed_value(payload[pos:pos + 3], 10000)
            lon = decode_signed_value(payload[pos + 3:pos + 6], 10000)
            alt = decode_signed_value(payload[pos + 6:pos + 9], 100)
            pos += 9
            entry.update({"name": "gps", "lat": lat, "lon": lon, "alt_m": alt})
            label = f"ch{channel} gps"
            value_text = f"{lat:.4f}, {lon:.4f}, alt {alt:.1f} m"
        elif field_type == LPP_VOLTAGE and pos + 2 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 2], 100)
            pos += 2
            entry.update({"name": "voltage", "value": value, "unit": "V"})
            label = f"ch{channel} voltage"
            value_text = f"{value:.2f} V"
        elif field_type == LPP_CURRENT and pos + 2 <= len(payload):
            value = decode_signed_value(payload[pos:pos + 2], 1000)
            pos += 2
            entry.update({"name": "current", "value": value, "unit": "A"})
            label = f"ch{channel} current"
            value_text = f"{value:.3f} A"
        elif field_type == LPP_POWER and pos + 2 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 2], 1)
            pos += 2
            entry.update({"name": "power", "value": value, "unit": "W"})
            label = f"ch{channel} power"
            value_text = f"{value:.0f} W"
        elif field_type == LPP_TEMPERATURE and pos + 2 <= len(payload):
            value = decode_signed_value(payload[pos:pos + 2], 10)
            pos += 2
            entry.update({"name": "temperature", "value": value, "unit": "C"})
            label = f"ch{channel} temp"
            value_text = f"{value:.1f} C"
        elif field_type == LPP_RELATIVE_HUMIDITY and pos + 1 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 1], 2)
            pos += 1
            entry.update({"name": "humidity", "value": value, "unit": "%"})
            label = f"ch{channel} humidity"
            value_text = f"{value:.1f}%"
        elif field_type == LPP_BAROMETRIC_PRESSURE and pos + 2 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 2], 10)
            pos += 2
            entry.update({"name": "pressure", "value": value, "unit": "hPa"})
            label = f"ch{channel} pressure"
            value_text = f"{value:.1f} hPa"
        elif field_type == LPP_ALTITUDE and pos + 2 <= len(payload):
            value = decode_signed_value(payload[pos:pos + 2], 1)
            pos += 2
            entry.update({"name": "altitude", "value": value, "unit": "m"})
            label = f"ch{channel} altitude"
            value_text = f"{value:.0f} m"
        elif field_type == LPP_GENERIC_SENSOR and pos + 4 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 4], 1)
            pos += 4
            entry.update({"name": "generic_sensor", "value": value})
            label = f"ch{channel} sensor"
            value_text = f"{value:.0f}"
        elif field_type == LPP_PERCENTAGE and pos + 1 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 1], 1)
            pos += 1
            entry.update({"name": "percentage", "value": value, "unit": "%"})
            label = f"ch{channel} percentage"
            value_text = f"{value:.0f}%"
        elif field_type == LPP_CONCENTRATION and pos + 2 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 2], 1)
            pos += 2
            entry.update({"name": "concentration", "value": value, "unit": "ppm"})
            label = f"ch{channel} concentration"
            value_text = f"{value:.0f} ppm"
        elif field_type == LPP_DIRECTION and pos + 2 <= len(payload):
            value = decode_unsigned_value(payload[pos:pos + 2], 1)
            pos += 2
            entry.update({"name": "direction", "value": value, "unit": "deg"})
            label = f"ch{channel} direction"
            value_text = f"{value:.0f} deg"
        else:
            remaining = len(payload) - pos
            entry.update({"name": "unknown", "raw_hex": payload[pos:].hex(), "unsupported_type": field_type})
            pos = len(payload)
            readings.append(entry)
            summary_parts.append(f"ch{channel} type {field_type} ({remaining} raw bytes)")
            break

        readings.append(entry)
        if label and value_text:
            summary_parts.append(f"{label} {value_text}")

    return {"measurements": readings, "summary": "; ".join(summary_parts)}


def decode_push_event(payload: bytes) -> dict:
    code = payload[0]
    event_type = PUSH_CODE_NAMES.get(code, "push_frame")
    summary = {
        "advert": "Advert push observed",
        "new_advert": "New advert push observed",
        "message_waiting": "Runtime message-waiting push observed",
    }.get(event_type, f"Push frame 0x{code:02x} observed")
    event = {
        "event_type": event_type,
        "push_code": code,
        "push_code_hex": f"0x{code:02x}",
        "payload_len": len(payload),
        "payload_hex": payload.hex(),
        "summary": summary,
        "detail": f"Code {code:#04x}, {len(payload)} bytes",
        "timestamp": int(time.time()),
    }
    if code == PUSH_CODE_TELEMETRY_RESPONSE and len(payload) >= 8:
        pub_key_prefix = payload[2:8].hex()
        telemetry = decode_lpp_payload(payload[8:])
        event.update({
            "pub_key_prefix": pub_key_prefix,
            "telemetry": telemetry,
            "summary": f"Telemetry response observed from {pub_key_prefix}" + (f": {telemetry['summary']}" if telemetry.get('summary') else ""),
            "detail": f"Telemetry response from {pub_key_prefix}, {len(telemetry.get('measurements', []))} measurement(s)",
        })
    return event
def recv_frame_until_non_push(sock: socket.socket, stage: str) -> tuple[bytes, list[dict]]:
    push_events: list[dict] = []
    while True:
        payload = recv_frame(sock, stage)
        if not payload:
            continue
        if payload[0] < 0x80:
            return payload, push_events
        push_events.append(decode_push_event(payload))


def recv_non_push_frame(sock: socket.socket, stage: str) -> bytes:
    payload, _ = recv_frame_until_non_push(sock, stage)
    return payload


def send_frame(sock: socket.socket, payload: bytes) -> None:
    header = bytes((ord("<"), len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
    sock.sendall(header + payload)


def expect_device_query(sock: socket.socket) -> None:
    send_frame(sock, bytes((CMD_DEVICE_QUERY, EXPECTED_FIRMWARE_VER_CODE)))
    payload = recv_non_push_frame(sock, "DEVICE_QUERY reply")
    if len(payload) != 82 or payload[0] != RESP_CODE_DEVICE_INFO:
        raise RuntimeError(f"unexpected DEVICE_QUERY reply: len={len(payload)} code={payload[:1].hex()}")


def expect_app_start(sock: socket.socket, app_name: str) -> None:
    payload = bytes((CMD_APP_START, 0, 0, 0, 0, 0, 0, 0)) + app_name.encode("utf-8")
    send_frame(sock, payload)
    response = recv_non_push_frame(sock, "APP_START reply")
    if len(response) < 2 or response[0] != RESP_CODE_SELF_INFO:
        raise RuntimeError(f"unexpected APP_START reply: len={len(response)} code={response[:1].hex()}")


def decode_signed_byte(value: int) -> int:
    return value - 256 if value >= 128 else value


def poll_next_message(sock: socket.socket) -> tuple[dict | None, list[dict]]:
    send_frame(sock, bytes((CMD_SYNC_NEXT_MESSAGE,)))
    payload, push_events = recv_frame_until_non_push(sock, "SYNC_NEXT_MESSAGE reply")
    if len(payload) == 1 and payload[0] == RESP_CODE_NO_MORE_MESSAGES:
        return None, push_events
    if len(payload) < 11 or payload[0] not in (RESP_CODE_CONTACT_MSG_RECV_V3, RESP_CODE_CHANNEL_MSG_RECV_V3):
        raise RuntimeError(f"unexpected SYNC_NEXT_MESSAGE reply: len={len(payload)} code={payload[:1].hex()}")

    if payload[0] == RESP_CODE_CONTACT_MSG_RECV_V3:
        timestamp = int.from_bytes(payload[12:16], "little")
        text = payload[16:].decode("utf-8", "replace")
        return {
            "code": payload[0],
            "snr_x4": decode_signed_byte(payload[1]),
            "channel_index": -1,
            "path_len": payload[10],
            "txt_type": payload[11],
            "timestamp": timestamp,
            "text": text,
            "message_scope": "direct",
            "sender_prefix": payload[4:10].hex(),
        }, push_events

    timestamp = int.from_bytes(payload[7:11], "little")
    text = payload[11:].decode("utf-8", "replace")
    return {
        "code": payload[0],
        "snr_x4": decode_signed_byte(payload[1]),
        "channel_index": payload[4],
        "path_len": payload[5],
        "txt_type": payload[6],
        "timestamp": timestamp,
        "text": text,
        "message_scope": "channel",
    }, push_events


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

            deadline = time.monotonic() + args.timeout
            drain_deadline: float | None = None
            all_messages: list[dict] = []
            matching_messages: list[dict] = []
            push_events: list[dict] = []
            while time.monotonic() < deadline:
                message, observed_push_events = poll_next_message(client_socket)
                if observed_push_events:
                    push_events.extend(observed_push_events)
                    if drain_deadline is None:
                        drain_deadline = min(deadline, time.monotonic() + args.burst_drain_seconds)
                if message is None:
                    if all_messages or push_events:
                        if drain_deadline is not None and time.monotonic() >= drain_deadline:
                            break
                    time.sleep(min(args.poll_interval, max(0.0, deadline - time.monotonic())))
                    continue
                if message["txt_type"] != TXT_TYPE_PLAIN:
                    if drain_deadline is None:
                        drain_deadline = min(deadline, time.monotonic() + args.burst_drain_seconds)
                    continue
                all_messages.append(message)
                channel_matches = (
                    message.get("message_scope") == "direct"
                    or args.channel_index < 0
                    or message["channel_index"] == args.channel_index
                )
                text_matches = not args.expect_text or args.expect_text in message["text"]
                if channel_matches and text_matches:
                    matching_messages.append(message)
                if drain_deadline is None:
                    drain_deadline = min(deadline, time.monotonic() + args.burst_drain_seconds)

            if all_messages or push_events:
                print(json.dumps({"messages": all_messages, "matching_messages": matching_messages, "push_events": push_events}, sort_keys=True))
                return 0

            raise TimeoutError("timed out waiting for a matching public channel message")
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