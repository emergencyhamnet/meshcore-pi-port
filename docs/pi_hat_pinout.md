# Pi HAT Radio Pinout

This document records the current Raspberry Pi HAT radio wiring expected by the Pi-native MeshCore port.

## Current Target Radio Family

The current Pi port is built around an `SX1262`-class LoRa radio path with explicit external RF path control.

Important characteristics of the currently supported family:

1. `SX1262`-compatible RadioLib path
2. explicit `TXEN` and `RXEN` GPIO control on the Pi side
3. separate `BUSY`, `RESET`, `DIO1`, and `NSS` lines
4. `SPI0` transport between the Pi and radio module

This matters because the current live build and bring-up flow assume a radio module family that behaves like the present E22-style `SX1262` path, not an arbitrary LoRa board.

## Expected Pi Wiring

Current expected mapping:

1. `NSS = GPIO8`
2. `DIO1 = GPIO25`
3. `RESET = GPIO17`
4. `BUSY = GPIO24`
5. `TXEN = GPIO22`
6. `RXEN = GPIO27`
7. `SPI = SPI0`

## Source Of Truth

The human-readable bring-up reference is:

1. `docs/PI_NATIVE_BRINGUP.md`

The code-level source of truth is:

1. `platform/pi_board.h`
2. `platform/pi_board.cpp`

The current hard-coded pin values in `platform/pi_board.h` are:

1. `nss = 8`
2. `dio1 = 25`
3. `reset = 17`
4. `busy = 24`
5. `txen = 22`
6. `rxen = 27`
7. `spi_bus = 0`

## RF Path Notes

The Pi port currently expects explicit RF path switching:

1. transmit mode drives `TXEN` high and `RXEN` low
2. receive mode drives `TXEN` low and `RXEN` high
3. standby drives both low

That behavior is implemented in `platform/pi_board.cpp`.

## Public Compatibility Note

For this alpha, users should assume the Pi port is validated against this specific `SX1262` plus explicit-`TXEN/RXEN` radio family. Other Pi-attached LoRa radios may require board-profile and bring-up changes before they behave correctly.