# Standalone MeshCore Node

**Status:** operating-mode scope and acceptance draft, 2026-10-25.

## Goal

Operate the Pi HAT as a MeshCore node without requiring the EHN basestation. Donor MeshCore
semantics and the published companion protocol are the compatibility reference. The goal is
high compatibility for the supported Pi hardware and firmware, not an unqualified claim of
parity with every native MeshCore board or app version.

## Interfaces

- The app-mode companion endpoint exposes the donor companion protocol to a published
  MeshCore client. Confirm the address and transport on the installed release; current alpha
  documentation uses loopback `127.0.0.1:5040`.
- The Pi-hosted browser UI is a separate local operator interface. See [Pi UI](pi-ui.md).
- The radio, MeshCore node identity, contacts, channels and persisted node state belong to the
  Pi runtime. They are not EHN directory records and must not be cloned casually between live
  nodes.
- An EHN gateway-link listener is not required for standalone operation unless deliberately
  enabled for a later integration test.

## Acceptance Checklist

Record the exact port commit, upstream MeshCore base, Pi OS/architecture, HAT/radio revision,
RadioLib version and companion client/app version. Then verify:

1. clean build and install from the documented source revision
2. service starts after reboot and reports its actual state
3. published companion client connects, completes startup/device query and reads supported
   contacts, channels, time and status
4. Pi UI reads live state and its intended local operations work
5. one controlled receive test and one authorized transmit/recipient-confirmed test
6. restart/reconnect behavior without duplicate node identities or unexpected message replay
7. recovery and backup include the correct root-owned runtime state, radio identity and
   application configuration, while excluding secrets from public test reports

Record unsupported commands, features, app versions and known behavioral differences rather
than inferring compatibility from a successful connection.

## Not Implied

Standalone success does not prove EHN gateway-link integration, basestation policy behavior,
replication, hardware sensor accuracy, or support for other radio HATs. Those require their
own scope and evidence.