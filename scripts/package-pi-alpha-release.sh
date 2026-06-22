#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
release_name="${1:-}"
output_dir="${MESHCORE_PI_RELEASE_OUT_DIR:-$repo_root/dist}"
runtime_bin="${MESHCORE_PI_LIVE_RUNTIME_BIN:-$repo_root/bin/pi-live-runtime}"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

[[ -n "$release_name" ]] || fail "usage: scripts/package-pi-alpha-release.sh <release-name>"

mkdir -p "$output_dir"

source_root="$output_dir/meshcore-pi-port-$release_name-source"
binary_root="$output_dir/meshcore-pi-port-$release_name-pi-binary"

rm -rf "$source_root" "$binary_root"
mkdir -p "$source_root" "$binary_root"

copy_tree() {
	local from="$1"
	local to="$2"
	mkdir -p "$(dirname "$to")"
	cp -R "$from" "$to"
}

copy_file() {
	local from="$1"
	local to="$2"
	mkdir -p "$(dirname "$to")"
	cp "$from" "$to"
}

pushd "$repo_root" >/dev/null

for path in \
	README.md \
	RELEASE.md \
	license.txt \
	main \
	platform \
	src \
	examples/companion_radio \
	include \
	lib/ed25519 \
	scripts \
	deploy/systemd \
	ui \
	docs/PI_NATIVE_BRINGUP.md \
	docs/pi_node_interface.md \
	docs/pi_alpha_release.md; do
	if [[ -d "$path" ]]; then
		copy_tree "$path" "$source_root/$path"
	else
		copy_file "$path" "$source_root/$path"
	fi
	done

	tar -czf "$output_dir/meshcore-pi-port-$release_name-source.tar.gz" -C "$output_dir" "$(basename "$source_root")"

	if [[ -x "$runtime_bin" ]]; then
		for path in \
			README.md \
			scripts/run-pi-live-runtime.sh \
			scripts/run-pi-companion-service.py \
			scripts/install-pi-live-runtime-service.sh \
			scripts/install-pi-node-ui-service.sh \
			scripts/write-dummy-telemetry-snapshot.py \
			deploy/systemd/meshcore-pi-live-runtime.service \
			deploy/systemd/meshcore-pi-node-ui.service \
			docs/pi_alpha_release.md \
			docs/PI_NATIVE_BRINGUP.md; do
			if [[ -d "$path" ]]; then
				copy_tree "$path" "$binary_root/$path"
			else
				copy_file "$path" "$binary_root/$path"
			fi
		done

		copy_file "$runtime_bin" "$binary_root/bin/pi-live-runtime"
		tar -czf "$output_dir/meshcore-pi-port-$release_name-pi-binary.tar.gz" -C "$output_dir" "$(basename "$binary_root")"
		printf 'Created binary archive: %s\n' "$output_dir/meshcore-pi-port-$release_name-pi-binary.tar.gz"
	else
		printf 'Skipping binary archive; runtime binary not found at %s\n' "$runtime_bin"
	fi

	popd >/dev/null

	printf 'Created source archive: %s\n' "$output_dir/meshcore-pi-port-$release_name-source.tar.gz"