#!/usr/bin/env bash
set -euo pipefail

runtime_endpoint="${MESHCORE_PI_RUNTIME_ENDPOINT:-serial:///dev/ttyS0}"
storage_root="${MESHCORE_PI_STORAGE_ROOT:-/var/lib/meshcore-pi-port}"
status_file="$storage_root/state/runtime-bridge.status"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

require_status_value() {
	local expected="$1"
	grep -q "^${expected}$" "$status_file" || fail "runtime status missing ${expected}"
}

[[ "$(uname -s)" == "Linux" ]] || fail "run this script on the Raspberry Pi host"
[[ -f "$status_file" ]] || fail "runtime status file not found: $status_file"

printf 'Runtime status from %s:\n' "$status_file"
cat "$status_file"

require_status_value "bridge_ready=1"
require_status_value "transport_started=1"
require_status_value "transport_enabled=1"

case "$runtime_endpoint" in
	serial://*)
		serial_device="${runtime_endpoint#serial://}"
		[[ -e "$serial_device" ]] || fail "serial runtime endpoint not present: $serial_device"
		printf 'Serial donor API endpoint is present: %s\n' "$serial_device"
		;;
	tcp://*)
		endpoint_body="${runtime_endpoint#tcp://}"
		host="${endpoint_body%%:*}"
		port="${endpoint_body##*:}"
		python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2.0)
try:
	sock.connect((host, port))
finally:
	sock.close()
PY
		printf 'TCP donor API endpoint accepted a connection: %s\n' "$runtime_endpoint"
		;;
	*)
		fail "unsupported runtime endpoint: $runtime_endpoint"
		;;
esac

cat <<EOF
Donor API smoke preflight passed.

This script verifies:
1. the runtime booted far enough to persist bridge status
2. the selected transport endpoint is available

Next manual step:
run one companion handshake against the live endpoint for DEVICE_QUERY / APP_START / GET_DEVICE_TIME / GET_CONTACTS.

Reference: docs/PI_NATIVE_BRINGUP.md
EOF