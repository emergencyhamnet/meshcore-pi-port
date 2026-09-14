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
sudo apt install -y build-essential git cmake python3 python3-pip libssl-dev pkg-config liblgpio-dev
```

`liblgpio-dev` is in the Raspberry Pi OS repositories (trixie and bookworm) and provides both `/usr/include/lgpio.h` and the runtime library. If your distribution lacks it, build `lg` from https://github.com/joan2937/lg.

Reference node that is known to build and run: Raspberry Pi OS trixie (32-bit), g++ 14.2, Python 3.13, `liblgpio-dev` 0.2.2, RadioLib 7.7.1.

## RadioLib Requirement

The build does not vendor `RadioLib`. It expects a system installation with headers under `/usr/local/include/RadioLib` and a static `libRadioLib.a` under `/usr/local/lib`.

Install the version proven with this port:

```bash
git clone --depth 1 --branch 7.7.1 https://github.com/jgromes/RadioLib.git /tmp/RadioLib
cmake -S /tmp/RadioLib -B /tmp/RadioLib/build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/RadioLib/build -j"$(nproc)"
sudo cmake --install /tmp/RadioLib/build
ls /usr/local/include/RadioLib/RadioLib.h /usr/local/lib/libRadioLib.a
```

Newer RadioLib releases will probably work but have not been validated against the Pi HAL in `platform/pi_radiolib_hal.cpp`; pin 7.7.1 for a first build.

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

To work from GitHub source directly, clone the verified alpha tag. Earlier alpha tags (`v0.2.0-alpha1`, `v0.2.0-alpha2`, `v0.1.0-alpha1`) do not build from a clean clone.

```bash
sudo git clone --branch v0.2.0-alpha3 https://github.com/emergencyhamnet/meshcore-pi-port.git /opt/meshcore-pi-port
sudo chown -R "$USER":"$USER" /opt/meshcore-pi-port
cd /opt/meshcore-pi-port
```

`/opt/meshcore-pi-port` is the default the service installers expect; using it means the generated unit files match this guide without overrides.

To work from a source release archive instead:

```bash
tar -xzf meshcore-pi-port-v0.2.0-alpha3-source.tar.gz
cd meshcore-pi-port-v0.2.0-alpha3-source
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

Install the Pi-hosted browser UI. If this node will serve an EHN basestation, allow basestation transmit on the embedded gateway link; the installer defaults it to off:

```bash
sudo env MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_ALLOW_TX=1 bash scripts/install-pi-browser-ui-service.sh
sudo systemctl start meshcore-pi-browser-ui.service
sudo systemctl status meshcore-pi-browser-ui.service --no-pager
```

The browser UI service also hosts the basestation gateway link on `0.0.0.0:7463` through the same native session, so the separate `meshcore-pi-gateway-link.service` is not needed in this layout.

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

## Fresh Node Bring-Up Checklist

Use this when standing up a brand-new node, for example a Raspberry Pi 4 with its own radio HAT, exactly as a new EHN participant would. Do not copy configuration or state from an existing node: the new node must mint its own identity and be provisioned through the normal path. Keep an existing node running untouched as a comparison reference.

Record every step where you had to deviate from this document; that list is the deliverable for improving the third-party install path.

### Before you start

1. Flash Raspberry Pi OS. 32-bit is the proven configuration; 64-bit is the intended future and should build but has not been validated yet. If you try 64-bit and hit anything architecture-specific, switch to 32-bit rather than debugging on the spot.
2. Enable SSH and SPI, join the network, note the IP address, and give the host a distinct hostname such as `ehn-node-2`.
3. Fit the HAT with power off, following `docs/pi_hat_pinout.md`. Confirm `/dev/spidev0.0` and `/dev/gpiochip0` exist after boot.

### Build and install

1. Install the build dependencies and `RadioLib` as described above.
2. Clone `v0.2.0-alpha3` into `/opt/meshcore-pi-port`.
3. Run `scripts/build-pi-live-runtime.sh`. Expect roughly 2 to 5 minutes and zero `error` lines. On a Pi 3B+ this took 2m14s.
4. Install the runtime service in `app` mode, then the browser UI service with `MESHCORE_PI_BROWSER_UI_GATEWAY_LINK_ALLOW_TX=1`.
5. Do not run any radio smoke test while another node with the same identity is on the air; a fresh node has a fresh identity, so this is only a concern if state was copied.

### Validate the node on its own

1. `cat /var/lib/meshcore-pi-port/state/runtime-bridge.status` shows `live_runtime_ready=1`.
2. `python3 scripts/run-native-companion-smoke.py --host 127.0.0.1 --port 5040` succeeds.
3. `http://<new-pi>:8099/` loads; Settings shows the new node name and public key; device time is current.
4. `python3 scripts/run-gateway-link-smoke.py --host 127.0.0.1 --port 7463 --timeout 10` succeeds.
5. From the browser UI, set the node name, then confirm an existing node sees the new node's advert and the new node sees the existing node.

### Provision it as an EHN gateway

1. In the browser UI, join the EHN private channel by pasting the `meshcore://channel/add` invite exported from an existing gateway, or create a new channel if this is the first gateway for a region.
2. Send a direct message between the new node and an existing node to prove RF both ways.
3. On the basestation host, add a station profile that points `BASESTATION_MESHCORE_LINK_ENDPOINT` at `<new-pi>:7463` and gives the gateway its own id, for example `EHN-XXX-2`. Do not edit the profile that points at the existing node.
4. Register the new node's public key against a user in the authority console, then send `@<that-user> test` from the phone and confirm delivery on the new node.

### Two gateways, two basestations

Running the original node behind the original basestation profile and the new node behind a second profile gives two complete EHN stations on one mesh. That is the intended setup for testing station-to-station behavior later; today it validates that a second station can be built from the documentation alone.

## Build A Release Artifact

To generate a source release archive:

```bash
scripts/package-pi-alpha-release.sh v0.2.0-alpha3
```

Artifacts are written to `dist/` by default.

Generated outputs:

1. `meshcore-pi-port-v0.2.0-alpha3-source.tar.gz`
2. `meshcore-pi-port-v0.2.0-alpha3-pi-binary.tar.gz` if `bin/pi-live-runtime` already exists and is executable

Recommended release build sequence on the Pi host:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
scripts/build-pi-live-runtime.sh
scripts/package-pi-alpha-release.sh v0.2.0-alpha3
```

## Release Checklist

Before publishing a Pi alpha release:

1. verify the supported radio-family note is current in `docs/pi_hat_pinout.md`
2. build `bin/pi-live-runtime` on the Pi host **from a fresh clone of the commit you intend to tag**; an incremental build in a long-lived working tree can succeed while the committed tree does not
3. validate app-mode bridge behavior
4. validate self telemetry using the current snapshot path
5. tag the tested commit
6. push the branch and tag
7. create the GitHub release using the matching notes file in `docs/`
8. optionally attach the packaged source archive and Pi binary bundle

Suggested publish sequence:

```bash
git tag v0.2.0-alpha3
git push origin pi-port-main
git push origin v0.2.0-alpha3
```

Then use:

1. the matching `docs/pi_alpha_release_*.md` notes file for the GitHub release body
2. the files in `dist/` as optional release assets

## Troubleshooting

Common build blockers:

1. missing `RadioLib.h` at the configured include prefix
2. missing `/usr/include/lgpio.h`
3. runtime binary not executable when installing the service
4. wrong radio wiring for the currently supported `SX1262` plus `TXEN/RXEN` family
5. `delay was not declared` or `FILESYSTEM does not name a type`: the tree is missing the Pi patches to `Arduino.h`, `target.h`, `src/helpers/IdentityStore.h`, or `src/helpers/radiolib/`; check out `v0.2.0-alpha3` or later rather than an older tag

If a long-lived working tree builds but a fresh clone does not, compare them with `scripts/pi-drift-report.sh` and `scripts/pi-reconcile-bundle.sh`, which ignore line-ending noise and list real content differences.

Start with:

1. `docs/pi_hat_pinout.md`
2. `docs/PI_NATIVE_BRINGUP.md`
3. `docs/pi_alpha_release.md`