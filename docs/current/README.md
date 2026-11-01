# Pi Port Current Documentation

**Status:** curated Pi-port documentation index, 2026-10-30. These documents describe current
scope and setup as understood in the local working tree; verify the exact release tag and
hardware before following an installation procedure.

## Next Project

- [Handover: alpha standalone Pi HAT testing](../handover/pi_alpha_standalone_testing_handover.md):
  repository state at handover and the phased plan for validating the v0.2.0-alpha4 test
  candidate on hardware.

## Start Here

1. [Hardware and connector specification](pi_hat_hardware_spec.md): J1-J8, Pi pin map, sensors, power and software boundary.
2. [Radio pinout summary](pi_hat_pinout.md): supported SX1262-family radio mapping.
3. [Build, install and release workflow](pi_install_build_release.md): practical Pi build and operating steps; release/tag references still require reconciliation before publication.
4. [Alpha scope](pi_alpha_release.md): standalone donor-companion contract and limitations.
5. [Alpha5 release notes](pi_alpha_release_v0.2.0-alpha5.md): RF control corrections and upgrade steps.
  [Alpha4 release notes](pi_alpha_release_v0.2.0-alpha4.md): v0.2.0-alpha4 scope, hardware
   validation evidence and known limitations.

## Operating Modes And Interfaces

- [Standalone MeshCore node](pi-port/standalone.md): native companion compatibility and standalone acceptance.
- [EHN gateway mode](pi-port/ehn-gateway.md): ownership, gateway link and integration acceptance.
- [Pi-hosted UI](pi-port/pi-ui.md): companion/UI/gateway control boundaries.
- [Standalone HAT sensor telemetry](pi-port/telemetry.md): optional I2C sampler, native request/reply permissions and limitations.

## Development And Release

- [Pi-port documentation scope](pi-port/index.md): overview and documentation rules.
- [Upstream provenance and maintenance](pi-port/upstream-maintenance.md): donor source tracking, sync and release validation.
- [Upstream sync procedure](UPSTREAM_SYNC.md): existing branch workflow.
- [Porting rules](PORTING_RULES.md): donor/Pi ownership boundaries.
- [Release process](RELEASE_PROCESS.md): manual Pi alpha release steps.

The older [bring-up/deployment notes](../archive/README.md) are retained for history but
contain commands and service layouts superseded by this current guide set.
