from __future__ import annotations

import argparse
from pathlib import Path

from gateway_link_client import MeshCoreGatewayLinkClient
from windows_node_page import build_node_page_model, render_node_page_html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Windows-side node page preview from the live gateway-link pipe.")
    parser.add_argument("--host", default="192.168.1.219", help="Gateway-link host. Default: 192.168.1.219")
    parser.add_argument("--port", type=int, default=7463, help="Gateway-link port. Default: 7463")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout in seconds")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("var/windows-node-page-preview.html"),
        help="Output HTML path. Default: var/windows-node-page-preview.html",
    )
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
    html = render_node_page_html(model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())