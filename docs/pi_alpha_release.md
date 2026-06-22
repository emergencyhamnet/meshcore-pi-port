# Pi Alpha Release

This document defines the smallest standalone alpha release for the Raspberry Pi HAT port.

## Scope

The alpha release should include only the Pi port source tree and the surfaces needed to make the published MeshCore app work.

Included in scope:

1. Pi live runtime build and runtime scripts
2. companion bridge in `app` mode on `127.0.0.1:5040`
3. Pi storage layout and persisted donor state
4. optional local browser UI for status and logs
5. dummy telemetry snapshot support

Explicitly out of scope:

1. basestation repository integration
2. real sensor ownership
3. browser-helper send and receive workflows as the primary interface
4. packaging the Pi as a full appliance image

## Release Contract

The alpha should present the Pi port as donor-companion-first.

Default behavior:

1. `MESHCORE_PI_INTERFACE_MODE=app`
2. published MeshCore app is the main interactive control surface
3. telemetry may come from a static snapshot file

## App-Mode Quickstart

On the Pi host:

```bash
cd /path/to/meshcore-pi-port
python3 scripts/write-dummy-telemetry-snapshot.py
scripts/build-pi-live-runtime.sh
sudo env MESHCORE_PI_INTERFACE_MODE=app bash scripts/install-pi-live-runtime-service.sh
sudo systemctl start meshcore-pi-live-runtime.service
sudo systemctl status meshcore-pi-live-runtime.service --no-pager
```

Optional local status UI:

```bash
sudo env MESHCORE_PI_INTERFACE_MODE=app bash scripts/install-pi-node-ui-service.sh
sudo systemctl start meshcore-pi-node-ui.service
```

Expected alpha endpoints:

1. published MeshCore app path: `127.0.0.1:5040`
2. donor runtime internal transport: `127.0.0.1:5041`
3. optional Pi node UI: `http://<pi-host>:8088`

## Telemetry Snapshot Contract

The runtime reads a simple key-value snapshot file for local battery and environmental telemetry.

Primary environment variables:

1. `MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH`
2. `MESHCORE_PI_TELEMETRY_SNAPSHOT_MAX_AGE_SECONDS`

Legacy compatibility aliases still accepted for now:

1. `MESHCORE_PI_BASESTATION_SNAPSHOT_PATH`
2. `MESHCORE_PI_BASESTATION_SNAPSHOT_MAX_AGE_SECONDS`

Default snapshot path:

```text
/tmp/meshcore-pi-telemetry.env
```

Required keys for a useful dummy file:

1. `vbat_v`
2. `temperature_c`
3. `humidity_pct`
4. `pressure_hpa`
5. `timestamp_unix`

To create a dummy snapshot for alpha testing:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
```

## Minimum Source Release Contents

Release these source surfaces together:

1. `main/`
2. `platform/`
3. `src/`
4. `examples/companion_radio/`
5. `scripts/`
6. `deploy/systemd/`
7. `ui/`
8. `docs/PI_NATIVE_BRINGUP.md`
9. `docs/pi_node_interface.md`
10. `docs/pi_alpha_release.md`

## Minimum Validation Before Tagging

1. build the runtime with `scripts/build-pi-live-runtime.sh`
2. generate a dummy telemetry file with `scripts/write-dummy-telemetry-snapshot.py`
3. start the runtime service in `app` mode
4. validate `APP_START`, `DEVICE_QUERY`, and `GET_CONTACTS`
5. confirm the published app connects through `127.0.0.1:5040`
6. confirm self telemetry returns at least battery and static environment values

## Binary Release Guidance

Source release is the primary artifact for the alpha. A Pi binary is appropriate only as a convenience artifact after the exact build input is documented.

If a binary is attached to the release:

1. build it on the same Pi OS family you intend to support first
2. publish the exact commit, build script, and build date used
3. package `bin/pi-live-runtime` with the service and launcher scripts that expect it
4. keep the source release authoritative if the binary and source ever diverge

For the current phase, a prebuilt `pi-live-runtime` tarball is reasonable as an optional release asset, but it should not replace the source-first install path.

To generate release archives from the repo itself:

```bash
scripts/package-pi-alpha-release.sh v0.1.0-alpha1
```

If `bin/pi-live-runtime` already exists on the Pi host, the same script also emits a binary bundle alongside the source archive.