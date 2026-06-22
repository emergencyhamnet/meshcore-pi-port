# Releasing Firmware

GitHub Actions is set up to automatically build and release firmware.

## Pi Port Alpha Releases

The Raspberry Pi HAT port currently uses a manual release flow rather than the firmware tag automation below.

Current standalone Pi alpha release notes live in:

1. `docs/pi_alpha_release.md` for scope, install, and packaging guidance
2. `docs/pi_alpha_release_v0.1.0-alpha1.md` for the `v0.1.0-alpha1` GitHub release body

For Pi alpha releases:

1. tag the tested `pi-port-main` commit
2. push the branch and tag
3. create the GitHub release manually using the matching notes file
4. optionally attach a prebuilt Pi binary bundle produced on the Pi host

It will automatically build firmware when one of the following tag formats are pushed.

- `companion-v1.0.0`
- `repeater-v1.0.0`
- `room-server-v1.0.0`

> NOTE: replace `v1.0.0` with the version you want to release as.

- You can push one, or more tags on the same commit, and they will all build separately.
- Once the firmware has been built, a new (draft) GitHub Release will be created.
- You will need to update the release notes, and publish it.
