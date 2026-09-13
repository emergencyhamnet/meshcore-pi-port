from __future__ import annotations

import argparse
import json

from gateway_link_client import GatewayLinkProtocolError, GatewayLinkRequestError, MeshCoreGatewayLinkClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a MeshCore gateway-link smoke session against the Windows-facing pipe.")
    parser.add_argument("--host", default="192.168.1.219", help="Gateway-link host. Default: 192.168.1.219")
    parser.add_argument("--port", type=int, default=7463, help="Gateway-link port. Default: 7463")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout in seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with MeshCoreGatewayLinkClient(args.host, args.port, timeout_seconds=args.timeout) as client:
            result = {
                "snapshot": client.get_snapshot(),
                "channels": client.list_channels(),
                "observed_nodes": client.list_observed_nodes(),
                "device": client.get_device_details(),
            }
    except (GatewayLinkProtocolError, GatewayLinkRequestError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    print(json.dumps({"ok": True, **result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())