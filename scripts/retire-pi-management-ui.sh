#!/usr/bin/env bash
set -euo pipefail

old_service_name="${MESHCORE_PI_OLD_UI_SERVICE:-meshcore-pi-node-ui.service}"
old_service_path="/etc/systemd/system/$old_service_name"
runtime_service="${MESHCORE_PI_LIVE_RUNTIME_SERVICE:-meshcore-pi-live-runtime.service}"
gateway_service="${MESHCORE_PI_GATEWAY_LINK_SERVICE:-meshcore-pi-gateway-link.service}"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

require_root() {
	if [[ "$(id -u)" -ne 0 ]]; then
		fail "run this cleanup as root, for example: sudo bash scripts/retire-pi-management-ui.sh"
	fi
}

require_root

if systemctl list-unit-files "$old_service_name" >/dev/null 2>&1; then
	if systemctl is-active --quiet "$old_service_name"; then
		printf 'Stopping %s\n' "$old_service_name"
		systemctl stop "$old_service_name"
	fi

	if systemctl is-enabled --quiet "$old_service_name"; then
		printf 'Disabling %s\n' "$old_service_name"
		systemctl disable "$old_service_name"
	fi
fi

if [[ -f "$old_service_path" ]]; then
	printf 'Removing unit file %s\n' "$old_service_path"
	rm -f "$old_service_path"
	systemctl daemon-reload
else
	printf 'No unit file found for %s\n' "$old_service_name"
fi

printf '\nRetained services:\n'
systemctl status "$runtime_service" --no-pager || true
printf '\n'
systemctl status "$gateway_service" --no-pager || true

cat <<EOF

Old local management UI retired: $old_service_name
Retained runtime service       : $runtime_service
Retained gateway service       : $gateway_service

Next steps:
1. install and start meshcore-pi-browser-ui.service
2. confirm nothing is listening on the old UI port if you intend to retire it fully
3. use journalctl -u meshcore-pi-browser-ui.service -f for live browser-UI logs
EOF