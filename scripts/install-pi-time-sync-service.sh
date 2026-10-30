#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="meshcore-pi-time-sync.service"
timer_name="meshcore-pi-time-sync.timer"
service_template="$repo_root/deploy/systemd/$service_name"
timer_template="$repo_root/deploy/systemd/$timer_name"
service_path="/etc/systemd/system/$service_name"
timer_path="/etc/systemd/system/$timer_name"
repo_target="${MESHCORE_PI_SERVICE_REPO_TARGET:-$repo_root}"

default_storage_root() {
	local invoking_user="${SUDO_USER:-${USER:-}}"
	if [[ -n "$invoking_user" ]]; then
		local user_state_root="/home/$invoking_user/meshcore-pi-port-state"
		if [[ -d "$user_state_root" ]]; then
			printf '%s\n' "$user_state_root"
			return
		fi
	fi

	printf '%s\n' "/var/lib/meshcore-pi-port"
}

storage_root="${MESHCORE_PI_STORAGE_ROOT:-$(default_storage_root)}"
time_source="${MESHCORE_PI_TIME_SOURCE:-host}"
set_host_clock="${MESHCORE_PI_SET_HOST_CLOCK:-0}"
gpsd_host="${MESHCORE_PI_GPSD_HOST:-127.0.0.1}"
gpsd_port="${MESHCORE_PI_GPSD_PORT:-2947}"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

require_root() {
	if [[ "$(id -u)" -ne 0 ]]; then
		fail "run this installer as root, for example: sudo bash scripts/install-pi-time-sync-service.sh"
	fi
}

require_file() {
	local file_path="$1"
	[[ -f "$file_path" ]] || fail "required file not found: $file_path"
}

require_root
require_file "$service_template"
require_file "$timer_template"
require_file "$repo_target/scripts/sync-pi-node-time.py"
require_file "$repo_target/scripts/run-live-set-device-time.py"

sed \
	-e "s|/opt/meshcore-pi-port|$repo_target|g" \
	-e "s|/var/lib/meshcore-pi-port|$storage_root|g" \
	-e "s|MESHCORE_PI_TIME_SOURCE=host|MESHCORE_PI_TIME_SOURCE=$time_source|g" \
	-e "s|MESHCORE_PI_SET_HOST_CLOCK=0|MESHCORE_PI_SET_HOST_CLOCK=$set_host_clock|g" \
	-e "s|MESHCORE_PI_GPSD_HOST=127.0.0.1|MESHCORE_PI_GPSD_HOST=$gpsd_host|g" \
	-e "s|MESHCORE_PI_GPSD_PORT=2947|MESHCORE_PI_GPSD_PORT=$gpsd_port|g" \
	"$service_template" > "$service_path"

cp "$timer_template" "$timer_path"

systemctl daemon-reload
systemctl enable "$timer_name"

cat <<EOF
Installed $service_name and $timer_name

Repo target    : $repo_target
Storage root   : $storage_root
Time source    : $time_source
Set host clock : $set_host_clock
GPSD host      : $gpsd_host
GPSD port      : $gpsd_port
Service path   : $service_path
Timer path     : $timer_path

Next steps:
1. systemctl start $service_name
2. systemctl start $timer_name
3. systemctl status $service_name --no-pager
4. systemctl list-timers $timer_name --all
EOF