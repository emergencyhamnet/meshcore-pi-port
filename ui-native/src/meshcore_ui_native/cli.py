from __future__ import annotations

import argparse
import json

from .companion_client import CompanionDeviceError, CompanionProtocolError, MeshCoreNativeTcpClient
from .node_page_model import build_node_page_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the native MeshCore UI model, browser shell, or desktop harness.")
    parser.add_argument("--host", default="127.0.0.1", help="Native companion host")
    parser.add_argument("--port", type=int, default=5040, help="Native companion port")
    parser.add_argument("--app-name", default="windows-native-ui", help="App name for APP_START")
    parser.add_argument("--protocol-version", type=int, default=3, help="Protocol version for DEVICE_QUERY")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout in seconds")
    parser.add_argument("--ui", action="store_true", help="Launch the desktop UI instead of printing JSON")
    parser.add_argument("--web", action="store_true", help="Launch the browser UI server instead of printing JSON")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Host interface for the browser UI server")
    parser.add_argument("--listen-port", type=int, default=8099, help="Port for the browser UI server")
    parser.add_argument("--gateway-link-host", default="", help="Optional host interface for an embedded gateway-link sidecar")
    parser.add_argument("--gateway-link-port", type=int, default=0, help="Optional port for an embedded gateway-link sidecar")
    parser.add_argument("--gateway-link-allow-basestation-tx", action="store_true", help="Allow basestation transmit through the embedded gateway-link sidecar")
    parser.add_argument("--gateway-link-service-name", default="meshcore-pi-live-runtime.service", help="Runtime service name reported by the embedded gateway-link sidecar")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.ui and args.web:
        print(json.dumps({"ok": False, "error": "choose either --ui or --web, not both"}))
        return 2
    if args.ui:
        from .desktop_app import launch_desktop_app

        return launch_desktop_app(
            host=args.host,
            port=args.port,
            app_name=args.app_name,
            protocol_version=args.protocol_version,
            timeout_seconds=args.timeout,
        )
    if args.web:
        from .web_app import launch_web_app

        return launch_web_app(
            host=args.host,
            port=args.port,
            app_name=args.app_name,
            protocol_version=args.protocol_version,
            timeout_seconds=args.timeout,
            bind_host=args.listen_host,
            bind_port=args.listen_port,
            gateway_link_host=str(args.gateway_link_host).strip() or None,
            gateway_link_port=int(args.gateway_link_port or 0) or None,
            gateway_link_allow_basestation_tx=bool(args.gateway_link_allow_basestation_tx),
            gateway_link_service_name=str(args.gateway_link_service_name).strip() or "meshcore-pi-live-runtime.service",
        )
    try:
        with MeshCoreNativeTcpClient(args.host, args.port, timeout_seconds=args.timeout) as client:
            snapshot = client.collect_session_snapshot(app_name=args.app_name, protocol_version=args.protocol_version)
    except (CompanionDeviceError, CompanionProtocolError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    model = build_node_page_model(snapshot)
    print(json.dumps({"ok": True, "node_page": model.to_dict()}, indent=2, sort_keys=True))
    return 0