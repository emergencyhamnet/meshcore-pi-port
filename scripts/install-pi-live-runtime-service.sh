#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="meshcore-pi-live-runtime.service"
template_path="$repo_root/deploy/systemd/$service_name"
service_path="/etc/systemd/system/$service_name"
repo_target="${MESHCORE_PI_SERVICE_REPO_TARGET:-$repo_root}"
interface_mode="${MESHCORE_PI_INTERFACE_MODE:-app}"
runtime_bin="${MESHCORE_PI_LIVE_RUNTIME_BIN:-$repo_target/bin/pi-live-runtime}"

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
		fail "run this installer as root, for example: sudo bash scripts/install-pi-live-runtime-service.sh"
	fi
}

require_file() {
	local file_path="$1"
	[[ -f "$file_path" ]] || fail "required file not found: $file_path"
}

require_root
require_file "$template_path"
require_file "$repo_target/scripts/run-pi-live-runtime.sh"
[[ -x "$runtime_bin" ]] || fail "runtime binary not found or not executable: $runtime_bin"

case "$interface_mode" in
	app)
		runtime_endpoint="${MESHCORE_PI_RUNTIME_ENDPOINT:-tcp://127.0.0.1:5041}"
		exec_start="/usr/bin/env python3 $repo_target/scripts/run-pi-companion-service.py"
		require_file "$repo_target/scripts/run-pi-companion-service.py"
		;;
	web)
		runtime_endpoint="${MESHCORE_PI_RUNTIME_ENDPOINT:-serial:///dev/ttyS0}"
		exec_start="/bin/bash $repo_target/scripts/run-pi-live-runtime.sh"
		;;
	*)
		fail "MESHCORE_PI_INTERFACE_MODE must be app or web (got: $interface_mode)"
		;;
esac

mkdir -p "$storage_root/identity" "$storage_root/state" "$storage_root/channels" "$storage_root/logs"

sed \
	-e "s|/opt/meshcore-pi-port|$repo_target|g" \
	-e "s|Environment=MESHCORE_PI_INTERFACE_MODE=app|Environment=MESHCORE_PI_INTERFACE_MODE=$interface_mode|g" \
	-e "s|tcp://127.0.0.1:5041|$runtime_endpoint|g" \
	-e "s|ExecStart=/usr/bin/env python3 /opt/meshcore-pi-port/scripts/run-pi-companion-service.py|ExecStart=$exec_start|g" \
	-e "s|/var/lib/meshcore-pi-port|$storage_root|g" \
	"$template_path" > "$service_path"

systemctl daemon-reload
systemctl enable "$service_name"

cat <<EOF
Installed $service_name

Repo target     : $repo_target
Interface mode  : $interface_mode
Runtime binary  : $runtime_bin
Runtime endpoint: $runtime_endpoint
Storage root    : $storage_root
Service path    : $service_path

Next steps:
1. systemctl start $service_name
2. systemctl status $service_name --no-pager
3. journalctl -u $service_name -n 50 --no-pager
EOF