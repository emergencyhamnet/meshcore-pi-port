# MeshCore Raspberry Pi HAT Hardware And Software Interface

**Status:** consolidated design reference, 2026-10-30. Connector assignments J1-J8 are based
on operator confirmation and the HAT Issue 1.0 design. They are not a substitute for checking
the fitted PCB revision, connector pin-1 marks, component values, or electrical behavior before
connecting hardware. The Pi-port code-level radio mapping is `platform/pi_board.h` and
`platform/pi_board.cpp`.

## Scope And Evidence

This specification covers the Raspberry Pi 3B/Pi 4 HAT designed around the Ebyte
E22-900M33S SX1262 radio, onboard sensors/ADC, switched outputs, watchdog connector, and J8
expansion header. It consolidates:

- operator-confirmed connector assignments dated 2026-10-30
- the original `MeshCore-Node/MeshCore_Pi_HAT_Hardware_Spec_Issue_1_0.rtf` and `pinmap.csv`
- the current Pi-port radio implementation in `platform/pi_board.h/.cpp`
- later operator confirmation of the J3 VBAT divider, which supersedes Issue 1.0

Where those sources conflict, the discrepancy is called out rather than silently merged.
Connector orientation must be established from the board silkscreen/keying before making a
cable. This document does not establish that every value or optional component is fitted on
every board revision.

## System Summary

- Radio: E22-900M33S, SX1262-class, SPI0, external TXEN/RXEN RF path control.
- Input power: J4 dual 5 V and dual ground pins. The HAT design distributes protected 5 V to
  the Pi, radio and fan branches; verify the installed board's power-path population and source
  current rating before powering the Pi through the HAT.
- Sensors: SHT40 temperature/RH, LPS22HH pressure/sensor temperature, ADS1015 voltage ADC.
- Sensor bus: Pi I2C1, 3.3 V logic. Sampler is optional and separate from the radio runtime.
- GPIO: radio controls are implemented; fan, auxiliary output and watchdog control are not
  enabled by the current Pi-port runtime.
- HAT EEPROM: not fitted per Issue 1.0.

## Connector Pinout

Pin numbers are physical connector pin numbers. Pi GPIO names use BCM numbering.

### J1 - Radio Reset

| J1 pin | Signal | Connection |
|---|---|---|
| 1 | GND | Common ground. |
| 2 | Radio reset | E22 NRST/RST net and Pi BCM17, physical header pin 11. Active-low radio reset. |

The E22 module reset is the radio reset signal, not the Pi reset input. The original Issue 1.0
spec identifies the E22 signal as NRST (module pin 15); confirm the fitted module/footprint
revision before wiring an external reset lead.

### J2 - Fan Output

| J2 pin | Signal | Connection |
|---|---|---|
| 1 | +5 V fan supply | Fused/switched-board 5 V fan branch per schematic. |
| 2 | Switched return | Low-side MOSFET drain; fan negative is switched to ground. |

The MOSFET gate is driven from BCM12, physical header pin 32 (PWM-capable). This is a
low-side switched supply, not a confirmed standard four-wire fan PWM interface. Fan startup
duty, frequency, current limit, tach feedback and fail-safe behavior are not established.
Issue 1.0 says fan tach is unused; the older `pinmap.csv` labels BCM4/physical pin 7 as
optional tach. Treat BCM4 as unused unless the fitted board is verified.

### J3 - UPS/Power Voltage Monitor Inputs

J3 is operator-described as the UPS control connector. Its four analog signals are voltage
monitor inputs; they are not digital control outputs. Pin 1 is ground. ADC mappings and
nominal divider ratios:

| J3 pin | Signal | ADS1015 input | Divider: source-to-ADC / ADC-to-GND | Nominal source multiplier |
|---|---|---|---|---|
| 1 | GND | - | - | - |
| 2 | VBAT | AIN3 | 250 kOhm / 100 kOhm | 3.5 |
| 3 | AUX | AIN2 | 100 kOhm / 100 kOhm | 2.0 |
| 4 | VOUT | AIN1 | 100 kOhm / 100 kOhm | 2.0 |
| 5 | VIN | AIN0 | 100 kOhm / 100 kOhm | 2.0 |

The 250 kOhm/100 kOhm VBAT divider and 3.5 multiplier are the operator-confirmed correction
to the Issue 1.0 document's 100 kOhm/249 kOhm arrangement and approximately 1.402 multiplier.
Do not use the older value for the confirmed board configuration.

These are nominal scale factors, not calibration. The ADS1015 is powered at 3.3 V. Its
programmable +/-4.096 V conversion range does not allow an analog pin above its supply/absolute
input limits. Confirm resistor population/tolerance, source range, ADC input safety and meter
calibration before relying on readings or setting alarms. Voltage alone is not state of charge;
there is no current sensor.

### J4 - 5 V Power Input

| J4 pin | Signal |
|---|---|
| 1 | +5 V input |
| 2 | +5 V input |
| 3 | GND |
| 4 | GND |

The two positive pins are the 5 V feed and the two ground pins are common return. Issue 1.0
describes protected 5V_PI, 5V_E22 and 5V_FAN branches; an E22 eFuse current limit of about 2 A
is a design value, not verified here for every fitted board. Size the upstream supply for the
Pi, radio transmit load and any fan/accessories. Verify the HAT power path before also
connecting another 5 V Pi supply; do not assume dual-feed isolation.

### J5 - Pi Reset/Watchdog Output

| J5 pin | Signal | Connection |
|---|---|---|
| 1 | GND | Common ground. |
| 2 | TPS3431 WDO | Open-drain watchdog output intended for the Pi RUN/GLOBAL_EN reset path. |

The TPS3431 WDI input is BCM6, physical header pin 31. Issue 1.0 specifies a 1 uF CWD for an
approximately 77 s timeout and recommends a 10-20 s heartbeat; confirm fitted timing parts
and Pi model/reset wiring before using this. J5 is the reset connector, but an earlier live-site
inspection reported it was physically unwired. Therefore do not assume the reference on-air
Pi currently has watchdog reset capability, and do not enable a heartbeat or connect J5 without
an operator/electrical review. No Pi-port watchdog control is implemented.

### J6 - Not Fitted

J6 is not fitted in the confirmed configuration. Do not assign software or wiring to it without
a board revision that defines the connector.

### J7 - Auxiliary Switched Output

Issue 1.0 describes J7 as a switched 5 V output:

| J7 pin | Signal |
|---|---|
| 1 | +5 V auxiliary supply |
| 2 | Switched output / low-side MOSFET drain |

The operator-confirmed MOSFET gate control is BCM5, physical header pin 29. An older `pinmap.csv`
lists BCM5 as unused; the operator-confirmed circuit assignment supersedes that CSV entry.
Current Pi-port software does not drive this output. Verify the installed circuit, maximum load,
polarity and inductive-load protection before use; no current limit or supported accessory is
certified by this specification.

### J8 - External 3.3 V/I2C/GPIO Bus

| J8 pin | Signal | Raspberry Pi connection |
|---|---|---|
| 1 | VDD 3.3 V | HAT 3.3 V logic rail. |
| 2 | GND | Common ground. |
| 3 | SDA | I2C1 SDA, BCM2, physical pin 3. |
| 4 | SCL | I2C1 SCL, BCM3, physical pin 5. |
| 5 | GPIO13 | BCM13, physical pin 33. |
| 6 | GPIO26 | BCM26, physical pin 37. |

J8 is a 3.3 V logic interface, not 5 V tolerant. GPIO13 and GPIO26 have no assigned HAT
function in the current Pi-port software. The I2C lines share the onboard I2C1 bus and pullups;
account for added module pullups and address conflicts when attaching devices.

## Pi Header And Radio Signal Map

The current code uses BCM numbering. Key physical-header map:

| Function | BCM GPIO | Physical pin |
|---|---:|---:|
| Radio reset / J1 pin 2 | 17 | 11 |
| Radio RXEN | 27 | 13 |
| Radio TXEN | 22 | 15 |
| Radio BUSY | 24 | 18 |
| SPI0 MOSI | 10 | 19 |
| SPI0 MISO | 9 | 21 |
| Radio DIO1 | 25 | 22 |
| SPI0 SCLK | 11 | 23 |
| SPI0 CE0/NSS | 8 | 24 |
| I2C1 SDA | 2 | 3 |
| I2C1 SCL | 3 | 5 |
| Fan gate | 12 | 32 |
| Watchdog WDI | 6 | 31 |
| Auxiliary gate | 5 | 29 |
| J8 GPIO | 13 | 33 |
| J8 GPIO | 26 | 37 |

The Pi-port's `platform/pi_board.h` currently configures SPI bus 0 at 8 MHz, mode 0,
8 bits/word. The RF path helper sets standby to TXEN=0/RXEN=0, receive to TXEN=0/RXEN=1,
and transmit to TXEN=1/RXEN=0. NRST is held high when idle and pulsed low/high for reset.
These are software configuration defaults; verify signal polarity and fitted board revision
before connecting a replacement radio.

## Onboard I2C Devices And Software

| Device | I2C address | Software-visible values |
|---|---:|---|
| SHT40-AD1B-R2 | `0x44` | Temperature and relative humidity; CRC must pass. |
| LPS22HHTR | `0x5C` | Pressure and sensor temperature; SA0/SDO tied low for this address. |
| ADS1015IDGSR | `0x48` | AIN0 VIN, AIN1 VOUT, AIN2 AUX, AIN3 VBAT; ADDR tied low. |

The sampler requires Pi I2C enabled (`/dev/i2c-1`) and OS-provided `python3-smbus2`. It reads
the sensors independently from the radio runtime, restores pressure-sensor/ADC configuration,
and atomically writes a fresh timestamped env snapshot. The service and install procedure are
in [Standalone Pi HAT Sensor Telemetry](pi-port/telemetry.md). It is optional and does not
change MeshCore native telemetry permissions.

For radio build and service setup, see [Pi install/build/release](pi_install_build_release.md)
and [staged native bring-up](PI_NATIVE_BRINGUP.md). Enable SPI, confirm `/dev/spidev0.0` and
`/dev/gpiochip0`, use the documented RadioLib and `lgpio` dependencies, and validate radio
initialization before any controlled RF test.

## Electrical And Validation Cautions

- Turn off power before fitting/removing the HAT or wiring J1-J8.
- Confirm connector pin 1 from silkscreen/keying, not cable orientation alone.
- Logic is 3.3 V; never apply 5 V to Pi GPIO, I2C, ADC inputs or J8 GPIO pins.
- Treat divider values as nominal until measured against a meter on the fitted PCB revision.
- J2/J7 are low-side switched outputs, not generic logic outputs; current, startup and load
  limits require board/fan/accessory review.
- Do not drive the TPS3431 WDI, J2 or J7 with the current Pi-port runtime. J5's watchdog reset
  wire and J6 population must be confirmed on each installation.
- The HAT design/spec is not proof of a particular live board's fitted options, calibration,
  thermal environment, RF legality or successful radio communication.