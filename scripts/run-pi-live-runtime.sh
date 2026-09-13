#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_bin="${MESHCORE_PI_LIVE_RUNTIME_BIN:-$repo_root/bin/pi-live-runtime}"
runtime_endpoint="${MESHCORE_PI_RUNTIME_ENDPOINT:-serial:///dev/ttyS0}"
storage_root="${MESHCORE_PI_STORAGE_ROOT:-/var/lib/meshcore-pi-port}"
status_file="$storage_root/state/runtime-bridge.status"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

[[ "$(uname -s)" == "Linux" ]] || fail "run this script on the Raspberry Pi host"
[[ -x "$runtime_bin" ]] || fail "runtime binary not found or not executable: $runtime_bin"

if pgrep -x pi-live-runtime >/dev/null 2>&1; then
	printf 'Stopping existing pi-live-runtime processes before launch.\n'
	pkill -x pi-live-runtime || true

	for _ in {1..20}; do
		if ! pgrep -x pi-live-runtime >/dev/null 2>&1; then
			break
		fi
		sleep 0.25
	done

	if pgrep -x pi-live-runtime >/dev/null 2>&1; then
		printf 'Existing processes did not exit after SIGTERM; forcing shutdown.\n'
		pkill -KILL -x pi-live-runtime || true
	fi

	pgrep -ax pi-live-runtime >/dev/null 2>&1 && fail "pi-live-runtime is still running after forced cleanup"
fi

mkdir -p "$storage_root/identity" "$storage_root/state" "$storage_root/channels" "$storage_root/logs"

printf 'Starting Pi live runtime\n'
printf 'Runtime binary  : %s\n' "$runtime_bin"
printf 'Runtime endpoint: %s\n' "$runtime_endpoint"
printf 'Storage root    : %s\n' "$storage_root"
printf 'Status file     : %s\n' "$status_file"

export MESHCORE_PI_RUNTIME_ENDPOINT="$runtime_endpoint"
export MESHCORE_PI_STORAGE_ROOT="$storage_root"

exec "$runtime_bin"