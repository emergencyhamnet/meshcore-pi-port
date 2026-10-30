# Pi-Hosted UI And Control Surfaces

**Status:** interface ownership draft, 2026-10-25.

The Pi port presents more than one interface. They are complementary clients of the Pi node,
not interchangeable authorities:

| Surface | Role | Typical address | Ownership |
|---|---|---|---|
| Published MeshCore companion client | Native donor companion workflow through app mode. | Pi loopback `127.0.0.1:5040`, forwarded or proxied according to the installed setup. | Pi runtime owns the companion endpoint and node session. |
| Pi-hosted browser UI | Local node operation, status, settings, contacts, channels and diagnostics/tools as implemented by the release. | Current local deployment uses `http://<pi-host>:8099/`. | Browser service and shared native-session broker; verify the owning systemd unit for that revision. |
| EHN gateway link | Basestation-facing adapter, not a general browser API. | Current local deployment uses port `7463`. | Browser/gateway service and the same native-session broker in the embedded-listener layout. |

The companion client and Pi UI should preserve donor MeshCore node behavior. EHN-specific
identity, policy and routing belong to the basestation, not to a Pi UI label or contact name.
In EHN mode, gateway-link permission applies to basestation operations through that link; it
must not be described as a universal transmit lock for all local/native interfaces unless the
implementation explicitly enforces that stronger policy.

## Operator Documentation Needed

For each released UI version, document the verified pages and actions, connection indicators,
what is cached versus refreshed, the owning service, safe restart procedure, and which actions
can transmit or alter radio/node state. Mark absent, experimental or untested controls rather
than retaining menu items as implied capabilities.

## Acceptance

Test the browser UI in standalone and EHN-enabled configurations: initial load, stale/offline
state, settings and channel changes, contact refresh, direct/group messaging where supported,
service restart, responsive layout and failure reporting. Verify a UI or API status read does
not create a competing hardware session. Separately prove the native companion path continues
to work when the Pi UI is running.