#!/usr/bin/env bash
set -euo pipefail

spi_device="${MESHCORE_PI_SPI_DEVICE:-/dev/spidev0.0}"
gpio_chip="${MESHCORE_PI_GPIOCHIP:-/dev/gpiochip0}"
storage_root="${MESHCORE_PI_STORAGE_ROOT:-/var/lib/meshcore-pi-port}"
status_file="$storage_root/state/runtime-bridge.status"

fail() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

[[ "$(uname -s)" == "Linux" ]] || fail "run this script on the Raspberry Pi host"
[[ -e "$spi_device" ]] || fail "SPI device not present: $spi_device"
[[ -e "$gpio_chip" ]] || fail "GPIO chip not present: $gpio_chip"

printf 'Pi radio smoke preflight\n'
printf 'SPI device : %s\n' "$spi_device"
printf 'GPIO chip  : %s\n' "$gpio_chip"

if [[ -f "$status_file" ]]; then
	printf 'Runtime bridge status:\n'
	cat "$status_file"
fi

cat <<'EOF'
Expected SX1262 HAT mapping:
- NSS   : GPIO8
- DIO1  : GPIO25
- RESET : GPIO17
- BUSY  : GPIO24
- TXEN  : GPIO22
- RXEN  : GPIO27
- SPI   : SPI0
EOF

if command -v pinctrl >/dev/null 2>&1; then
	printf 'Current pinctrl state for radio pins:\n'
	pinctrl get 8 17 22 24 25 27
elif command -v raspi-gpio >/dev/null 2>&1; then
	printf 'Current raspi-gpio state for radio pins:\n'
	raspi-gpio get 8 17 22 24 25 27
else
	printf 'No pin state utility found; skipping live GPIO dump.\n'
fi

cat <<EOF
Radio smoke preflight passed.

This script verifies host visibility of the SPI and GPIO surfaces that the Pi runtime expects.

Next manual step:
start the Pi runtime binary, then confirm radio init does not hang and proceed to receive-only RF checks.

Reference: docs/PI_NATIVE_BRINGUP.md
EOF