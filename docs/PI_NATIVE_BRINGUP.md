# Pi Native Bring-Up

This document defines the first Pi-native bring-up path for the donor-aligned runtime.

What this phase is for:

1. move from Windows-side structural probes into execution on the Raspberry Pi
2. verify runtime boot, storage, transport, and radio-host visibility before wider RF testing
3. stage hardware work so failures are isolated to one surface at a time

What this phase is not for:

1. full external integration stacks
2. broad interoperability testing across many donor features
3. uncontrolled live transmit testing as the first hardware step

For standalone alpha app-mode validation, telemetry can come from a static snapshot file instead of live sensors.

Generate one with:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
```

There is now a separate host-radio bring-up path for the missing Linux HAL layer:

1. `scripts/build-pi-radiolib-smoke.sh`
2. run the smoke binary without transmit first
3. only then do one controlled `--tx` burst

## Preconditions

Run this on the Raspberry Pi host that has the target radio HAT attached.

Minimum expectations:

1. Linux userspace with `bash`
2. a C++ compiler installed, usually `g++`
3. the repo checked out locally on the Pi
4. SPI enabled on the Pi
5. the radio HAT wired to the expected GPIO mapping
6. `lgpio` development headers installed for the non-Arduino RadioLib HAL
7. a system-installed `RadioLib` prefix, default `/usr/local`

Expected HAT mapping:

1. `NSS = GPIO8`
2. `DIO1 = GPIO25`
3. `RESET = GPIO17`
4. `BUSY = GPIO24`
5. `TXEN = GPIO22`
6. `RXEN = GPIO27`
7. `SPI = SPI0`

See also:

1. `docs/pi_hat_pinout.md` for the dedicated pinout reference and radio-family note

## Environment

Export the runtime settings before bring-up.

Example:

```bash
export MESHCORE_PI_RUNTIME_ENDPOINT="serial:///dev/ttyS0"
export MESHCORE_PI_STORAGE_ROOT="/var/lib/meshcore-pi-port"
export MESHCORE_PI_RUNTIME_BIN="$PWD/bin/pi-companion-runtime"
export MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH="/tmp/meshcore-pi-telemetry.env"
```

Current defaults if you do not override them:

1. runtime endpoint: `serial:///dev/ttyS0`
2. storage root: `/var/lib/meshcore-pi-port`
3. runtime status file: `/var/lib/meshcore-pi-port/state/runtime-bridge.status`

## Optional Service Install

Once the live runtime is built and manually validated, install the boot-time service with:

```bash
sudo bash scripts/install-pi-live-runtime-service.sh
```

What this does:

1. installs `deploy/systemd/meshcore-pi-live-runtime.service` into `/etc/systemd/system`
2. points the unit at the checked-out repo path and current runtime binary
3. creates the runtime storage directories if needed
4. enables the service for boot

Recommended follow-up:

```bash
sudo systemctl start meshcore-pi-live-runtime.service
sudo systemctl status meshcore-pi-live-runtime.service --no-pager
journalctl -u meshcore-pi-live-runtime.service -n 50 --no-pager
```

## Bring-Up Order

Use this order exactly.

1. `scripts/build-pi-runtime.sh`
2. run the runtime binary
3. `scripts/run-donor-api-smoke.sh`
4. `scripts/run-radio-smoke.sh`
5. do one receive-only RF check
6. only then move to controlled transmit testing

## RadioLib Host Bring-Up

Use this only when you are working on the missing live Linux radio binding.

Run:

```bash
scripts/build-pi-radiolib-smoke.sh
bin/pi-radiolib-smoke
```

Optional controlled burst:

```bash
bin/pi-radiolib-smoke --tx meshcore-smoke
```

This path is intentionally separate from the donor runtime. It is meant to validate:

1. `RadioLib` is installed on the Pi in a usable non-Arduino layout
2. `lgpio` can drive the expected GPIO and SPI surfaces
3. the donor `CustomSX1262Wrapper` can initialize on Linux before it is folded into the persistent runtime

## Step 1: Build The Runtime Binary

The repo now has a concrete Pi-native build script for the runtime entrypoint, and it performs the preflight checks as part of the build.

Run:

```bash
scripts/build-pi-runtime.sh
```

Current build behavior:

1. compiles the Pi runtime into `$MESHCORE_PI_RUNTIME_BIN`
2. uses a native `g++` command line with the Pi runtime sources, donor companion sources, core MeshCore sources, helper sources, and the local `lib/ed25519` C sources
3. bakes in the current firmware defaults used by the donor probe surface unless you override `FIRMWARE_VERSION` or `FIRMWARE_BUILD_DATE`

Expected outcome from the first build:

1. a runtime binary at `$MESHCORE_PI_RUNTIME_BIN`
2. no donor source edits during bring-up
3. the binary exits with code `0` only when all current boot, storage, transport, and donor probe checks pass

## Step 2: Run The Runtime

Run:

```bash
bash scripts/run-pi-live-runtime.sh
```

This launcher preserves the same exported environment, ensures only one `pi-live-runtime` process is active, and then `exec`s the live runtime binary.

Minimum success conditions:

1. storage directories exist
2. runtime status file is written
3. transport is started and enabled
4. process does not hang during board, GPIO, SPI, or radio-path setup

The current status file path is:

```text
$MESHCORE_PI_STORAGE_ROOT/state/runtime-bridge.status
```

## Step 3: Donor API Smoke

Run:

```bash
scripts/run-donor-api-smoke.sh
```

This checks:

1. `bridge_ready=1`
2. `transport_started=1`
3. `transport_enabled=1`
4. the configured serial or TCP endpoint is actually present

After that, do one manual companion handshake against the live endpoint covering:

1. `CMD_DEVICE_QUERY`
2. `CMD_APP_START`
3. `CMD_GET_DEVICE_TIME`
4. `CMD_GET_CONTACTS`

Or run the automated local handshake check on the Pi:

```bash
MESHCORE_PI_STORAGE_ROOT=/home/n2dh/meshcore-pi-port-state python3 scripts/run-live-companion-handshake.py
```

This temporarily brings the live runtime up on a localhost TCP endpoint, exercises the four companion commands, and then restores the default serial live runtime.

## Step 4: Radio Smoke

Run:

```bash
scripts/run-radio-smoke.sh
```

This checks:

1. SPI device visibility, default ` /dev/spidev0.0`
2. GPIO chip visibility, default ` /dev/gpiochip0`
3. expected radio HAT pin mapping
4. live GPIO state dump if `pinctrl` or `raspi-gpio` is available

## Step 5: First RF Test

Do not start with transmit.

First RF test order:

1. bring the runtime up with the HAT attached
2. confirm radio init does not hang
3. start a persisted-contact watcher on the Pi:

```bash
MESHCORE_PI_STORAGE_ROOT=/home/n2dh/meshcore-pi-port-state \
python3 scripts/await-pi-rx-contact.py --timeout 60
```

4. leave the Pi in receive mode
5. transmit from a known-good donor node nearby
6. verify the watcher reports a new or updated contact record in `$MESHCORE_PI_STORAGE_ROOT/channels/contacts3`

Only after receive works should you try:

1. one self advert transmit
2. one controlled app-facing exchange

## Exit Code Map

The current Pi entrypoint exits non-zero when a specific bring-up stage fails.

From `main/pi_companion_main.cpp`:

1. `1` board bootstrap failed
2. `2` GPIO init failed
3. `3` SPI init failed
4. `4` radio path setup failed
5. `5` storage init failed
6. `6` transport preflight failed
7. `7` transport begin failed
8. `8` transport enable/connect failed
9. `9` donor runtime bridge not ready
10. `10` donor host contracts not ready
11. `11` donor datastore probe failed
12. `12` donor MyMesh probe failed

## Decision Point

Once the Pi can:

1. start the runtime
2. persist runtime status
3. answer the companion handshake at the live endpoint
4. see the expected SPI and GPIO surfaces

then the next work should shift from host-side probes to Pi-native runtime and RF validation.