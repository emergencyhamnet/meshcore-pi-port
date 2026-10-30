# v0.2.0-alpha4

## Status

Unpublished alpha4 **test candidate**. The candidate is now a clean commit series on
`pi-port-main`: base `5c9a2160`, candidate commit `96ebe5f2`, plus bring-up fixes
`fc1baf8f` (missing time-sync timer template), `39d96d9c` (set-time helper port collision),
`e9ddba38` (set-time already-synced tolerance) and `0447cb16` (boot-only time-sync timer).
Hardware validation of `0447cb16` is recorded below. Not yet tagged or published; the exact
archive hash must still be recorded when the release bundle is built.

## Highlights

- Fixed the Pi nonblocking transport path so `EAGAIN` means the connection remains healthy.
- Reduced direct and channel send latency by avoiding full node snapshots and synchronous post-send inbox drains.
- Added cached contact and active-channel inventories to routine UI/gateway snapshots.
- Routine snapshots read channel 0 plus known active channel slots instead of probing every capacity slot.
- Manual UI Refresh and channel creation perform an explicit full channel rescan.
- Removed routine full node refreshes after message events and sends.
- Reduced basestation MeshCore inbound forwarding polling from 15 seconds to 1 second.
- Added single-flight protection to the basestation workbench refresh cycle.
- Improved SMS panel resilience by retaining the last good state during transient refresh failures.
- Added RCS registration replies and group/direct messaging-mode enforcement in the basestation.
- Corrected Pi shell-script executable modes and made the runtime build script avoid privileged storage writes.
- Added focused broker, channel-cache, routing, group-fanout, deduplication, and refresh tests.
- Added an optional standalone HAT I2C sampler that writes the Pi runtime's timestamped native
	telemetry snapshot format. It is a separate systemd service, installed disabled by default;
	it does not change native telemetry permissions or send broadcasts.

## Verified

- Pi-port unittest suite: 31 tests pass locally, including three hardware-free sampler tests.
- Sampler syntax and shell installer/packager syntax checks pass locally.
- Prior Pi and EHN integration observations are historical and do not certify this candidate.

## Hardware validation, 2026-10-30

Commit `0447cb16` built from a fresh clone on a newly imaged node and passed the standalone
acceptance checklist in `pi-port/standalone.md`:

- Host: Raspberry Pi 3B, Raspberry Pi OS Lite 64-bit (Debian 13 trixie), aarch64,
  kernel 6.18, g++ 14.2, Python 3.13, liblgpio-dev 0.2.2, RadioLib 7.7.1. **First 64-bit
  build/run validation** (warnings only; previously only 32-bit was proven).
- HAT: Issue 1.0 board, E22-900M33S; SHT40/ADS1015/LPS22HH all present on I2C1.
- Clean build via `scripts/build-pi-live-runtime.sh`; `live_radio_ready=1`,
  `live_runtime_ready=1`.
- Runtime, browser UI and boot-only time-sync services survive reboot; node identity stable
  across two reboots and multiple runtime restarts (no duplicate identities).
- App-mode companion smoke test passes (`127.0.0.1:5040`).
- Pi UI live operations verified over its API: set name, set radio params (persisted across
  runtime restart), flood advert, channel/contact reads, direct message send.
- RF acceptance with a second node (LilyGo T-Beam, same room, SNR ~11.75 both ways):
  flood advert received by the T-Beam; incoming direct message received and decrypted on the
  Pi; authorized reply delivered with recipient-side confirmation.
- Standalone HAT sampler installed, enabled and producing fresh snapshots every 10 s
  (temperature/humidity/pressure/VBAT; mode 0600). Native telemetry permissions remain 0.
  Sensor accuracy/calibration against reference instruments is still unverified.
- Root-owned state backup (`/var/lib/meshcore-pi-port`: identity, channels/contacts, prefs,
  state) created and content-verified.

## Explicit limitations

- The companion bridge serves **one client at a time**. The Pi browser UI holds the
	`127.0.0.1:5040` session whenever its service is running, so a published MeshCore client
	(or any smoke test) cannot connect until `meshcore-pi-browser-ui.service` is stopped. A
	client connecting during session handover may receive one stale push frame.
- Dummy snapshot values must not be presented as measured hardware values. The optional sampler
	is separate from the runtime, and sensor accuracy/calibration and receiver-visible telemetry
	remain unverified. The onboard SHT40 reads board/enclosure temperature (~40 C observed on an
	idle Pi 3B), not ambient.
- Gateway acceptance is not RF delivery confirmation. A send timeout is ambiguous and must not be blindly retried.
- The Pi UI `Check messages` controls reload broker-cached conversation history; they do not directly force a radio inbox sync. They remain for compatibility and may be removed or relabeled later.
- Routine caches can miss contact/channel changes made through another client until manual Refresh or a reconnect performs discovery.
- The basestation currently polls Pi inbound events every second; a future broker/event-stream integration can remove that remaining polling interval.
- Meshtastic support is not included in this Pi-port release. It remains a separate basestation
	gateway adapter and must be tested on separate hardware or storage before sharing the Pi HAT
	with MeshCore.

## Release validation still required

1. Confirm the published MeshCore client connects through `127.0.0.1:5040` (stop the browser
	UI service first; the bridge serves one client at a time).
2. If claiming calibrated telemetry, compare sampler voltage/environment readings against
	reference instruments and review native telemetry permissions before a controlled
	request/reply test. Battery permission remains unsafe to claim until missing/stale VBAT
	semantics are resolved.
3. Review source archive contents and hashes. Tag and publish only after release-note review
	and explicit approval. Clean-clone build and standalone hardware sign-off were completed
	2026-10-30 (see Hardware validation above); EHN gateway-link behavior remains untested on
	this candidate.
