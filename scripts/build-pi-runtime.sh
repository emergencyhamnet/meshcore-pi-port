#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_bin="${MESHCORE_PI_RUNTIME_BIN:-$repo_root/bin/pi-companion-runtime}"
runtime_endpoint="${MESHCORE_PI_RUNTIME_ENDPOINT:-serial:///dev/ttyS0}"
storage_root="${MESHCORE_PI_STORAGE_ROOT:-/var/lib/meshcore-pi-port}"
status_file="$storage_root/state/runtime-bridge.status"
compiler="${CXX:-g++}"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

require_file() {
	local file_path="$1"
	[[ -f "$file_path" ]] || fail "missing required source file: $file_path"
}

[[ "$(uname -s)" == "Linux" ]] || fail "run this script on the Raspberry Pi host"
command -v "$compiler" >/dev/null 2>&1 || fail "compiler not found: $compiler"

require_file "$repo_root/main/pi_companion_main.cpp"
require_file "$repo_root/main/pi_runtime_boot.cpp"
require_file "$repo_root/main/pi_runtime_adapter.cpp"
require_file "$repo_root/main/pi_donor_runtime_bridge.cpp"
require_file "$repo_root/main/pi_donor_host_contracts.cpp"
require_file "$repo_root/main/pi_donor_datastore_probe.cpp"
require_file "$repo_root/main/pi_donor_mymesh_probe.cpp"
require_file "$repo_root/platform/pi_board.cpp"
require_file "$repo_root/platform/pi_gpio.cpp"
require_file "$repo_root/platform/pi_spi.cpp"
require_file "$repo_root/platform/pi_storage.cpp"
require_file "$repo_root/platform/pi_transport.cpp"

mkdir -p "$storage_root/identity" "$storage_root/state" "$storage_root/channels" "$storage_root/logs"

cat <<EOF
Pi runtime preflight complete.

Repository root : $repo_root
Compiler        : $compiler
Runtime binary  : $runtime_bin
Runtime endpoint: $runtime_endpoint
Storage root    : $storage_root
Status file     : $status_file

What this script validates today:
1. you are on a Linux host
2. a C++ compiler is installed
3. the Pi runtime source surface is present
4. the storage layout exists

Next on the Pi:
1. build the runtime binary at $runtime_bin using your Pi-native compiler integration
2. run the binary with MESHCORE_PI_RUNTIME_ENDPOINT and MESHCORE_PI_STORAGE_ROOT set as needed
3. run scripts/run-donor-api-smoke.sh
4. run scripts/run-radio-smoke.sh

Reference: docs/PI_NATIVE_BRINGUP.md
EOF