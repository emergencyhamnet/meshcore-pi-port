# Release Process

Each Pi runtime release should be tied to a known upstream state.

For the first standalone Pi alpha, the release should come from the Pi port repository itself without requiring the basestation repository.

Release steps:

1. Sync `upstream-main` to the chosen upstream commit or release.
2. Merge into `pi-port-main`.
3. Validate radio init, identity store, donor API connect, and app-mode companion bridge.
4. Generate a dummy telemetry file with `scripts/write-dummy-telemetry-snapshot.py` and verify self telemetry returns stable values.
5. Validate one advert, one public message, and one direct message.
6. Tag the Pi runtime release.
7. If you publish a Pi binary, attach it as a convenience artifact built from the same tagged source and documented build script.

Do not release a build that depends on local-only companion protocol changes.