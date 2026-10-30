#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="meshcore-pi-hat-sensors.service"
template="$repo_root/deploy/systemd/$service_name"
service_path="/etc/systemd/system/$service_name"
repo_target="${MESHCORE_PI_SERVICE_REPO_TARGET:-$repo_root}"
snapshot_path="${MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH:-/tmp/meshcore-pi-telemetry.env}"
service_user="meshcore-pi-sensors"
enable_service=0

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

[[ "$(id -u)" -eq 0 ]] || fail "run this installer as root, for example: sudo bash scripts/install-pi-hat-sensors-service.sh"
[[ -f "$template" ]] || fail "service template not found: $template"
[[ -f "$repo_target/scripts/pi_hat_sensor_sampler.py" ]] || fail "sampler not found: $repo_target/scripts/pi_hat_sensor_sampler.py"

if [[ "${1:-}" == "--enable" ]]; then
	enable_service=1
elif [[ "$#" -gt 0 ]]; then
	fail "usage: sudo bash scripts/install-pi-hat-sensors-service.sh [--enable]"
fi

if ! getent group i2c >/dev/null; then
	fail "I2C group not found; enable I2C and install the OS I2C tools first"
fi
if ! /usr/bin/python3 -c 'import smbus2' >/dev/null 2>&1; then
	fail "python3-smbus2 is missing; install it with: sudo apt install python3-smbus2"
fi

if ! id "$service_user" >/dev/null 2>&1; then
	useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin "$service_user"
fi
usermod -a -G i2c "$service_user"

sed \
	-e "s|/opt/meshcore-pi-port|$repo_target|g" \
	-e "s|/tmp/meshcore-pi-telemetry.env|$snapshot_path|g" \
	"$template" > "$service_path"
chmod 0644 "$service_path"
systemctl daemon-reload

if [[ "$enable_service" -eq 1 ]]; then
	systemctl enable --now "$service_name"
else
	printf 'Installed disabled service; no sensor reads will start until explicitly enabled.\n'
fi

cat <<EOF
Installed $service_name

Repo target : $repo_target
Service user: $service_user (I2C group only)
Snapshot    : $snapshot_path
Enabled now : $enable_service

Enable later with:
  sudo systemctl enable --now $service_name

Check status/logs with:
  systemctl status $service_name --no-pager
  journalctl -u $service_name -n 50 --no-pager

This service writes a local snapshot only. It does not change MeshCore telemetry permissions,
send radio packets, or configure a basestation. Enable the native node's telemetry permissions
separately in the Pi UI after reviewing the disclosure scope.
EOF