# v0.1.0-alpha1

## Overview

`v0.1.0-alpha1` is the first standalone alpha release of the Raspberry Pi HAT MeshCore port.

This release publishes the Pi port as its own source release, separate from the basestation repository. The main goal of this alpha is to make the published MeshCore app work against the Pi runtime through the donor companion interface while keeping the release surface small and explicit.

## Scope

Included in this alpha:

1. Pi-native live runtime build and launch path
2. app-mode companion bridge on `127.0.0.1:5040`
3. donor-aligned runtime, storage, and companion behavior
4. optional local browser UI for status and logs
5. dummy telemetry snapshot support
6. source-first release packaging for the Pi port repo

Out of scope for this alpha:

1. basestation integration
2. real sensor ownership
3. full appliance or image packaging
4. broader helper-driven browser workflows as the primary interface

## Highlights

1. Added a standalone Pi alpha release guide
2. Added a dummy telemetry snapshot writer for app-mode testing
3. Neutralized telemetry snapshot naming so the Pi port no longer implies a basestation dependency
4. Added packaging support for a source archive and optional Pi binary bundle
5. Documented the intentional `17 dBm` Pi HAT TX power ceiling used for this hardware path

## Runtime Model

This port remains donor-first.

The Pi runtime hosts donor `MyMesh`, donor `DataStore`, donor packet and routing behavior, and donor companion protocol behavior. Pi-specific work is focused on the Linux host boundary:

1. runtime bootstrap
2. transport
3. storage
4. GPIO
5. SPI
6. RadioLib HAL integration

## App-Mode Contract

Default alpha mode:

1. `MESHCORE_PI_INTERFACE_MODE=app`

Expected endpoints:

1. published MeshCore app path: `127.0.0.1:5040`
2. donor runtime internal transport: `127.0.0.1:5041`
3. optional Pi node UI: `http://<pi-host>:8088`

## Telemetry

This alpha supports a simple key-value telemetry snapshot file for battery and environmental values.

Primary environment variables:

1. `MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH`
2. `MESHCORE_PI_TELEMETRY_SNAPSHOT_MAX_AGE_SECONDS`

Legacy compatibility aliases still accepted for now:

1. `MESHCORE_PI_BASESTATION_SNAPSHOT_PATH`
2. `MESHCORE_PI_BASESTATION_SNAPSHOT_MAX_AGE_SECONDS`

A dummy snapshot can be generated with:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
```

## Packaging

Source is the authoritative release artifact for this alpha.

The repo also includes packaging support for:

1. source archive generation
2. optional prebuilt Pi runtime bundle when `bin/pi-live-runtime` is already built on the Pi host

Packaging helper:

```bash
scripts/package-pi-alpha-release.sh v0.1.0-alpha1
```

## Notes

This is an alpha release. Its main purpose is to establish a clean, public, standalone Pi port release surface and a repeatable app-mode validation path.

Recommended validation path:

1. build the runtime on the Pi
2. generate a dummy telemetry snapshot
3. install and run the app-mode runtime service
4. validate published-app connection and companion behavior