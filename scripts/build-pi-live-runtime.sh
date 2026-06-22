#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_bin="${MESHCORE_PI_LIVE_RUNTIME_BIN:-$repo_root/bin/pi-live-runtime}"
runtime_endpoint="${MESHCORE_PI_RUNTIME_ENDPOINT:-serial:///dev/ttyS0}"
storage_root="${MESHCORE_PI_STORAGE_ROOT:-/var/lib/meshcore-pi-port}"
status_file="$storage_root/state/runtime-bridge.status"
compiler="${CXX:-g++}"
build_dir="${MESHCORE_PI_LIVE_BUILD_DIR:-$repo_root/.build/pi-live-runtime}"
radiolib_prefix="${MESHCORE_PI_RADIOLIB_PREFIX:-/usr/local}"
radiolib_include_dir="${MESHCORE_PI_RADIOLIB_INCLUDE_DIR:-$radiolib_prefix/include/RadioLib}"
radiolib_lib_dir="${MESHCORE_PI_RADIOLIB_LIB_DIR:-$radiolib_prefix/lib}"

defines=(
	-D__linux__
	-DNDEBUG
	-DMESHCORE_PI_LIVE_RADIO
	-DMESHCORE_PI_BOARD_OWNS_RF_SWITCH
	-DSX126X_TXEN=22
	-DSX126X_RXEN=27
	-DSX126X_DIO2_AS_RF_SWITCH=true
	-DSX126X_DIO3_TCXO_VOLTAGE=1.8
	-DSX126X_CURRENT_LIMIT=140
	-DFIRMWARE_VER_CODE=13
	-DFIRMWARE_VERSION='"v1.16.0"'
	-DFIRMWARE_BUILD_DATE='"6 Jun 2026"'
	-DLORA_FREQ=910.525
	-DLORA_BW=62.5
	-DLORA_SF=7
	-DLORA_CR=5
	# Keep the chip-drive ceiling at 17 dBm for the Pi HAT build; field measurements
	# showed about 30 dBm output at the test port at this setting, which is already
	# near the module's practical advertised maximum once PA gain and coax loss are included.
	-DLORA_TX_POWER=17
	-DMAX_CONTACTS=100
	-DMAX_GROUP_CHANNELS=15
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
	-I"$radiolib_include_dir"
)

sources=(
	main/pi_live_runtime_main.cpp
	main/pi_runtime_boot.cpp
	main/pi_runtime_adapter.cpp
	main/pi_donor_runtime_bridge.cpp
	main/pi_donor_host_contracts.cpp
	main/pi_donor_live_runtime.cpp
	main/pi_runtime_target.cpp
	platform/pi_board.cpp
	platform/pi_gpio.cpp
	platform/pi_spi.cpp
	platform/pi_storage.cpp
	platform/pi_transport.cpp
	platform/pi_radiolib_hal.cpp
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
	src/helpers/radiolib/RadioLibWrappers.cpp
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
[[ -f "$radiolib_include_dir/RadioLib.h" ]] || fail "RadioLib header not found at $radiolib_include_dir/RadioLib.h"
[[ -f /usr/include/lgpio.h ]] || fail "lgpio header not found at /usr/include/lgpio.h"

for relative_source in "${sources[@]}" "${c_sources[@]}"; do
	require_file "$repo_root/$relative_source"
done

mkdir -p "$storage_root/identity" "$storage_root/state" "$storage_root/channels" "$storage_root/logs"
mkdir -p "$build_dir" "$(dirname "$runtime_bin")"

cpp_objects=()
for relative_source in "${sources[@]}"; do
	object_path="$build_dir/${relative_source%.cpp}.o"
	mkdir -p "$(dirname "$object_path")"
	cpp_objects+=("$object_path")
done

c_objects=()
for relative_source in "${c_sources[@]}"; do
	object_path="$build_dir/${relative_source%.c}.o"
	mkdir -p "$(dirname "$object_path")"
	c_objects+=("$object_path")
done

printf 'Building Pi live runtime binary with %s\n' "$compiler"
printf 'RadioLib include : %s\n' "$radiolib_include_dir"
printf 'RadioLib lib dir : %s\n' "$radiolib_lib_dir"
printf 'Output binary    : %s\n' "$runtime_bin"

pushd "$repo_root" >/dev/null
for index in "${!sources[@]}"; do
	"$compiler" \
		-std=c++17 \
		-O2 \
		-Wall \
		-Wextra \
		"${includes[@]}" \
		"${defines[@]}" \
		-c "${sources[$index]}" \
		-o "${cpp_objects[$index]}"
done

for index in "${!c_sources[@]}"; do
	gcc \
		-O2 \
		-Wall \
		-Wextra \
		"${includes[@]}" \
		-D__linux__ \
		-DNDEBUG \
		-c "${c_sources[$index]}" \
		-o "${c_objects[$index]}"
done

"$compiler" \
	"${cpp_objects[@]}" \
	"${c_objects[@]}" \
	-L"$radiolib_lib_dir" \
	-lRadioLib \
	-llgpio \
	-lcrypto \
	-lpthread \
	-o "$runtime_bin"
popd >/dev/null

cat <<EOF
Pi live runtime build complete.

Runtime binary  : $runtime_bin
Runtime endpoint: $runtime_endpoint
Storage root    : $storage_root
Status file     : $status_file

Next on the Pi:
1. run bash scripts/run-pi-live-runtime.sh
2. inspect $status_file
3. validate donor traffic against the live runtime path
EOF