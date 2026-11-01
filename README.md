# MeshCore Pi Port

Standalone Raspberry Pi HAT port of MeshCore, built to run a complete MeshCore node on a Pi with donor-faithful runtime behavior, companion-app compatibility, and Pi-native runtime integration.

## Quick Start

For the operating-mode overview and current documentation map, start with
[Current Pi-Port Documentation](./docs/current/README.md). The port serves two related use cases:
standalone MeshCore operation with companion-app compatibility, and use as an EHN basestation
gateway. The Pi-hosted browser UI is documented as a shared operator surface.

For supported hardware, build/install instructions and the alpha scope, use the
[current documentation index](./docs/current/README.md). Check each document's status before
treating candidate or draft instructions as a released installation recipe.

## Status

This repository currently represents an early standalone alpha of the Pi port.

Use [v0.2.0-alpha5](./docs/current/pi_alpha_release_v0.2.0-alpha5.md) for the E22 GPIO,
power-control and settings-save corrections. Existing installations must rebuild and restart;
the older alpha4 tag does not contain these fixes.

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

1. [Current Pi HAT hardware and connector specification](./docs/current/pi_hat_hardware_spec.md)
2. [Radio pinout summary](./docs/current/pi_hat_pinout.md)

## What This Port Provides

This port is intended to form a complete MeshCore node built on a Raspberry Pi.

Included surfaces:

1. donor-aligned MeshCore node runtime
2. Pi-native runtime bootstrap
3. Pi-native transport, storage, GPIO, SPI, and RadioLib HAL integration
4. app-mode companion bridge on `127.0.0.1:5040`
5. optional local browser UI for status and logs
6. static telemetry snapshot support for standalone testing
7. optional standalone HAT sensor sampler, installed separately and disabled by default

## Interface Model

The primary supported device contract is the donor MeshCore companion protocol.

Default operating mode:

1. `MESHCORE_PI_INTERFACE_MODE=app`

Expected app-mode endpoints:

1. published MeshCore app endpoint: `127.0.0.1:5040`
2. internal runtime transport: `127.0.0.1:5041`
3. final Pi-hosted browser UI: `http://<pi-host>:8099`
4. basestation gateway link: `tcp://<pi-host>:7463`

This keeps the runtime-owned native companion path, the Pi-hosted browser UI, and the basestation gateway link as separate surfaces with separate roles.

For more detail, see:

1. [Pi-port UI guide](./docs/current/pi-port/pi-ui.md)
2. [Alpha scope](./docs/current/pi_alpha_release.md)

## Relationship To The EHN Basestation

This repository is the MeshCore gateway for the Emergency Ham Network. It owns the radio, the
native companion protocol, the Pi-hosted node UI, and the basestation-facing gateway link on
`7463`. It does not own identity, routing policy, or message storage; those live in the separate
`ehn-basestation` repository, which connects to this node over the gateway link. Architecture
and specifications are in `ehn-docs`.

## Telemetry

The Pi runtime can expose battery and environmental telemetry from a timestamped key-value
snapshot. For the optional standalone I2C sampler, disabled-by-default service and native
permission boundary, see [Standalone Pi HAT Sensor Telemetry](./docs/current/pi-port/telemetry.md).

Primary environment variables:

1. `MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH`
2. `MESHCORE_PI_TELEMETRY_SNAPSHOT_MAX_AGE_SECONDS`

A dummy telemetry snapshot can be generated with:

```bash
python3 scripts/write-dummy-telemetry-snapshot.py
```

## Build And Install

For a practical install, build, validation, and release flow, use:

1. [Current Pi-port install/build guide](./docs/current/pi_install_build_release.md)

For alpha scope and release-contract notes, see:

1. [Current alpha scope and release contract](./docs/current/pi_alpha_release.md)

For detailed bring-up and radio validation guidance, see:

1. [Archived native bring-up notes](./docs/archive/PI_NATIVE_BRINGUP.md), for history only

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



