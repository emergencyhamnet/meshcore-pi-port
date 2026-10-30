# Standalone Pi HAT Sensor Telemetry

**Status:** optional sampler/service draft, 2026-10-29. Sensor sampling is separate from the
MeshCore runtime; no telemetry permission or radio transmission is enabled by installing the
sampler.

## Data Path

```text
HAT I2C1 sensors -> meshcore-pi-hat-sensors.service
                 -> /tmp/meshcore-pi-telemetry.env
                 -> Pi runtime's native MeshCore telemetry response
                 -> requesting MeshCore client
```

This works in standalone-node mode and does not require `ehn-basestation`. The Pi-port runtime
does not poll I2C itself. Its existing native reader consumes a timestamped key/value file when
it prepares a telemetry response. The sampler owns sensor I2C reads; the Pi runtime remains the
only radio/SPI owner. Do not run a second sampler against the same HAT while this service is
active.

## Measurements And Limits

The sampler reads SHT40, LPS22HH and ADS1015 on I2C1. It exports only valid values supported by
the current Pi runtime reader:

| Field | Sensor | Native use |
|---|---|---|
| `temperature_c` | SHT40 | Environment telemetry response. |
| `humidity_pct` | SHT40 | Environment telemetry response. |
| `pressure_hpa` | LPS22HH | Environment telemetry response. |
| `vbat_v` | ADS1015 AIN3 | Pi board battery-voltage hook; not a state-of-charge estimate. |

VIN, VOUT, AUX and the pressure sensor's second temperature remain in the canonical basestation
snapshot only; the current Pi-port native reader does not map them. Voltage scale factors are
nominal and must be calibrated for the fitted board. The pressure sensor temperature may be
enclosure-heated rather than outdoor ambient.

The runtime rejects a snapshot older than its configured maximum age (60 seconds by default).
If the file is absent, stale, or VBAT is missing, the current battery callback returns `0`;
do not enable base/battery permission until this behavior is fixed or independently confirmed
to mean unavailable to every consuming client. Never advertise that zero means a measured
empty battery.

## Install Without Enabling

Install `python3-smbus2` from the OS package manager, then install the unit without starting or
enabling it:

```bash
sudo apt update
sudo apt install -y python3-smbus2
sudo bash scripts/install-pi-hat-sensors-service.sh
```

The installer creates a system account `meshcore-pi-sensors`, adds only I2C device access,
installs the unit and leaves it disabled. It does not change the MeshCore runtime or browser UI
service, telemetry preferences, radio configuration, or permissions. Inspect the generated
unit and ensure the I2C bus belongs to group `i2c` before enabling.

After wiring, calibration and snapshot-path review, an operator may explicitly enable it:

```bash
sudo systemctl enable --now meshcore-pi-hat-sensors.service
systemctl status meshcore-pi-hat-sensors.service --no-pager
sudo journalctl -u meshcore-pi-hat-sensors.service -n 50 --no-pager
```

Use the optional `--enable` installer argument only when intentionally installing and enabling
in one step. The service samples every ten seconds by default and atomically writes
`/tmp/meshcore-pi-telemetry.env` with mode `0600`. Override its path/interval in the installed
unit only after matching `MESHCORE_PI_TELEMETRY_SNAPSHOT_PATH` and maximum-age settings on the
Pi runtime. The file is local operational data, not a radio message or a secret distribution
mechanism.

## Native Telemetry Permission

The browser UI reports native `base`, `location` and `environment` telemetry modes. These are
MeshCore node settings, independent from sampler service state:

- `environment` permission gates temperature, humidity and pressure replies.
- `base` permission includes battery voltage and other base telemetry.
- `location` permission is separate and is not required for these HAT readings.

Keep permissions at their existing value until the operator explicitly chooses which contacts
or remote requesters may receive the readings. Installing or starting the sampler never
changes these settings. This path is request/reply native telemetry, not a periodic broadcast.
Only a controlled client request after permission review should be used for RF acceptance.

## Validation And Rollback

Before enabling, verify the expected I2C addresses and compare voltage readings with a meter.
Then validate the local env-file timestamps and valid-field omission. After explicit service
enablement, confirm the Pi UI still reports native permission values. Do not claim RF delivery
until a permitted request is made and a receiving client confirms the data.

Stop and disable the sampler with:

```bash
sudo systemctl disable --now meshcore-pi-hat-sensors.service
```

This does not alter node identity, radio settings, telemetry permissions or the MeshCore runtime.