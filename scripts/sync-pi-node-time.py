#!/usr/bin/env python3

import argparse
import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_gpsd_time(value: str) -> int:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return int(datetime.fromisoformat(normalized).timestamp())


def read_gpsd_epoch(host: str, port: int, timeout: float, max_reports: int) -> int:
    with socket.create_connection((host, port), timeout=timeout) as conn:
        conn.settimeout(timeout)
        conn.sendall(b'?WATCH={"enable":true,"json":true};\n')
        buffer = b""
        reports = 0
        while reports < max_reports:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                reports += 1
                try:
                    payload = json.loads(line.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    continue
                if payload.get("class") != "TPV":
                    continue
                if "time" not in payload:
                    continue
                mode = int(payload.get("mode", 0) or 0)
                if mode < 2:
                    continue
                return parse_gpsd_time(str(payload["time"]))
    raise RuntimeError("no valid GPSD TPV time fix available")


def resolve_epoch(args: argparse.Namespace) -> tuple[int, str]:
    if args.source == "host":
        return int(time.time()), "host"
    if args.source == "gpsd":
        return read_gpsd_epoch(args.gpsd_host, args.gpsd_port, args.gpsd_timeout, args.gpsd_reports), "gpsd"
    raise RuntimeError(f"unsupported time source: {args.source}")


def set_host_clock(epoch_seconds: int) -> None:
    if os.geteuid() != 0:
        raise RuntimeError("setting the Pi clock requires root")
    subprocess.run(["date", "-u", "-s", f"@{epoch_seconds}"], check=True, capture_output=True, text=True)


def sync_node_clock(storage_root: str, epoch_seconds: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MESHCORE_PI_STORAGE_ROOT"] = storage_root
    return subprocess.run(
        ["python3", "scripts/run-live-set-device-time.py", "--epoch-seconds", str(epoch_seconds)],
        cwd=repo_root(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync the Pi host clock and the MeshCore node RTC from a selected time source."
    )
    parser.add_argument(
        "--source",
        choices=("host", "gpsd"),
        default=os.environ.get("MESHCORE_PI_TIME_SOURCE", "host"),
        help="Time source for synchronization. host uses current Pi UTC. gpsd uses a GPSD TPV time fix.",
    )
    parser.add_argument(
        "--storage-root",
        default=os.environ.get("MESHCORE_PI_STORAGE_ROOT", "/var/lib/meshcore-pi-port"),
    )
    parser.add_argument(
        "--set-host-clock",
        action="store_true",
        default=os.environ.get("MESHCORE_PI_SET_HOST_CLOCK", "0") == "1",
        help="Also set the Pi host clock to the resolved epoch before syncing the node RTC.",
    )
    parser.add_argument("--gpsd-host", default=os.environ.get("MESHCORE_PI_GPSD_HOST", "127.0.0.1"))
    parser.add_argument("--gpsd-port", type=int, default=int(os.environ.get("MESHCORE_PI_GPSD_PORT", "2947")))
    parser.add_argument("--gpsd-timeout", type=float, default=float(os.environ.get("MESHCORE_PI_GPSD_TIMEOUT", "8.0")))
    parser.add_argument("--gpsd-reports", type=int, default=int(os.environ.get("MESHCORE_PI_GPSD_REPORTS", "20")))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        epoch_seconds, source_used = resolve_epoch(args)
        if args.set_host_clock:
            set_host_clock(epoch_seconds)
        node_result = sync_node_clock(args.storage_root, epoch_seconds)
        payload = {
            "ok": node_result.returncode == 0,
            "source": source_used,
            "epoch_seconds": epoch_seconds,
            "utc": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(epoch_seconds)),
            "set_host_clock": args.set_host_clock,
            "node_stdout": node_result.stdout.strip(),
            "node_stderr": node_result.stderr.strip(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if node_result.returncode == 0 else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())