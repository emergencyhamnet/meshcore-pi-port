# Release Process

Each Pi runtime release should be tied to a known upstream state.

Release steps:

1. Sync `upstream-main` to the chosen upstream commit or release.
2. Merge into `pi-port-main`.
3. Validate radio init, identity store, and donor API connect.
4. Validate one advert, one public message, and one direct message.
5. Tag the Pi runtime release.
6. Update the basestation repository to pin that tested runtime release.

Do not release a build that depends on local-only companion protocol changes.