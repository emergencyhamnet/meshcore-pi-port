from __future__ import annotations

import argparse
import json

from gateway_link_client import MeshCoreGatewayLinkClient
from windows_node_page import build_directed_private_message_request, build_node_page_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or send a Windows-side directed private message through the live gateway-link pipe.")
    parser.add_argument("--host", default="192.168.1.219", help="Gateway-link host. Default: 192.168.1.219")
    parser.add_argument("--port", type=int, default=7463, help="Gateway-link port. Default: 7463")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout in seconds")
    parser.add_argument("--text", required=True, help="Directed private message text")
    parser.add_argument("--public-key", default="", help="Optional explicit target public key")
    parser.add_argument("--send", action="store_true", help="Actually send the message instead of only previewing the request")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with MeshCoreGatewayLinkClient(args.host, args.port, timeout_seconds=args.timeout) as client:
        model = build_node_page_model(
            client.get_snapshot(),
            client.get_device_details(),
            client.list_channels(),
            client.list_observed_nodes(),
        )
        payload = build_directed_private_message_request(
            model,
            args.text,
            public_key=args.public_key or None,
        )
        if not args.send:
            print(json.dumps({"ok": True, "preview_only": True, "request": payload}, indent=2, sort_keys=True))
            return 0
        result = client.send_directed_private_message(public_key=payload["public_key"], text=payload["text"])
    print(json.dumps({"ok": True, "preview_only": False, "result": result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())