#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="meshcore-pi-gateway-link.service"
template_path="$repo_root/deploy/systemd/$service_name"
service_path="/etc/systemd/system/$service_name"
repo_target="${MESHCORE_PI_SERVICE_REPO_TARGET:-$repo_root}"
gateway_host="${MESHCORE_PI_GATEWAY_LINK_HOST:-0.0.0.0}"
gateway_port="${MESHCORE_PI_GATEWAY_LINK_PORT:-7463}"
runtime_service="${MESHCORE_PI_LIVE_RUNTIME_SERVICE:-meshcore-pi-live-runtime.service}"
interface_mode="${MESHCORE_PI_INTERFACE_MODE:-app}"
allow_tx="${MESHCORE_PI_GATEWAY_LINK_ALLOW_TX:-1}"

default_storage_root() {
	local invoking_user="${SUDO_USER:-${USER:-}}"
	if [[ -n "$invoking_user" ]]; then
		local user_state_root="/home/$invoking_user/meshcore-pi-port-state"
		if [[ -d "$user_state_root" ]]; then
			printf '%s\n' "$user_state_root"
			return
		fi
	fi

	printf '%s\n' "/var/lib/meshcore-pi-port"
}

storage_root="${MESHCORE_PI_STORAGE_ROOT:-$(default_storage_root)}"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

require_root() {
	if [[ "$(id -u)" -ne 0 ]]; then
		fail "run this installer as root, for example: sudo bash scripts/install-pi-gateway-link-service.sh"
	fi
}

require_file() {
	local file_path="$1"
	[[ -f "$file_path" ]] || fail "required file not found: $file_path"
}

require_root
require_file "$template_path"
require_file "$repo_target/scripts/run-pi-gateway-link.sh"
require_file "$repo_target/ui-native/src/meshcore_ui_native/gateway_link_server.py"

mkdir -p "$storage_root/state"

sed \
	-e "s|/opt/meshcore-pi-port|$repo_target|g" \
	-e "s|Environment=MESHCORE_PI_INTERFACE_MODE=app|Environment=MESHCORE_PI_INTERFACE_MODE=$interface_mode|g" \
	-e "s|Environment=MESHCORE_PI_GATEWAY_LINK_HOST=0.0.0.0|Environment=MESHCORE_PI_GATEWAY_LINK_HOST=$gateway_host|g" \
	-e "s|Environment=MESHCORE_PI_GATEWAY_LINK_PORT=7463|Environment=MESHCORE_PI_GATEWAY_LINK_PORT=$gateway_port|g" \
	-e "s|Environment=MESHCORE_PI_GATEWAY_LINK_ALLOW_TX=1|Environment=MESHCORE_PI_GATEWAY_LINK_ALLOW_TX=$allow_tx|g" \
	-e "s|/var/lib/meshcore-pi-port|$storage_root|g" \
	-e "s|meshcore-pi-live-runtime.service|$runtime_service|g" \
	"$template_path" > "$service_path"

systemctl daemon-reload
systemctl enable "$service_name"

cat <<EOF
Installed $service_name

Repo target    : $repo_target
Gateway host   : $gateway_host
Gateway port   : $gateway_port
Interface mode : $interface_mode
Allow TX       : $allow_tx
Storage root   : $storage_root
Runtime service: $runtime_service
Service path   : $service_path

Next steps:
1. systemctl start $service_name
2. systemctl status $service_name --no-pager
3. journalctl -u $service_name -n 50 --no-pager
EOF