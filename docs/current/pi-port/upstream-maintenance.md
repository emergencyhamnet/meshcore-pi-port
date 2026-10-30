# Upstream Provenance And Maintenance

**Status:** process draft, 2026-10-25. Confirm repository remotes, exact source ancestry and
license notices before publishing a release statement.

## Provenance Record

The Pi port is based on donor MeshCore code from the
[upstream MeshCore repository](https://github.com/meshcore-dev/MeshCore), with Pi-owned
Linux runtime, transport, storage, GPIO, SPI/RadioLib HAL, service packaging and UI/gateway
integration. For every release, record:

- upstream repository URL and exact commit or release tag used as the donor base
- Pi-port branch, exact commit/tag and date built
- which release files/patches are upstream-derived, Pi-owned, or packaging/deployment-only
- third-party dependency versions and their applicable license notices
- build OS, architecture, compiler, RadioLib and `lgpio` versions, plus whether the artifact
  was built from a clean checkout
- known deviations, unsupported hardware and compatibility test results

Do not state only "latest upstream" or infer provenance from the branch name.

## Update Workflow

The existing [upstream sync notes](../UPSTREAM_SYNC.md) describe the branch flow, and
[porting rules](../PORTING_RULES.md) state the donor-behavior constraints. Before applying an
upstream update:

1. fetch and record the candidate upstream commit; review release notes and changes touching
   companion protocol, `MyMesh`, datastore, transport and radio behavior
2. sync the upstream mirror branch without Pi edits, then integrate that reviewed state into
   the Pi port
3. resolve conflicts with an ownership map; keep platform adaptation in Pi-owned files where
   practical, and justify every donor behavior change
4. build from a clean checkout and review the donor/Pi diff; never treat an incremental build
   from a dirty working tree as release evidence
5. run the validation matrix below before updating the recorded supported version

The existing porting rule that says to avoid gateway-specific functionality must be read
alongside the Pi port's gateway-link role: preserve upstream MeshCore node semantics, while
implementing EHN adaptation at the Pi-owned boundary. Resolve any ambiguity in those rules
before accepting a change that alters donor behavior.

## Release Validation Matrix

| Area | Minimum evidence |
|---|---|
| Build and hardware | Clean clone, supported Pi OS/architecture, exact HAT/radio wiring, pinned toolchain/dependencies, clean runtime build. |
| Native compatibility | Published companion client connects; startup/device query, contacts/channels and supported messaging behavior checked. |
| Pi UI | UI surfaces and operations tested; its session ownership, errors, refresh behavior and restart path documented. |
| Standalone node | Receive plus controlled transmit with remote receipt evidence; reboot/reconnect and state persistence checked. |
| EHN integration | Gateway-link status, transmit-disabled rejection, permitted direct/group paths as supported, and separate basestation/Pi service recovery checked. |
| Release artifact | Exact source archive and optional binary correspond to the same recorded Pi commit; hashes and release notes reviewed. |

Not every release must claim every optional feature, but unsupported rows must be marked
untested or out of scope rather than silently omitted. Publish standalone and EHN results
separately so one mode cannot imply acceptance of the other.