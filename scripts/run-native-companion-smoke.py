from __future__ import annotations

import argparse
import json

from native_companion_client import CompanionDeviceError, CompanionProtocolError, MeshCoreNativeTcpClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a native MeshCore companion smoke session against a TCP endpoint.")
    parser.add_argument("--host", default="127.0.0.1", help="Companion TCP host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=5040, help="Companion TCP port. Default: 5040")
    parser.add_argument("--app-name", default="windows-native-ui", help="App name sent in APP_START")
    parser.add_argument("--protocol-version", type=int, default=3, help="Protocol version byte for DEVICE_QUERY")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout in seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with MeshCoreNativeTcpClient(args.host, args.port, timeout_seconds=args.timeout) as client:
            snapshot = client.collect_session_snapshot(app_name=args.app_name, protocol_version=args.protocol_version)
    except (CompanionDeviceError, CompanionProtocolError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    print(json.dumps({"ok": True, **snapshot}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())