# Raspberry Pi MeshCore Port

**Status:** documentation scope draft, 2026-10-25. Check release tags, hardware, service
templates and live behavior before treating any procedure as a validated installation recipe.

The Pi port has two use cases. Where supported, they share the MeshCore node runtime and
Pi-hosted UI, but have different integration and acceptance requirements. Select the use case
before setup. A standalone alpha artifact does not automatically include or certify the EHN
gateway integration; the EHN-linked local deployment may be a separate source state.

## Choose A Use Case

| Use case | Purpose | Primary interface | Additional interface |
|---|---|---|---|
| [Standalone MeshCore node](standalone.md) | Operate the Pi as a MeshCore node without requiring an EHN basestation. Preserve compatibility with donor MeshCore behavior and published companion clients as closely as the supported port allows. | Published MeshCore companion app through the app-mode endpoint. | Pi-hosted browser UI for node operation and diagnostics. |
| [EHN basestation gateway](ehn-gateway.md) | Attach the Pi node to a separate EHN basestation for EHN policy, identity, routing and delivery. | EHN gateway link to the basestation. | The same Pi-hosted browser UI and companion endpoint remain distinct control surfaces. |

The [Pi UI guide](pi-ui.md) describes those surfaces and their ownership boundaries. One mode
does not imply that the other has been configured or acceptance-tested.

## Shared References

- [Hardware and wiring](../pi_hat_hardware_spec.md): full connector/software specification; [radio pinout](../pi_hat_pinout.md) summarizes the radio-specific mapping.
- [Build, install and release guide](../pi_install_build_release.md): current practical workflow; verify its referenced tag and service commands against the release being prepared.
- [Runtime architecture and staged bring-up](../PI_NATIVE_BRINGUP.md): engineering history/reference. Some sections describe earlier layouts; do not use a conflicting command over the current build/install guide without checking the scripts.
- [Browser UI deployment notes](../PI_BROWSER_UI_MOVE_PLAN.md): service and deployment history; reconcile its separate gateway-link service examples with the current embedded-listener service layout.
- [Alpha scope](../pi_alpha_release.md): release intent and limitations.
- [Standalone HAT sensor telemetry](telemetry.md): optional I2C sampler, native MeshCore request/reply behavior, and permission gates.
- [Upstream source and update policy](upstream-maintenance.md): provenance and release gate.

## Documentation Rules

- Label statements as released, tested local behavior, candidate, or planned. A working tree or live node is not automatically a published release.
- Record exact Pi-port commit, donor MeshCore commit/tag, build dependencies, hardware revision and service layout for each release.
- Keep standalone companion compatibility, Pi UI operation and EHN gateway-link integration as separate test rows.
- Never document example or private node identities, channel keys, credentials, or operational database paths as transferable configuration.
- Preserve the single-owner rule for the radio/SPI hardware and native companion session. Do not start a second broker or gateway-link listener to follow an older service example.

## Known Documentation Work

These pages establish scope and acceptance criteria. They do not certify that every listed
test has passed. The old bring-up and browser-move records need reconciliation with the
current install script and installed service templates. See [upstream maintenance](upstream-maintenance.md)
for release provenance requirements.