# v0.2.0-alpha4

## Status

Unpublished alpha4 **test candidate**. This candidate is assembled from a dirty local
`pi-port-main` working tree based on `5c9a2160`; it is not a tagged source revision and is not
ready for a GitHub release. The exact archive hash must be recorded when the test bundle is
built. Do not treat branch name or pre-existing live-service observations as release evidence.

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
- The new sampler has not been installed or run on a Pi; no hardware readings or native
	telemetry replies are validated by this candidate.
- Prior Pi and EHN integration observations are historical and do not certify this candidate.

## Explicit limitations

- Dummy snapshot values must not be presented as measured hardware values. The optional sampler
	is separate from the runtime, and sensor accuracy/calibration and receiver-visible telemetry
	remain unverified.
- Gateway acceptance is not RF delivery confirmation. A send timeout is ambiguous and must not be blindly retried.
- The Pi UI `Check messages` controls reload broker-cached conversation history; they do not directly force a radio inbox sync. They remain for compatibility and may be removed or relabeled later.
- Routine caches can miss contact/channel changes made through another client until manual Refresh or a reconnect performs discovery.
- The basestation currently polls Pi inbound events every second; a future broker/event-stream integration can remove that remaining polling interval.
- Meshtastic support is not included in this Pi-port release. It remains a separate basestation
	gateway adapter and must be tested on separate hardware or storage before sharing the Pi HAT
	with MeshCore.

## Release validation still required

1. Decide and create a clean, reviewable commit from the intended candidate changes; preserve
	unrelated local edits and record the exact donor MeshCore base.
2. Build from a fresh clone of that exact commit on supported Pi hardware.
3. Run the app-mode companion smoke test and gateway-link smoke test.
4. Test standalone MeshCore compatibility and Pi UI behavior separately from EHN gateway-link
	behavior.
5. If testing HAT telemetry, install the sampler only by explicit opt-in, check calibrated
	readings and file freshness, then review native telemetry permissions before a controlled
	request/reply test. Battery permission remains unsafe to claim until missing/stale VBAT
	semantics are resolved.
6. Confirm the published MeshCore client connects through `127.0.0.1:5040` and obtain
	recipient-side evidence for authorized direct/group RF tests.
7. Review source archive contents and hashes. Tag and publish only after clean-clone build,
	hardware sign-off, release-note review and explicit approval.
