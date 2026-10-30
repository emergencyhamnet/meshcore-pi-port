# Handover: Testing The Alpha Standalone MeshCore Pi HAT Port

**Status:** handover document, 2026-10-30. Written from the local `pi-port-main` working tree.
**Audience:** the next engineer/session taking over validation of the standalone Pi HAT port.
**Next project:** take the unpublished **v0.2.0-alpha4 test candidate** through standalone
testing on real Pi HAT hardware and, only after sign-off, through release packaging.

## 1. Where The Project Stands

- Branch: `pi-port-main`, based on commit `5c9a2160` ("Install guide: fresh-node checklist,
  pinned RadioLib 7.7.1 and liblgpio-dev, alpha3 tag, gateway TX switch").
- The working tree is **dirty**: the alpha4 candidate exists only as uncommitted local changes
  on top of `5c9a2160`. Nothing about alpha4 is tagged, published, or hardware-verified.
- Last tag known to build from a clean clone: `v0.2.0-alpha3`. Earlier alpha tags do not.
- The candidate's scope, verified claims, and explicit limitations are in
  [pi_alpha_release_v0.2.0-alpha4.md](../current/pi_alpha_release_v0.2.0-alpha4.md). Read it
  first; do not re-state its unverified items as facts.

Uncommitted candidate changes fall into these groups:

1. Documentation reorganization into `docs/current/` (curated guide set) and `docs/archive/`
   (superseded bring-up notes), with deletions of the old top-level copies.
2. New optional standalone HAT I2C sensor sampler: `scripts/pi_hat_sensor_sampler.py`,
   `scripts/install-pi-hat-sensors-service.sh`,
   `deploy/systemd/meshcore-pi-hat-sensors.service`, and
   `test/test_pi_hat_sensor_sampler.py`.
3. Pi transport fix (`platform/pi_transport.cpp`: nonblocking `EAGAIN` handling) and
   latency/caching changes in `ui-native/src/meshcore_ui_native/` (broker, gateway link
   server, companion client, web app).
4. Shell script executable-mode and privilege fixes across `scripts/`.

## 2. Key Reference Documents

Start from the curated index: [docs/current/README.md](../current/README.md).

| Topic | Document |
|---|---|
| Hardware, connectors J1-J8, sensors, power | [pi_hat_hardware_spec.md](../current/pi_hat_hardware_spec.md) |
| Radio pin mapping (SX1262 / E22-900M33S) | [pi_hat_pinout.md](../current/pi_hat_pinout.md) |
| Build, install, smoke tests, release packaging | [pi_install_build_release.md](../current/pi_install_build_release.md) |
| Alpha scope and donor-companion contract | [pi_alpha_release.md](../current/pi_alpha_release.md) |
| Alpha4 candidate notes (this test's subject) | [pi_alpha_release_v0.2.0-alpha4.md](../current/pi_alpha_release_v0.2.0-alpha4.md) |
| Standalone-mode acceptance checklist | [pi-port/standalone.md](../current/pi-port/standalone.md) |
| Optional HAT sensor telemetry (sampler) | [pi-port/telemetry.md](../current/pi-port/telemetry.md) |
| Pi-hosted browser UI boundaries | [pi-port/pi-ui.md](../current/pi-port/pi-ui.md) |
| Release process and gates | [RELEASE_PROCESS.md](../current/RELEASE_PROCESS.md) |
| Donor/Pi ownership rules | [PORTING_RULES.md](../current/PORTING_RULES.md) |

## 3. Hardware And Environment Reference

- Target: Raspberry Pi 3B/Pi 4 with the Issue 1.0 HAT around the Ebyte E22-900M33S
  (SX1262-class) radio on SPI0; sensors SHT40, LPS22HH, ADS1015 on I2C1.
- Reference node known to build and run: Raspberry Pi OS trixie (32-bit), g++ 14.2,
  Python 3.13, `liblgpio-dev` 0.2.2, RadioLib **7.7.1** (pinned; newer is unvalidated).
- Verify the fitted PCB revision, connector pin-1 marks and the operator-confirmed J3 VBAT
  divider (250 k/100 k, x3.5) before trusting any voltage reading; see the hardware spec.
- The Pi runtime is the only radio/SPI owner. The sensor sampler is a separate service and
  must be the only I2C sampler on the HAT.

## 4. Test Project Plan

Work the phases in order. Each phase gates the next.

### Phase 0 - Produce A Clean, Reviewable Candidate Commit

The dirty tree is the single biggest handover risk. Before any hardware testing:

1. Review the uncommitted changes and separate intended candidate changes from unrelated
   local edits (preserve the latter; do not discard).
2. Create a clean commit (or small series) for the candidate and record the exact donor
   MeshCore base it tracks.
3. Run the hardware-free checks on that commit: the Pi-port unittest suite under `test/`
   (31 tests passing at handover, including three sampler tests), plus
   `python3 -m py_compile scripts/pi_hat_sensor_sampler.py` and `bash -n` on changed scripts.
4. Record the commit hash; all subsequent evidence must cite it.

### Phase 1 - Fresh-Clone Build On Pi Hardware

Follow [pi_install_build_release.md](../current/pi_install_build_release.md) exactly on a
supported Pi host:

1. Pre-checks: `ls /dev/spidev0.0`, `ls /dev/gpiochip0` (enable SPI via `raspi-config` if needed).
2. Install build deps and RadioLib 7.7.1 as documented.
3. Clone the Phase 0 commit fresh (do not reuse the dirty tree) into `/opt/meshcore-pi-port`.
4. Build the native runtime with `scripts/build-pi-live-runtime.sh` and confirm the early
   dependency-failure checks behave as documented.

### Phase 2 - Smoke Tests

1. App-mode companion smoke:
   `python3 scripts/run-native-companion-smoke.py --host 127.0.0.1 --port 5040`
2. Radio smoke per the install guide (`scripts/run-radio-smoke.sh`). Never run a radio smoke
   test while another node with the same identity is on the air.
3. Gateway-link smoke (`scripts/run-gateway-link-smoke.py --host 127.0.0.1 --port 7463
   --timeout 10`) only if deliberately exercising the gateway listener; it is **not** part of
   standalone acceptance and must be reported separately.

### Phase 3 - Standalone Acceptance

Execute the checklist in [pi-port/standalone.md](../current/pi-port/standalone.md). In
summary, record the exact port commit, upstream base, Pi OS/arch, HAT/radio revision, RadioLib
version and companion client version, then verify:

1. clean build and install from the documented source revision
2. service starts after reboot and reports its actual state
3. a published MeshCore client connects via `127.0.0.1:5040`, completes startup/device query
   and reads contacts, channels, time and status
4. Pi UI reads live state and its local operations work
5. one controlled receive test and one authorized transmit test **with recipient-side
   confirmation** (gateway acceptance is not RF delivery confirmation)
6. restart/reconnect without duplicate node identities or message replay
7. backup/recovery covers root-owned runtime state, radio identity and configuration, with
   secrets excluded from test reports

Record unsupported commands and behavioral differences explicitly; do not infer compatibility
from a successful connection. Also exercise the alpha4-specific changes: send latency on
direct and channel messages, cached contact/channel snapshots vs. manual Refresh rescan, and
cache staleness after changes made from another client.

### Phase 4 - Optional: HAT Sensor Telemetry

Only by explicit opt-in, following [pi-port/telemetry.md](../current/pi-port/telemetry.md):

1. Install the sampler without enabling it; verify I2C addresses and the generated unit.
2. Compare ADC voltage readings against a meter (divider ratios are nominal, VBAT x3.5).
3. Enable, then check `/tmp/meshcore-pi-telemetry.env` freshness, mode `0600`, and
   valid-field omission.
4. Review native telemetry permissions before any controlled request/reply RF test.
5. **Do not enable base/battery permission**: a missing/stale VBAT currently reports `0`,
   which must never be presented as a measured empty battery.

The sampler has never been installed or run on a Pi as of this handover; there are no hardware
readings to compare against.

### Phase 5 - Release Gate

Per [RELEASE_PROCESS.md](../current/RELEASE_PROCESS.md) and the alpha4 notes: review source
archive contents and hashes, record the exact archive hash when the test bundle is built, and
tag/publish only after clean-clone build, hardware sign-off, release-note review, and explicit
operator approval. Until then alpha4 remains an unpublished candidate.

## 5. Known Limitations And Risks To Carry Into Testing

- Prior Pi/EHN integration observations are historical; they do not certify this candidate.
- A send timeout is ambiguous; do not blindly retry.
- Pi UI `Check messages` reloads broker-cached history; it does not force a radio inbox sync.
- Routine caches can miss contact/channel changes made via another client until manual
  Refresh or reconnect.
- Meshtastic support is out of scope for this release and must not share the HAT with
  MeshCore during these tests.
- Standalone success does not prove EHN gateway integration, replication, sensor accuracy,
  or support for other radio HATs.

## 6. Evidence Rules

For every claim in the eventual release notes, record: commit hash, host details, exact
command, output/log excerpt, and date. Keep receive/transmit evidence recipient-confirmed.
Keep secrets, private keys, and node identity material out of public reports. Separate
standalone evidence from any EHN gateway evidence.
