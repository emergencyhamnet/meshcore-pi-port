# MeshCore Pi Port

Standalone Raspberry Pi HAT port of MeshCore, built to run a complete MeshCore node on a Pi with donor-faithful runtime behavior, companion-app compatibility, and Pi-native runtime integration.

## Quick Start

If you want to build and run the current Pi alpha on supported hardware, start here:

1. `docs/pi_hat_pinout.md` for supported radio-family and wiring assumptions
2. `docs/pi_install_build_release.md` for prerequisites, build, install, validation, and release packaging
3. `docs/pi_alpha_release.md` for alpha scope and release contract

## Status

This repository currently represents an early standalone alpha of the Pi port.

Current goals:

1. run a real MeshCore node on a Raspberry Pi
2. preserve donor MeshCore companion behavior
3. support the published MeshCore app through a stable Pi-local companion bridge
4. provide a source-first release path for Pi-native builds and testing

This is not yet intended to claim broad compatibility across arbitrary Pi-attached LoRa radios.

## Current Hardware Scope

The current Pi port is validated against a specific radio family and wiring model.

Supported path today:

1. `SX1262`-class LoRa radio path
2. explicit `TXEN` and `RXEN` RF path control
3. separate `BUSY`, `RESET`, `DIO1`, and `NSS` lines
4. `SPI0` connection to the Raspberry Pi

This means the current port is built for a Pi HAT style radio design in the same family as the present E22-style `SX1262` implementation, not a generic "any LoRa board on a Pi" target.

See:

1. [docs/pi_hat_pinout.md](./docs/pi_hat_pinout.md)
2. [docs/PI_NATIVE_BRINGUP.md](./docs/PI_NATIVE_BRINGUP.md)

## What This Port Provides

This port is intended to form a complete MeshCore node built on a Raspberry Pi.

Included surfaces:

1. donor-aligned MeshCore node runtime
2. Pi-native runtime bootstrap
3. Pi-native transport, storage, GPIO, SPI, and RadioLib HAL integration
4. app-mode companion bridge on `127.0.0.1:5040`
5. optional local browser UI for status and logs
6. static telemetry snapshot support for standalone testing

## Interface Model

The primary supported device contract is the donor MeshCore companion protocol.

Default operating mode:

1. `MESHCORE_PI_INTERFACE_MODE=app`

Expected app-mode endpoints:

1. published MeshCore app endpoint: `127.0.0.1:5040`
2. internal runtime transport: `127.0.0.1:5041`
3. optional Pi node UI: `http://<pi-host>:8088`

This keeps the published MeshCore client as the main interactive control surface while the Pi hosts the runtime locally.

For more detail, see:

1. [docs/pi_node_interface.md](./docs/pi_node_interface.md)
2. [docs/pi_alpha_release.md](./docs/pi_alpha_release.md)

## Telemetry

The Pi runtime can expose battery and environmental telemetry from a simple key-value snapshot file.

Primary environment variables:

1. `MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH`
2. `MESHCORE_PI_TELEMETRY_SNAPSHOT_MAX_AGE_SECONDS`

A dummy telemetry snapshot can be generated with:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
```

## Build And Install

For a practical install, build, validation, and release flow, use:

1. [docs/pi_install_build_release.md](./docs/pi_install_build_release.md)

For alpha scope and release-contract notes, see:

1. [docs/pi_alpha_release.md](./docs/pi_alpha_release.md)

For detailed bring-up and radio validation guidance, see:

1. [docs/PI_NATIVE_BRINGUP.md](./docs/PI_NATIVE_BRINGUP.md)

## Current Limitations

This alpha does not yet claim:

1. generic support for arbitrary Pi-attached LoRa radios
2. full basestation integration as part of the release contract
3. appliance-style Pi image packaging
4. broad hardware abstraction across all SX126x variants

The supported path today is the specific Pi HAT radio family documented in this repo.

## Upstream Relationship

This port is built on donor-faithful MeshCore behavior rather than a clean-room reimplementation.

The Pi-specific work focuses on the Linux host boundary:

1. runtime bootstrap
2. storage
3. transport
4. GPIO
5. SPI
6. RadioLib HAL integration

Core MeshCore routing, datastore, and companion behavior continue to come from the upstream MeshCore codebase.

## License

MeshCore is open-source software released under the MIT License. See the repository license files for details.



