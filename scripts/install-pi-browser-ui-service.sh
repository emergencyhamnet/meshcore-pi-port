#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="meshcore-pi-browser-ui.service"
template_path="$repo_root/deploy/systemd/$service_name"
service_path="/etc/systemd/system/$service_name"
repo_target="${MESHCORE_PI_SERVICE_REPO_TARGET:-$repo_root}"
ui_host="${MESHCORE_PI_BROWSER_UI_HOST:-0.0.0.0}"
ui_port="${MESHCORE_PI_BROWSER_UI_PORT:-8099}"
companion_host="${MESHCORE_PI_BROWSER_UI_COMPANION_HOST:-127.0.0.1}"
companion_port="${MESHCORE_PI_BROWSER_UI_COMPANION_PORT:-5040}"
runtime_service="${MESHCORE_PI_LIVE_RUNTIME_SERVICE:-meshcore-pi-live-runtime.service}"
gateway_enabled="${MESHCORE_PI_BROWSER_UI_ENABLE_GATEWAY_LINK:-1}"
gateway_host="${MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_HOST:-0.0.0.0}"
gateway_port="${MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_PORT:-7463}"
gateway_allow_tx="${MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_ALLOW_TX:-0}"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

require_root() {
	if [[ "$(id -u)" -ne 0 ]]; then
		fail "run this installer as root, for example: sudo bash scripts/install-pi-browser-ui-service.sh"
	fi
}

require_file() {
	local file_path="$1"
	[[ -f "$file_path" ]] || fail "required file not found: $file_path"
}

require_root
require_file "$template_path"
require_file "$repo_target/scripts/run-pi-browser-ui.sh"
require_file "$repo_target/ui-native/src/meshcore_ui_native/web_app.py"

sed \
	-e "s|/opt/meshcore-pi-port|$repo_target|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_HOST=0.0.0.0|Environment=MESHCORE_PI_BROWSER_UI_HOST=$ui_host|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_PORT=8099|Environment=MESHCORE_PI_BROWSER_UI_PORT=$ui_port|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_COMPANION_HOST=127.0.0.1|Environment=MESHCORE_PI_BROWSER_UI_COMPANION_HOST=$companion_host|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_COMPANION_PORT=5040|Environment=MESHCORE_PI_BROWSER_UI_COMPANION_PORT=$companion_port|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_ENABLE_GATEWAY_LINK=1|Environment=MESHCORE_PI_BROWSER_UI_ENABLE_GATEWAY_LINK=$gateway_enabled|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_HOST=0.0.0.0|Environment=MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_HOST=$gateway_host|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_PORT=7463|Environment=MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_PORT=$gateway_port|g" \
	-e "s|Environment=MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_ALLOW_TX=0|Environment=MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_ALLOW_TX=$gateway_allow_tx|g" \
	-e "s|Environment=MESHCORE_PI_LIVE_RUNTIME_SERVICE=meshcore-pi-live-runtime.service|Environment=MESHCORE_PI_LIVE_RUNTIME_SERVICE=$runtime_service|g" \
	-e "s|meshcore-pi-live-runtime.service|$runtime_service|g" \
	"$template_path" > "$service_path"

systemctl daemon-reload
systemctl enable "$service_name"

cat <<EOF
Installed $service_name

Repo target      : $repo_target
UI host          : $ui_host
UI port          : $ui_port
Companion host   : $companion_host
Companion port   : $companion_port
Gateway enabled  : $gateway_enabled
Gateway host     : $gateway_host
Gateway port     : $gateway_port
Gateway allow TX : $gateway_allow_tx
Runtime service  : $runtime_service
Service path     : $service_path

Next steps:
1. systemctl start $service_name
2. systemctl status $service_name --no-pager
3. journalctl -u $service_name -n 50 --no-pager
EOF