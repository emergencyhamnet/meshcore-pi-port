#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_bin="${MESHCORE_PI_RADIOLIB_SMOKE_BIN:-$repo_root/bin/pi-radiolib-smoke}"
build_dir="${MESHCORE_PI_RADIOLIB_SMOKE_BUILD_DIR:-$repo_root/.build/pi-radiolib-smoke}"
compiler="${CXX:-g++}"
c_compiler="${CC:-gcc}"
radiolib_prefix="${MESHCORE_PI_RADIOLIB_PREFIX:-/usr/local}"
radiolib_include_dir="${MESHCORE_PI_RADIOLIB_INCLUDE_DIR:-$radiolib_prefix/include/RadioLib}"
radiolib_lib_dir="${MESHCORE_PI_RADIOLIB_LIB_DIR:-$radiolib_prefix/lib}"
radiolib_lib_name="${MESHCORE_PI_RADIOLIB_LIB_NAME:-RadioLib}"
lgpio_lib_name="${MESHCORE_PI_LGPIO_LIB_NAME:-lgpio}"

defines=(
	-D__linux__
	-DNDEBUG
	-DMESHCORE_PI_BOARD_OWNS_RF_SWITCH
	-DFIRMWARE_VER_CODE=13
	-DLORA_FREQ=910.525
	-DLORA_BW=62.5
	-DLORA_SF=7
	-DLORA_CR=5
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
	-I"$radiolib_include_dir"
)

sources=(
	main/pi_radiolib_smoke.cpp
	platform/pi_board.cpp
	platform/pi_gpio.cpp
	platform/pi_radiolib_hal.cpp
	src/helpers/radiolib/RadioLibWrappers.cpp
)

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

require_file() {
	local file_path="$1"
	[[ -f "$file_path" ]] || fail "missing required file: $file_path"
}

[[ "$(uname -s)" == "Linux" ]] || fail "run this script on the Raspberry Pi host"
command -v "$compiler" >/dev/null 2>&1 || fail "compiler not found: $compiler"
command -v "$c_compiler" >/dev/null 2>&1 || fail "C compiler not found: $c_compiler"
[[ -f "$radiolib_include_dir/RadioLib.h" ]] || fail "RadioLib header not found at $radiolib_include_dir/RadioLib.h"
[[ -f "/usr/include/lgpio.h" ]] || fail "lgpio header not found at /usr/include/lgpio.h"

for relative_source in "${sources[@]}"; do
	require_file "$repo_root/$relative_source"
done

mkdir -p "$build_dir" "$(dirname "$output_bin")"

objects=()
for relative_source in "${sources[@]}"; do
	object_path="$build_dir/${relative_source%.cpp}.o"
	mkdir -p "$(dirname "$object_path")"
	objects+=("$object_path")
done

printf 'Building Pi RadioLib smoke binary with %s\n' "$compiler"
printf 'RadioLib include : %s\n' "$radiolib_include_dir"
printf 'RadioLib lib dir : %s\n' "$radiolib_lib_dir"
printf 'Output binary    : %s\n' "$output_bin"

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
		-o "${objects[$index]}"
done

"$compiler" \
	"${objects[@]}" \
	-L"$radiolib_lib_dir" \
	-l"$radiolib_lib_name" \
	-l"$lgpio_lib_name" \
	-lpthread \
	-o "$output_bin"
popd >/dev/null

cat <<EOF
Pi RadioLib smoke build complete.

Repository root : $repo_root
Output binary   : $output_bin
Build dir       : $build_dir
RadioLib include: $radiolib_include_dir
RadioLib lib dir: $radiolib_lib_dir

Next on the Pi:
1. run $output_bin
2. if init succeeds, run $output_bin --tx meshcore-smoke
3. only then decide whether to fold this HAL path into the donor runtime
EOF