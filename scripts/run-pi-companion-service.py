#!/usr/bin/env python3

import argparse
import os
import select
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose a stable TCP companion endpoint by bridging an external client socket to the Pi donor runtime transport."
    )
    parser.add_argument("--listen-host", default=os.environ.get("MESHCORE_PI_COMPANION_LISTEN_HOST", "127.0.0.1"))
    parser.add_argument(
        "--listen-port",
        type=int,
        default=int(os.environ.get("MESHCORE_PI_COMPANION_LISTEN_PORT", "5040")),
    )
    parser.add_argument("--runtime-host", default=os.environ.get("MESHCORE_PI_RUNTIME_HOST", "127.0.0.1"))
    parser.add_argument(
        "--runtime-port",
        type=int,
        default=int(os.environ.get("MESHCORE_PI_HELPER_RUNTIME_PORT", "5041")),
    )
    parser.add_argument(
        "--storage-root",
        default=os.environ.get("MESHCORE_PI_STORAGE_ROOT", "/var/lib/meshcore-pi-port"),
    )
    parser.add_argument(
        "--runtime-bin",
        default=os.environ.get("MESHCORE_PI_LIVE_RUNTIME_BIN"),
    )
    parser.add_argument("--runtime-connect-timeout", type=float, default=10.0)
    parser.add_argument("--runtime-ready-timeout", type=float, default=10.0)
    parser.add_argument("--post-ready-delay", type=float, default=0.5)
    parser.add_argument("--client-accept-timeout", type=float, default=1.0)
    parser.add_argument("--restart-delay", type=float, default=0.5)
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


def wait_for_runtime_ready(status_path: Path, expected_endpoint: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if status_path.exists():
            content = status_path.read_text(encoding="utf-8", errors="replace")
            if (
                "live_runtime_ready=1" in content
                and "transport_enabled=1" in content
                and f"runtime_endpoint={expected_endpoint}" in content
            ):
                return
        time.sleep(0.2)
    raise TimeoutError(f"timed out waiting for runtime ready in {status_path} for {expected_endpoint}")


def terminate_runtime(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    process.kill()
    process.wait(timeout=5)


def close_socket(sock: socket.socket | None) -> None:
    if sock is None:
        return
    try:
        sock.close()
    except OSError:
        pass


def relay_until_closed(runtime_sock: socket.socket, client_sock: socket.socket) -> None:
    sockets = [runtime_sock, client_sock]
    for sock in sockets:
        sock.setblocking(False)

    while True:
        readable, _, exceptional = select.select(sockets, [], sockets, 1.0)
        if exceptional:
            raise RuntimeError("socket relay encountered an exceptional condition")
        if not readable:
            continue

        for source in readable:
            try:
                payload = source.recv(4096)
            except BlockingIOError:
                continue
            if not payload:
                return
            target = client_sock if source is runtime_sock else runtime_sock
            target.sendall(payload)


def serve_clients(
    *,
    runtime_sock: socket.socket,
    client_listener: socket.socket,
    stop_requested: callable,
) -> bool:
    while not stop_requested():
        try:
            client_sock, client_addr = client_listener.accept()
        except socket.timeout:
            continue

        print(f"Accepted companion client from {client_addr[0]}:{client_addr[1]}")
        sys.stdout.flush()
        try:
            relay_until_closed(runtime_sock, client_sock)
            print("Companion client disconnected")
            sys.stdout.flush()
        except Exception as exc:
            print(f"WARNING: companion client session failed: {exc}", file=sys.stderr)
            return False
        finally:
            close_socket(client_sock)

    return True


def main() -> int:
    args = parse_args()
    outer_endpoint = f"tcp://{args.listen_host}:{args.listen_port}"
    runtime_endpoint = f"tcp://{args.runtime_host}:{args.runtime_port}"
    status_path = Path(args.storage_root) / "state" / "runtime-bridge.status"
    runtime_listener: socket.socket | None = None
    client_listener: socket.socket | None = None

    stop_requested = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    runtime_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    runtime_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    runtime_listener.bind((args.runtime_host, args.runtime_port))
    runtime_listener.listen(1)
    runtime_listener.settimeout(args.runtime_connect_timeout)

    client_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_listener.bind((args.listen_host, args.listen_port))
    client_listener.listen(1)
    client_listener.settimeout(args.client_accept_timeout)

    print(f"MeshCore companion bridge listening on {outer_endpoint}")
    print(f"Runtime transport endpoint: {runtime_endpoint}")
    print(f"Storage root: {args.storage_root}")
    sys.stdout.flush()

    try:
        while not stop_requested:
            runtime_process: subprocess.Popen[bytes] | None = None
            runtime_sock: socket.socket | None = None

            try:
                runtime_process = subprocess.Popen(
                    ["bash", "scripts/run-pi-live-runtime.sh"],
                    cwd=repo_root(),
                    env=runtime_env(args, runtime_endpoint),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid,
                )
                runtime_sock, _ = runtime_listener.accept()
                wait_for_runtime_ready(status_path, runtime_endpoint, args.runtime_ready_timeout)
                time.sleep(args.post_ready_delay)

                print("Live runtime connected; companion bridge entering persistent accept loop")
                sys.stdout.flush()
                session_ok = serve_clients(
                    runtime_sock=runtime_sock,
                    client_listener=client_listener,
                    stop_requested=lambda: stop_requested,
                )
                if not session_ok:
                    raise RuntimeError("runtime relay session failed")
            except TimeoutError as exc:
                print(f"WARNING: {exc}", file=sys.stderr)
            except Exception as exc:
                print(f"WARNING: companion bridge cycle failed: {exc}", file=sys.stderr)
            finally:
                close_socket(runtime_sock)
                terminate_runtime(runtime_process)

            if not stop_requested:
                time.sleep(args.restart_delay)
    finally:
        close_socket(client_listener)
        close_socket(runtime_listener)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())