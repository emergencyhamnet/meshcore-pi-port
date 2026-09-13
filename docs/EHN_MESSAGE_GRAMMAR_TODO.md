# EHN Message Grammar TODO

This note captures the deferred code work needed to move from the current implemented message grammar to the preferred target grammar after presentation work and continued testing.

## Current Baseline

Current implemented behavior:

1. direct external message: `EHN @user-id message text`
2. group external message: `EHN gateway-id message text`
3. registration lookup on SMS: `EHN:`
4. MeshCore and Meshtastic private EHN channel traffic: implicit group traffic

## Target Grammar

Normative spec: `d:\Projects\EHN Documents\md\message-grammar.md`.

Decisions confirmed 2026-09-13:

1. `@user-id message text` for direct user delivery
2. `&group-id message text` for group delivery; `group-id` is the owning `gateway_id` for now
3. `#sink-id message text` for sensor or device submissions routed by sink policy
4. `register` alone, case-insensitive, is the registration token; `EHN:` is retired
5. the legacy `EHN ` prefix is rejected outright with reason `legacy_prefix`, no transition window
6. bare unaddressed text on external transports is log-only with no reply
7. user and sink ids normalize to lowercase, group ids to uppercase

## Code Tasks

Done on 2026-09-13 in `d:\Projects\ehn-basestation`:

1. parser no longer accepts the `EHN` prefix; `legacy_prefix` is a hard rejection
2. explicit `&group-id` parsing; bare-word group targets are rejected as `unaddressed_text`
3. explicit `#sink-id` parsing with target type `sink`
4. sinks resolve to a sink registry in the delivery DB: `sinks` and `sink_endpoints` tables in `DeliveryStore`
5. private-channel implicit group behavior preserved on MeshCore and Meshtastic
6. registration is whole-message `register`
7. sink endpoints support `local-file` and `http` adapter types in `ehn_basestation.sinks`; `email` is a future adapter
8. sink delivery rides the shared queue as route `sink`, target `sink:<sink-id>`, one pending row per enabled endpoint, retry on transport failure, no retry on 4xx or missing adapter
9. sink validation covers enabled state, accepted actor classes, accepted content classes, and `max_body_chars`
10. sink submissions appear as `sink_submission` events with `network=sink` and `conversation_scope=sink`; workbench exposes `GET /api/delivery/sinks` and `POST /api/delivery/sinks/dispatch`
11. tests: `tests/test_message_policy.py`, `tests/test_sink_delivery.py`, and sink cases in `tests/test_workbench_server.py`
12. `ham_plaintext_gate_required` still set from transport policy regardless of grammar

Remaining:

1. authority console read-only sink inventory
2. `email` sink adapter
3. live validation of `@`, `&`, `#`, and `register` through the Android SMS app
4. sink admin UI beyond the `seed-sinks` / `show-sinks` CLI and `dev/windows/data/sinks-seed.json`

## Deferred Documentation Tasks

1. update onboarding material to explain `@`, `&`, and `#` as the primary operator grammar
2. document sink endpoint configuration for testers once the HTTP collector path is exercised live

## Decision Notes

Working guidance:

1. the basestation remains the routing authority
2. gateways remain thin adapters
3. external sink endpoints are delivery adapters, not alternate sources of policy truth
4. local acceptance and storage should not depend on live internet access