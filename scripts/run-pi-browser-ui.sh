#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ui_host="${MESHCORE_PI_BROWSER_UI_HOST:-0.0.0.0}"
ui_port="${MESHCORE_PI_BROWSER_UI_PORT:-8099}"
companion_host="${MESHCORE_PI_BROWSER_UI_COMPANION_HOST:-127.0.0.1}"
companion_port="${MESHCORE_PI_BROWSER_UI_COMPANION_PORT:-5040}"
app_name="${MESHCORE_PI_BROWSER_UI_APP_NAME:-pi-browser-ui}"
protocol_version="${MESHCORE_PI_BROWSER_UI_PROTOCOL_VERSION:-3}"
timeout_seconds="${MESHCORE_PI_BROWSER_UI_TIMEOUT_SECONDS:-5.0}"
gateway_enabled="${MESHCORE_PI_BROWSER_UI_ENABLE_GATEWAY_LINK:-1}"
gateway_host="${MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_HOST:-0.0.0.0}"
gateway_port="${MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_PORT:-7463}"
gateway_allow_tx="${MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_ALLOW_TX:-0}"
runtime_service="${MESHCORE_PI_LIVE_RUNTIME_SERVICE:-meshcore-pi-live-runtime.service}"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

[[ "$(uname -s)" == "Linux" ]] || fail "run this script on the Raspberry Pi host"
command -v python3 >/dev/null 2>&1 || fail "python3 is required on the Pi host"
[[ -d "$repo_root/ui-native/src/meshcore_ui_native" ]] || fail "ui-native package not found under $repo_root/ui-native/src"

export PYTHONPATH="$repo_root/ui-native/src${PYTHONPATH:+:$PYTHONPATH}"

printf 'Starting MeshCore browser UI\n'
printf 'UI bind         : %s:%s\n' "$ui_host" "$ui_port"
printf 'Companion target: %s:%s\n' "$companion_host" "$companion_port"
printf 'App name        : %s\n' "$app_name"
printf 'Protocol version: %s\n' "$protocol_version"
if [[ "$gateway_enabled" == "1" || "$gateway_enabled" == "true" || "$gateway_enabled" == "yes" ]]; then
	printf 'Gateway link    : %s:%s (tx=%s)\n' "$gateway_host" "$gateway_port" "$gateway_allow_tx"
fi

cd "$repo_root"
command=(
	python3 -m meshcore_ui_native
	--web
	--host "$companion_host"
	--port "$companion_port"
	--app-name "$app_name"
	--protocol-version "$protocol_version"
	--timeout "$timeout_seconds"
	--listen-host "$ui_host"
	--listen-port "$ui_port"
)

if [[ "$gateway_enabled" == "1" || "$gateway_enabled" == "true" || "$gateway_enabled" == "yes" ]]; then
	command+=(
		--gateway-link-host "$gateway_host"
		--gateway-link-port "$gateway_port"
		--gateway-link-service-name "$runtime_service"
	)
	if [[ "$gateway_allow_tx" == "1" || "$gateway_allow_tx" == "true" || "$gateway_allow_tx" == "yes" ]]; then
		command+=(--gateway-link-allow-basestation-tx)
	fi
fi

exec "${command[@]}"