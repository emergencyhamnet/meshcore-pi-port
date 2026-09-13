# Meshtastic Adapter Start

This note captures the current agreed starting point for a future Meshtastic gateway or adapter.

The intent is to resume later without dragging the old prototype assumptions into the new basestation shape.

## Status

Current decision:

1. defer active Meshtastic implementation until MeshCore plus SMS behavior is stable end to end
2. do not convert the old Meshtastic prototype in place as the primary path
3. build a fresh Meshtastic adapter against the current basestation contract when work resumes

This is a planning and handoff note. It is not a request to add Meshtastic-specific runtime features to the Pi port now.

## Why A Fresh Adapter

The current architecture is clearer than the old prototype shape:

1. the basestation owns routing, directory lookup, operator-facing event history, and policy
2. the gateway adapter owns transport-specific send, receive, normalization, and health projection
3. the transport-native endpoint identity is the canonical matching key
4. human-readable `user_id` values are display and operator identifiers, not transport truth

Trying to retrofit the old Meshtastic prototype directly would likely preserve older UI-driven or name-driven assumptions that the newer MeshCore and SMS work is intentionally moving away from.

## Target Contract

When Meshtastic work resumes, mirror the current MeshCore-shaped adapter boundary rather than the old prototype boundary.

Expected ownership split:

1. basestation core
2. Meshtastic runtime client or link layer
3. Meshtastic adapter normalization layer
4. workbench display and operator actions

The basestation core should continue to own:

1. direct versus group policy
2. directory lookup and authority fallback
3. endpoint-to-user mapping
4. message event storage
5. cross-transport routing rules
6. compliance and ambiguity handling

The Meshtastic-specific slice should own:

1. connection and health status
2. node inventory and channel inventory projection
3. send actions using Meshtastic-native semantics
4. receive normalization into the common event model
5. transport-specific identifiers and metadata

## Identity Rules

The same identity hardening used for MeshCore should carry over conceptually.

Rules:

1. use the Meshtastic node identifier as the canonical endpoint identity for routing and matching
2. treat long name and short name as metadata only
3. if a node identifier matches a known directory endpoint, show that record's `user_id` in operator views
4. if no directory match exists, show the raw endpoint identity rather than inventing a human label from names
5. never depend on display names as the authoritative routing key

Important nuance:

1. Meshtastic node identity is the correct canonical transport identity for this adapter
2. it should still be treated as weaker than a MeshCore public key for trust purposes
3. the adapter should preserve that distinction rather than pretending both transports prove identity the same way

## Reuse Plan

Expected reusable pieces from the current stack:

1. common message policy and inbound classification logic in the basestation repo
2. directory user and endpoint model
3. gateway registration and orchestration pattern
4. message event store and normalization targets
5. workbench message rendering patterns that already prefer `user_id` with endpoint metadata shown separately

Expected Meshtastic-specific new work:

1. node-facing client implementation
2. inbound payload normalization
3. outbound send implementation
4. health and status mapping
5. handling of Meshtastic-specific delivery or acknowledgment semantics

## First Resume Steps

When implementation starts, do this in order:

1. inspect the old Meshtastic prototype only as donor reference for transport access and field availability
2. write down the exact adapter contract in basestation terms before copying any code
3. identify the minimum receive event shape needed for direct messages, group messages, node identity, and channel identity
4. map Meshtastic-native fields into the common event model with node ID as the canonical source identity
5. keep names and presentation details as optional metadata
6. add focused tests for identity mapping, direct routing, group routing, and unknown-sender handling before UI polish

## Open Questions To Resolve Later

These should be answered from the actual Meshtastic transport or client layer when work resumes:

1. what exact node identifier is consistently available on inbound and outbound paths
2. whether direct messages and channel messages expose the same sender identity fidelity
3. what acknowledgment or delivery evidence is actually available versus only locally accepted send requests
4. how much of the old prototype flattened node metadata too early
5. whether any current Meshtastic path already preserves both node ID and names cleanly enough to reuse the parsing layer

## Guardrails

Do not do these when the Meshtastic slice starts:

1. do not let Meshtastic-specific UI assumptions define the shared basestation contract
2. do not route by long name or short name
3. do not copy prototype naming or message-display shortcuts into the core policy layer
4. do not make Meshtastic behave like MeshCore where the transport semantics are actually different
5. do not add Meshtastic-specific logic to the Pi runtime repo unless it is strictly documentation or host tooling around the gateway boundary

## Related Notes

Relevant nearby references in this workspace:

1. `docs/EHN_GATEWAY_MESSAGE_POLICY.md`
2. `docs/WINDOWS_UI_HANDOFF_2026-08-24.md`
3. `docs/PORTING_RULES.md`

The basestation implementation work referenced by this note currently lives in the sibling `ehn-basestation` repository, not in this Pi runtime repository.