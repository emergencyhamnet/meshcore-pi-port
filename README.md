# MeshCore Pi Port

Standalone Raspberry Pi HAT port of MeshCore, built to run a complete MeshCore node on a Pi with donor-faithful runtime behavior, companion-app compatibility, and Pi-native runtime integration.

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

<<<<<<< HEAD
This means the current port is built for a Pi HAT style radio design in the same family as the present E22-style `SX1262` implementation, not a generic “any LoRa board on a Pi” target.
=======
- Install [PlatformIO](https://docs.platformio.org) in [Visual Studio Code](https://code.visualstudio.com).
- Clone and open the MeshCore repository in Visual Studio Code.
- For the Raspberry Pi HAT port alpha, start with [docs/pi_alpha_release.md](./docs/pi_alpha_release.md) and [docs/PI_NATIVE_BRINGUP.md](./docs/PI_NATIVE_BRINGUP.md).
- For a step-by-step Pi install, build, validation, and release flow, use [docs/pi_install_build_release.md](./docs/pi_install_build_release.md).
- The current Raspberry Pi HAT port is validated against an `SX1262`-class radio path with explicit `TXEN/RXEN` control. See [docs/pi_hat_pinout.md](./docs/pi_hat_pinout.md) for the expected Pi wiring and radio-family assumptions.
- See the example applications you can modify and run:
  - [Companion Radio](./examples/companion_radio) - For use with an external chat app, over BLE, USB or Wi-Fi.
  - [KISS Modem](./examples/kiss_modem) - Serial KISS protocol bridge for host applications. ([protocol docs](./docs/kiss_modem_protocol.md))
  - [Simple Repeater](./examples/simple_repeater) - Extends network coverage by relaying messages.
  - [Simple Room Server](./examples/simple_room_server) - A simple BBS server for shared Posts.
  - [Simple Secure Chat](./examples/simple_secure_chat) - Secure terminal based text communication between devices.
  - [Simple Sensor](./examples/simple_sensor) - Remote sensor node with telemetry and alerting.
>>>>>>> fa80a140 (Improve Pi install, build, and release documentation)

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






