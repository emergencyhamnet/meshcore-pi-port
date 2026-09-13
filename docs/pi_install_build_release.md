# Pi Install, Build, And Release

This guide describes the practical end-to-end flow for installing, building, validating, and releasing the Raspberry Pi HAT MeshCore port.

If you only need the high-level alpha scope, read `docs/pi_alpha_release.md` first. If you are actually trying to get a Pi node running or produce a release artifact, use this document.

## Scope

Use this guide when you want to:

1. install the Pi port on a Raspberry Pi host
2. build the native `pi-live-runtime` binary
3. validate the published MeshCore app path in `app` mode
4. package a source release and optional Pi binary bundle

This guide assumes the current supported radio family documented in `docs/pi_hat_pinout.md`.

## Host Requirements

Run these steps on the Raspberry Pi host that will own the runtime and radio HAT.

Minimum expected host state:

1. Raspberry Pi OS or another Linux environment with `bash`
2. SPI enabled
3. the supported radio HAT wired to the expected GPIO mapping
4. network access for cloning the repo and publishing artifacts if needed

Recommended quick checks before building:

```bash
uname -a
ls /dev/spidev0.0
ls /dev/gpiochip0
```

If SPI is not enabled yet, enable it before continuing. On Raspberry Pi OS that is commonly done with:

```bash
sudo raspi-config
```

Then enable SPI under the interface settings and reboot.

## Build Dependencies

The native Pi build script expects:

1. `g++`
2. `gcc`
3. `python3`
4. OpenSSL development headers for `-lcrypto`
5. `lgpio` development headers providing `/usr/include/lgpio.h`
6. a system-installed `RadioLib` with headers visible under a prefix such as `/usr/local/include/RadioLib`

Typical Debian or Raspberry Pi OS package bootstrap:

```bash
sudo apt update
sudo apt install -y build-essential git python3 python3-pip libssl-dev pkg-config
```

For `lgpio`, install the package set that provides both the runtime library and `/usr/include/lgpio.h` on your distribution. On many Pi-oriented systems this is typically an `lgpio` or `liblgpio-dev` package.

## RadioLib Requirement

The build does not vendor `RadioLib`. It expects a system installation.

Default paths used by the build:

1. headers: `/usr/local/include/RadioLib`
2. library: `/usr/local/lib`

If your `RadioLib` install lives elsewhere, override the build-time environment:

```bash
export MESHCORE_PI_RADIOLIB_INCLUDE_DIR=/custom/prefix/include/RadioLib
export MESHCORE_PI_RADIOLIB_LIB_DIR=/custom/prefix/lib
```

The build script will fail early if either of these is missing:

1. `RadioLib.h` under the configured include prefix
2. `lgpio.h` under `/usr/include`

That early failure is intentional so packaging and release builds do not silently produce incomplete artifacts.

## Clone And Prepare

To work from GitHub source directly:

```bash
git clone https://github.com/emergencyhamnet/meshcore-pi-port.git
cd meshcore-pi-port
```

To work from a source release archive instead:

```bash
tar -xzf meshcore-pi-port-v0.1.0-alpha1-source.tar.gz
cd meshcore-pi-port-v0.1.0-alpha1-source
```

Optional but useful for standalone validation:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
```

By default this writes:

```text
/tmp/meshcore-pi-telemetry.env
```

You can override that path with `MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH`.

## Build The Pi Runtime

```bash
scripts/build-pi-live-runtime.sh
```

What this produces:

1. native Pi runtime binary at `bin/pi-live-runtime` by default
2. object files under `.build/pi-live-runtime`
3. storage directories under `/var/lib/meshcore-pi-port` unless overridden

If you want the binary somewhere else, set:

```bash
export MESHCORE_PI_LIVE_RUNTIME_BIN=/custom/path/pi-live-runtime
```

Important defaults baked into the current Pi alpha build:

1. `MESHCORE_PI_LIVE_RADIO`
2. `SX126X_TXEN=22`
3. `SX126X_RXEN=27`
4. `SX126X_DIO2_AS_RF_SWITCH=true`
5. `SX126X_DIO3_TCXO_VOLTAGE=1.8`
6. `SX126X_CURRENT_LIMIT=140`
7. `LORA_TX_POWER=17`

## Install The Runtime Service

For published-app compatibility, use `app` mode:

```bash
sudo env MESHCORE_PI_INTERFACE_MODE=app bash scripts/install-pi-live-runtime-service.sh
sudo systemctl start meshcore-pi-live-runtime.service
sudo systemctl status meshcore-pi-live-runtime.service --no-pager
```

Recommended first-time environment overrides if you want to keep node state outside `/var/lib` while testing:

```bash
export MESHCORE_PI_STORAGE_ROOT=$HOME/meshcore-pi-port-state
export MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH=/tmp/meshcore-pi-telemetry.env
```

Then install with:

```bash
sudo --preserve-env=MESHCORE_PI_STORAGE_ROOT,MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH,MESHCORE_PI_INTERFACE_MODE \
	env MESHCORE_PI_INTERFACE_MODE=app bash scripts/install-pi-live-runtime-service.sh
```

Retire the old local management UI if it is still installed:

```bash
sudo bash scripts/retire-pi-management-ui.sh
```

Install the Pi-hosted browser UI:

```bash
sudo bash scripts/install-pi-browser-ui-service.sh
sudo systemctl start meshcore-pi-browser-ui.service
sudo systemctl status meshcore-pi-browser-ui.service --no-pager
```

Expected app-mode endpoints:

1. published MeshCore app bridge: `127.0.0.1:5040`
2. donor runtime internal transport: `127.0.0.1:5041`
3. final Pi-hosted browser UI: `http://<pi-host>:8099`
4. basestation gateway link: `tcp://<pi-host>:7463`

## Minimum Validation

After installation, validate in this order:

1. `systemctl status meshcore-pi-live-runtime.service --no-pager`
2. `journalctl -u meshcore-pi-live-runtime.service -n 50 --no-pager`
3. `python3 scripts/run-native-companion-smoke.py --host 127.0.0.1 --port 5040`
4. published MeshCore app connection through `127.0.0.1:5040`
5. self telemetry readback using the dummy snapshot or live telemetry provider

Optional extra checks:

```bash
cat "$MESHCORE_PI_STORAGE_ROOT/state/runtime-bridge.status"
python3 scripts/run-radio-smoke.sh
```

What success looks like:

1. the service stays running
2. `127.0.0.1:5040` accepts companion clients
3. the published app can complete `APP_START` and `DEVICE_QUERY`
4. self telemetry shows battery and static environment values if the dummy snapshot exists

## Build A Release Artifact

To generate a source release archive:

```bash
scripts/package-pi-alpha-release.sh v0.1.0-alpha1
```

Artifacts are written to `dist/` by default.

Generated outputs:

1. `meshcore-pi-port-v0.1.0-alpha1-source.tar.gz`
2. `meshcore-pi-port-v0.1.0-alpha1-pi-binary.tar.gz` if `bin/pi-live-runtime` already exists and is executable

Recommended release build sequence on the Pi host:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
scripts/build-pi-live-runtime.sh
scripts/package-pi-alpha-release.sh v0.1.0-alpha1
```

## Release Checklist

Before publishing a Pi alpha release:

1. verify the supported radio-family note is current in `docs/pi_hat_pinout.md`
2. build `bin/pi-live-runtime` on the Pi host
3. validate app-mode bridge behavior
4. validate self telemetry using the current snapshot path
5. tag the tested commit
6. push the branch and tag
7. create the GitHub release using the matching notes file in `docs/`
8. optionally attach the packaged source archive and Pi binary bundle

Suggested publish sequence:

```bash
git tag v0.1.0-alpha1
git push origin pi-port-main
git push origin v0.1.0-alpha1
```

Then use:

1. `docs/pi_alpha_release_v0.1.0-alpha1.md` for the GitHub release body
2. the files in `dist/` as optional release assets

## Troubleshooting

Common build blockers:

1. missing `RadioLib.h` at the configured include prefix
2. missing `/usr/include/lgpio.h`
3. runtime binary not executable when installing the service
4. wrong radio wiring for the currently supported `SX1262` plus `TXEN/RXEN` family

Start with:

1. `docs/pi_hat_pinout.md`
2. `docs/PI_NATIVE_BRINGUP.md`
3. `docs/pi_alpha_release.md`