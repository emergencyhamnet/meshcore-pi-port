#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

host="${MESHCORE_PI_GATEWAY_LINK_HOST:-0.0.0.0}"
port="${MESHCORE_PI_GATEWAY_LINK_PORT:-7463}"
storage_root="${MESHCORE_PI_STORAGE_ROOT:-/var/lib/meshcore-pi-port}"
service_name="${MESHCORE_PI_LIVE_RUNTIME_SERVICE:-meshcore-pi-live-runtime.service}"
interface_mode="${MESHCORE_PI_INTERFACE_MODE:-app}"
allow_tx="${MESHCORE_PI_GATEWAY_LINK_ALLOW_TX:-1}"
native_host="${MESHCORE_PI_GATEWAY_LINK_NATIVE_HOST:-127.0.0.1}"
native_port="${MESHCORE_PI_GATEWAY_LINK_NATIVE_PORT:-5040}"
app_name="${MESHCORE_PI_GATEWAY_LINK_APP_NAME:-meshcore-gateway-link}"
protocol_version="${MESHCORE_PI_GATEWAY_LINK_PROTOCOL_VERSION:-3}"
timeout_seconds="${MESHCORE_PI_GATEWAY_LINK_TIMEOUT_SECONDS:-5.0}"

cd "$repo_root"
export PYTHONPATH="$repo_root/ui-native/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m meshcore_ui_native.gateway_link_server \
  --host "$host" \
  --port "$port" \
  --native-host "$native_host" \
  --native-port "$native_port" \
  --app-name "$app_name" \
  --protocol-version "$protocol_version" \
  --timeout "$timeout_seconds" \
  --service-name "$service_name" \
  --allow-basestation-tx "$allow_tx"