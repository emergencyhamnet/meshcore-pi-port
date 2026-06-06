#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_bin="${MESHCORE_PI_RUNTIME_BIN:-$repo_root/bin/pi-companion-runtime}"
runtime_endpoint="${MESHCORE_PI_RUNTIME_ENDPOINT:-serial:///dev/ttyS0}"
storage_root="${MESHCORE_PI_STORAGE_ROOT:-/var/lib/meshcore-pi-port}"
status_file="$storage_root/state/runtime-bridge.status"
compiler="${CXX:-g++}"
build_dir="${MESHCORE_PI_BUILD_DIR:-$repo_root/.build/pi-runtime}"
firmware_version="${FIRMWARE_VERSION:-v1.16.0}"
firmware_build_date="${FIRMWARE_BUILD_DATE:-6 Jun 2026}"

defines=(
	-D__linux__
	-DNDEBUG
	-DFIRMWARE_VER_CODE=13
	"-DFIRMWARE_VERSION=\"$firmware_version\""
	"-DFIRMWARE_BUILD_DATE=\"$firmware_build_date\""
	-DLORA_FREQ=915.0
	-DLORA_BW=250
	-DLORA_SF=10
	-DLORA_CR=5
	-DLORA_TX_POWER=20
	-DMAX_CONTACTS=100
	-DOFFLINE_QUEUE_SIZE=16
)

includes=(
	-I.
	-Imain
	-Iplatform
	-Isrc
	-Isrc/helpers
	-Iinclude
	-Iexamples/companion_radio
	-Ilib/ed25519
)

sources=(
	main/pi_companion_main.cpp
	main/pi_runtime_boot.cpp
	main/pi_runtime_adapter.cpp
	main/pi_donor_runtime_bridge.cpp
	main/pi_donor_host_contracts.cpp
	main/pi_donor_datastore_probe.cpp
	main/pi_donor_mymesh_probe.cpp
	platform/pi_board.cpp
	platform/pi_gpio.cpp
	platform/pi_spi.cpp
	platform/pi_storage.cpp
	platform/pi_transport.cpp
	src/Dispatcher.cpp
	src/Identity.cpp
	src/Mesh.cpp
	src/Packet.cpp
	src/Utils.cpp
	src/helpers/AdvertDataHelpers.cpp
	src/helpers/BaseChatMesh.cpp
	src/helpers/ClientACL.cpp
	src/helpers/CommonCLI.cpp
	src/helpers/IdentityStore.cpp
	src/helpers/RegionMap.cpp
	src/helpers/StaticPoolPacketManager.cpp
	src/helpers/TransportKeyStore.cpp
	src/helpers/TxtDataHelpers.cpp
	examples/companion_radio/DataStore.cpp
	examples/companion_radio/MyMesh.cpp
	)

c_sources=(
	lib/ed25519/add_scalar.c
	lib/ed25519/fe.c
	lib/ed25519/ge.c
	lib/ed25519/keypair.c
	lib/ed25519/key_exchange.c
	lib/ed25519/sc.c
	lib/ed25519/seed.c
	lib/ed25519/sha512.c
	lib/ed25519/sign.c
	lib/ed25519/verify.c
)

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

for relative_source in "${sources[@]}" "${c_sources[@]}"; do
	require_file "$repo_root/$relative_source"
done

mkdir -p "$storage_root/identity" "$storage_root/state" "$storage_root/channels" "$storage_root/logs"
mkdir -p "$build_dir" "$(dirname "$runtime_bin")"

compile_command=(
	"$compiler"
	-std=c++17
	-O2
	-Wall
	-Wextra
	"${includes[@]}"
	"${defines[@]}"
	"${sources[@]}"
	-x
	c
	"${c_sources[@]}"
	-x
	none
	-o
	"$runtime_bin"
)

printf 'Building Pi runtime binary with %s\n' "$compiler"
printf 'Build directory : %s\n' "$build_dir"
printf 'Output binary   : %s\n' "$runtime_bin"

pushd "$repo_root" >/dev/null
"${compile_command[@]}"
popd >/dev/null

cat <<EOF
Pi runtime build complete.

Repository root : $repo_root
Compiler        : $compiler
Runtime binary  : $runtime_bin
Runtime endpoint: $runtime_endpoint
Storage root    : $storage_root
Status file     : $status_file
Build dir       : $build_dir

What this script completed:
1. you are on a Linux host
2. a C++ compiler is installed
3. the Pi runtime source surface is present
4. the storage layout exists
5. the Pi runtime binary was compiled

Next on the Pi:
1. run the binary with MESHCORE_PI_RUNTIME_ENDPOINT and MESHCORE_PI_STORAGE_ROOT set as needed
2. inspect the exit code from main/pi_companion_main.cpp if startup fails
3. run scripts/run-donor-api-smoke.sh
4. run scripts/run-radio-smoke.sh

Reference: docs/PI_NATIVE_BRINGUP.md
EOF