# EHN Gateway Message Policy

This note captures the current working policy for how EHN should treat mesh traffic and external traffic at a basestation or gateway boundary.

This is an EHN and basestation policy note. It does not redefine MeshCore node semantics inside the runtime.

## Scope

This policy currently covers:

1. MeshCore direct and group traffic as seen by an EHN gateway
2. SMS and similar external text transports at the EHN edge
3. Ham plaintext-compliance rules for cross-transport traffic
4. Required identifiers and local cache assumptions
5. Unknown-sender, sensor, and malformed-message handling

This policy assumes one routable EHN group per gateway for now.

## Current Implementation Status

Reviewed against the current message-policy implementation on 2026-09-13.

The implemented live rules are now the target grammar:

1. `@user-id message text` for direct user delivery
2. `&group-id message text` for group delivery, where `group-id` is the owning `gateway_id`
3. `#sink-id message text` for sensor or device submissions; parsing lands, sink delivery is still a placeholder
4. `register` alone, case-insensitive, for registration lookup
5. MeshCore or Meshtastic traffic received on the designated private EHN channel is accepted as implicit group traffic
6. the legacy `EHN` prefix and `EHN:` probe are rejected with reason `legacy_prefix`
7. unknown or malformed traffic outside those rules is log-only with an explicit reason code

The normative grammar lives in `d:\Projects\EHN Documents\md\message-grammar.md`.

## Core Routing Model

Two operator-visible conversation modes are supported:

1. `single`
2. `group`

These are conversation-scope routing states, not permanent user types.

EHN also needs two broad actor classes:

1. `person`
2. `device`

`device` covers non-human senders and recipients such as weather stations, environmental sensors, telemetry probes, and hobby or STEM nodes.

Rules:

1. `single` means the message is intended for one person and should be routed only to that person's selected endpoint
2. `group` means the message is intended for the local shared EHN conversation and should be routed to the gateway's EHN private mesh channel when delivered onto MeshCore
3. replies should inherit the conversation scope unless the operator explicitly changes it
4. user records may store defaults and permissions, but not a permanent classification that a person is only a group user or only a single user
5. actor class is independent of conversation scope, so a `device` may publish group telemetry or may be queried directly as `single`

## MeshCore Policy

On MeshCore, EHN uses two traffic styles:

1. direct node-to-node messaging for `single`
2. the designated EHN private channel for `group`

Current working rules:

1. all one-to-one EHN traffic on MeshCore should be sent as direct node traffic
2. all group EHN traffic on MeshCore should be sent on the gateway's designated EHN private channel
3. public channels are not part of EHN routing by default
4. the basestation should preserve MeshCore-native routing behavior rather than trying to simulate a new mesh protocol above it

This keeps the mesh semantics simple:

1. direct remains person-to-person
2. channel remains shared conversation
3. the gateway decides which mode applies, but does not invent new radio behavior

## One Group Per Gateway

The current policy intentionally avoids multiple EHN groups on one gateway.

For now:

1. each gateway exposes one default EHN group conversation
2. that group maps to one private mesh channel on that gateway
3. `group` traffic targets that one group
4. `single` traffic targets a specific user endpoint

Serial fanout of one logical group message into many direct node messages is out of scope. It wastes airtime, complicates replies, and hides delivery differences between recipients.

## Required Identifiers

The minimum identifiers are:

1. `gateway_id`
2. `user_id`
3. `endpoint_id`
4. internal `group_id`

Current working assumptions:

1. each gateway has one globally unique `gateway_id`
2. each user has one stable `user_id`
3. each transport endpoint has its own stable `endpoint_id` or transport-native key
4. each gateway may keep an internal default `group_id`, but operators normally interact with the `gateway_id` as the visible group target because there is only one routable group per gateway

## Gateway Naming

Start with a simple operator-readable gateway naming scheme:

1. `EHN-<three-letter-region>`
2. examples: `EHN-NNJ`, `EHN-TEX`, `EHN-CAL`

If growth later requires multiple gateways in one region, allow an optional suffix:

1. `EHN-NNJ-1`
2. `EHN-NNJ-07107`
3. `EHN-NNJ-HOB`

The visible group target for the current one-group-per-gateway model is therefore the `gateway_id`.

## External Transport Policy

External text transports such as SMS should be normalized into the same `single` and `group` model.

When traffic enters or leaves an amateur-radio path, the basestation must also apply the existing ham plaintext and content-compliance rules. The gateway must not use the EHN routing layer to hide, tunnel, or preserve opaque protected content over a ham-facing message path.

Recommended rule:

1. the sender addresses either a user or a gateway group
2. the gateway resolves that target into the correct transport-native send action
3. if the selected delivery path includes ham radio, the resulting over-air content must be compliant plaintext in the form already defined by the EHN documentation and operating rules

For SMS, the implemented format is:

1. `@user-id message text` for `single`
2. `&group-id message text` for `group`
3. `#sink-id message text` for sink submissions
4. `register` as a lookup-only registration request

Examples:

1. `@jane-1234 Need status update`
2. `&EHN-NNJ Shelter supplies arrived`
3. `#school-weather 21.4C 68% 1012hPa`
4. `register`

Under this policy:

1. `@user-id` targets one person
2. `&group-id` targets the local group bound to that gateway
3. `#sink-id` targets a configured sink
4. external senders should not need to specify a gateway for direct messages unless later routing rules require an explicit override

## Target Message Grammar

The grammar below is now implemented; this section is kept for the reasoning.

Syntax:

1. `@user-id message text` for direct user delivery
2. `&group-id message text` for local group delivery
3. `#sink-id message text` for sensor or device submissions routed to one or more configured sink endpoints
4. `register` for registration lookup

Reasoning:

1. requiring `EHN` on every message is mostly redundant once the system already knows it is processing EHN-targeted traffic at the gateway edge
2. explicit first-character prefixes are easier to teach and easier to parse safely than mixing prefixed direct messages with bare-word group targets
3. `&group-id` removes ambiguity that would otherwise exist with a bare leading `gateway-id`
4. `#sink-id` creates a clean path for device and sensor traffic without pretending every destination is a person

Current intent for those targets:

1. `@user-id` resolves to one known user and then to that user's allowed endpoint routes
2. `&group-id` resolves to a local shared conversation or other policy-defined group target
3. `#sink-id` resolves to a sink policy that may fan out to one or more configured endpoints such as a local store, HTTP sink, email mailbox, or other adapter

Guardrails for the target grammar:

1. parsing should inspect only the first token and fail closed on ambiguity
2. bare unprefixed text should not be treated as a routable command by default
3. sink delivery must remain queue-backed so external HTTP or email endpoints are not a live dependency for message acceptance
4. actor class `device` should remain first-class and should map naturally onto `#sink-id` submissions

## Sensor And Sink Routing

Sensor or student device traffic is a valid expansion of the current model if it stays basestation-owned.

Recommended target behavior:

1. a device or student sender submits telemetry or report content using `#sink-id ...`
2. the basestation classifies the traffic as valid sensor or device content
3. the basestation stores the inbound event locally before any external fanout is attempted
4. the basestation resolves `#sink-id` into one or more configured sink endpoints
5. immediate delivery may target a local handler, while external delivery such as HTTP POST or email should be queued and retried by normal delivery policy

This keeps the architecture local-first. The student or field device submits data to EHN, and EHN remains responsible for validation, storage, and onward delivery.

Examples of viable future sink endpoints:

1. a school HTTP collector
2. a school mailbox
3. a local file or database sink
4. a future institution-specific adapter

These are delivery routes, not new message-policy brains.

## Explicit Registration

The current operational registration rule is intentionally narrow.

Registration is lookup-only traffic, not normal routed message traffic.

Current registration triggers:

1. a message consisting only of `register`, case-insensitive, on any transport
2. on the designated private EHN channel the same token is group-scoped registration

An addressed message whose body is `register` is ordinary routed text, and the retired `EHN:` probe is rejected as `legacy_prefix`.

Current registration outcomes:

1. reply `registered` when the sender exists in the local DB or is found in the authority DB and copied locally
2. reply `unknown user` when the message is valid registration traffic but the sender endpoint does not match either DB

Guardrail:

1. unknown registration requests do not create provisional local users

RCS identity note:

1. phone number matching remains the primary path when Android supplies a sender number
2. notification-derived RCS may provide only a visible contact name
3. when name-only RCS support is needed, the authority directory must store the exact visible sender string as `rcs_name`
4. `rcs_name` belongs only to the SMS transport path and should not be treated as meaningful MeshCore or Meshtastic identity data
5. name-only RCS should resolve only by that explicit field, not by loose display-name matching
6. once that lookup succeeds, `user_id` remains the canonical routing and operator identity; `rcs_name` is only a fallback ingress key

## Lessons From The Phone SMS Gateway

The current public Android bridge evidence is more valuable for operator behavior and routing constraints than for long-term data-model design.

What should be preserved from the phone-as-SMS-gateway experiments:

1. keep the SMS adapter thin and policy-driven rather than letting the phone app become a second routing brain
2. treat `group` and `single` as explicit operating modes, because mixed or ambiguous SMS reply behavior quickly becomes confusing
3. do not bridge public-channel mesh traffic into SMS by default
4. prefer one shared private-channel group path plus clear one-to-one routing rather than fuzzy hybrid heuristics
5. if a reply target is ambiguous, drop it and log the reason instead of guessing
6. use explicit caller or endpoint mappings where needed, but keep them unique enough to avoid accidental cross-routing
7. keep dedupe and echo suppression as first-class gateway responsibilities because phone notifications and bridged replies can easily loop
8. make operator logs explain why a message was delivered, dropped, throttled, or considered ambiguous

Operational lessons worth retaining:

1. the phone bridge depended on Android SMS receive and send permissions plus notification access, so the SMS adapter must expect platform-specific runtime prerequisites
2. the USB-connected mesh node is just the transport edge; the routing policy should stay above that device link
3. shared-channel routing is the simplest operator model for group traffic
4. channel-bound routing can work for dedicated one-to-one paths, but it introduces mapping conflicts and needs guardrails
5. only one effective routing mode at a time is easier for operators to understand than a half-implemented hybrid mode

Design guidance carried forward into EHN:

1. MeshCore and Meshtastic should share one transport-neutral routing policy layer
2. SMS should remain a carrier-specific ingress or egress adapter that feeds the same policy layer
3. ambiguous SMS-to-mesh or mesh-to-SMS cases should fail closed with logging
4. the first version should optimize for understandable behavior and operator trust, not for maximal automation
5. preserve room for later per-caller or per-endpoint overrides without making them the baseline model

Source-grounded note from the current Android app in `D:\Projects\Meshtastic Basestation\android-sms-gateway`:

1. the app is already close to the desired thin-adapter shape
2. it captures inbound carrier SMS through `SmsInboundReceiver`
3. it captures Google Messages RCS traffic through `MessagingNotificationListenerService`
4. it forwards accepted inbound traffic to the basestation over HTTP through `GatewayApiClient`
5. it polls the basestation for outbound SMS work in `BasestationGatewayService`
6. it sends outbound SMS through Android `SmsManager`
7. it reports completion back to the basestation
8. it does not contain direct Meshtastic USB transport logic in this project
9. it does not appear to hold the main routing or directory authority locally on the phone

Current implementation-specific limits that should be remembered:

1. the phone app is coupled to basestation HTTP endpoints such as `/api/sms/android/inbound` and `/api/sms/android/outbound`
2. outbound work is polling-based rather than event-pushed
3. RCS capture is notification-derived, so sender identity may be only a visible display name and not a phone number
4. Android runtime permissions and notification-listener access are operational prerequisites, not optional extras
5. the phone-side logs are meant to explain forwarding and send outcomes, but not to replace host-side routing authority

Recommended future direction from this code review:

1. keep SMS receive, SMS send, notification capture, and local phone settings on Android
2. keep routing mode, ambiguity decisions, directory lookups, dedupe policy, and ham compliance policy on the Windows or Pi basestation side
3. eventually replace or wrap the Android app's direct HTTP coupling with a more generic gateway-edge contract only if that adds real value without making deployment harder
4. do not move the common EHN routing brain onto the phone just because the phone currently has the carrier interface

## Immediate Integration Plan

Current agreed execution plan:

1. keep the current Android SMS app in service until it creates a serious operational roadblock
2. build the SMS gateway integration first against the Windows basestation because that is the faster workbench for development and inspection
3. write that Windows-side SMS integration so its gateway-facing contract and policy wiring can be moved to the Pi with minimal change
4. let the basestation own routing, directory resolution, policy, dedupe, delivery state, and operator logging across both MeshCore and SMS gateways
5. keep the Android side limited to phone-local concerns such as permissions, notification capture, SMS send, and SMS receive

What this means for the interface boundary:

1. the Android app remains an edge adapter that speaks the existing HTTP contract
2. the new basestation SMS gateway code should be written as a host-side adapter behind a transport-neutral gateway interface
3. no SMS-specific routing policy should be buried in Windows-only UI code or Android phone code
4. any host-specific concerns such as bind address, storage path, service wrapper, or LAN versus USB-debug connectivity must stay outside the core gateway policy layer so the same logic can run on Windows first and Pi later

Practical near-term target:

1. get one working Windows basestation path with the current Android app posting inbound traffic and claiming outbound work
2. connect that SMS path to the same basestation routing layer that will also manage the MeshCore gateway
3. use that paired MeshCore-plus-SMS setup as the first real basestation integration test bed before broadening to more gateway types

## Ham Plaintext Compliance

Ham-facing traffic must obey the EHN plaintext compliance rules already defined in the wider EHN documentation set.

Operational policy here is simple:

1. if a message will be transmitted over a ham mesh path, the emitted content must be compliant plaintext
2. the basestation may transform or normalize external content into compliant plaintext before ham transmission
3. the basestation must not relay encrypted, opaque, or non-compliant application payloads onto ham transport just because the inbound side was digital
4. if a message cannot be rendered into compliant plaintext, it must be blocked from ham transmission and logged
5. ham-to-non-ham forwarding may preserve the conversation meaning, but the ham-side representation must remain compliant

This means the security and policy layer is not optional when bridging between ham and general external transports. Validation must happen before the message is accepted for ham delivery.

## First-Seen Message Lookup And Local Copy

The basestation should treat first-seen valid EHN traffic as a trigger to hydrate local identity data.

For the first valid routed message seen from a sender endpoint:

1. check the local cache or field-station store first
2. if not found, query the authority or master database
3. if found, store a local copy of the relevant profile and endpoint data
4. if not found, create a provisional local sender record only when the message itself is valid EHN traffic

For explicit registration traffic:

1. check the local cache or field-station store first
2. if not found, query the authority or master database
3. if found, store a local copy of the relevant profile and endpoint data
4. if not found, reply `unknown user` and do not create a provisional local sender record

This supports local operation while preserving a stronger authority model on the master store.

Operational intent for field basestations:

1. a valid inbound message should not fail just because the local basestation has never seen that sender before
2. the field basestation should check its own local DB first because that is the fastest and most resilient path
3. if the sender is missing locally, the field basestation should ask the main or authority DB whether that sender or endpoint is already known
4. if the authority DB returns a match, the field basestation should cache a local copy and continue handling the message normally
5. if the authority DB has no match for a normal routed message, the basestation should treat the sender as an ad hoc new local record and continue, while clearly marking that record as provisional or observed
6. if the authority DB has no match for an explicit registration request, the basestation should not add a new local user record just because the registration probe was well formed

This means inbound traffic can continue even when the authority link is slow, partial, or temporarily absent.

## Review Of Valid Message Handling

The current implementation was reviewed before this document update so the target grammar does not silently contradict live code.

What is currently true in code:

1. SMS and other external text transports still require the explicit `EHN` prefix
2. `@user-id` is the only implemented explicit user-target syntax
3. group targeting still expects a gateway-style identifier after `EHN`
4. private EHN mesh channels remain implicit group traffic
5. `device` actor class and `telemetry` content class are already supported in the common policy layer
6. unknown syntax is logged rather than loosely guessed into another route

What this means for the next change:

1. dropping the `EHN` prefix is a deliberate behavior change, not a doc-only clarification
2. adding `&group-id` is a parser and operator-contract change, not just a UI wording change
3. adding `#sink-id` is a message-policy and delivery-policy expansion that should land together with sink-route modeling

## Background Authority Sync

The authority and field basestation databases should also converge outside the live message path.

Recommended baseline behavior:

1. field basestations should perform occasional background pull sync against the authority DB rather than relying only on message-triggered lookups
2. the sync can be periodic and simple, for example polling every few minutes or on a jittered interval, rather than trying to be event-perfect
3. the pull should be relevance-aware where possible, so smaller field stations receive users and endpoints that matter to their configured gateways, stations, roles, or recent traffic
4. local cache hydration from first-seen traffic should remain separate from slower background sync so message handling stays responsive
5. field basestations should report back useful authority-facing facts such as last seen, last active, endpoint verification changes, and provisional records created from valid traffic

Practical goal:

1. the authority DB remains the stronger source of identity truth
2. the field DB remains the resilient working cache plus local operational store
3. slow periodic sync catches edits made centrally even if no message traffic happens right away

## Upward Review And Promotion

New records discovered only from live inbound traffic need a controlled path back toward the authority DB.

Recommended behavior:

1. if a valid inbound sender is unknown to both local and authority DBs, create a provisional local record
2. mark that record with a review state such as `PENDING_AUTHORITY_REVIEW`
3. include enough evidence for later review, such as gateway, endpoint, first-seen time, last-seen time, actor class, and a small history summary
4. expose provisional records to operators so they can confirm, merge, enrich, or reject them
5. allow the authority side to accept a provisional record as a new known user, merge it into an existing user, or dismiss it as noise or abuse

Recommended propagation model:

1. field basestations should export or push review candidates upward to the authority DB on a slower background path or operator action
2. authority acceptance should create or update the main record and make that decision available to future field sync pulls
3. authority rejection should prevent the same endpoint from silently becoming a trusted record without renewed evidence or operator review

This preserves the ability to keep operating with new people in the field without allowing unreviewed first-seen traffic to become permanent authority truth automatically.

## Unknown Sender Policy

An unknown sender is not automatically an error.

If the incoming traffic is valid EHN traffic but the sender is unknown:

1. accept the message into the appropriate local conversation view
2. attempt profile lookup from the master database
3. if found, cache the sender locally
4. if not found, create a provisional local sender record
5. mark the sender state as unverified or provisional for operator awareness

Recommended sender states:

1. `known`
2. `cached`
3. `provisional`
4. `blocked`

## Device And Sensor Users

EHN must support non-human endpoints as first-class records.

The current policy uses a `device` actor class for:

1. weather stations
2. environmental sensors
3. telemetry beacons
4. hobby or STEM nodes
5. service endpoints that publish machine-generated status

Rules for `device` actors:

1. they still use normal `user_id` and `endpoint_id` style records, but their actor class is `device`
2. they may originate `group` traffic, especially periodic telemetry or local status reports
3. they may also support `single` request or response traffic when queried directly
4. their profile should carry enough metadata to describe sensor type, owner, location, and permitted output classes
5. the basestation should distinguish device-generated telemetry from person-to-person chat in storage and UI even when both use the same transport

Suggested profile fields for a `device` record:

1. actor class
2. device role
3. owner or steward
4. physical or logical location
5. supported telemetry classes such as base, location, or environment
6. publish mode such as periodic, event-driven, or request-response
7. ham plaintext eligibility for outgoing summaries or alerts

This allows weather and other sensor traffic to fit the same routing model without forcing every endpoint to look like a human chat user.

## Malformed Or Non-EHN Traffic

Malformed or non-EHN-format traffic should use the strictest simple default:

1. log it
2. optionally display it to operators for review
3. take no automatic action beyond logging

That means:

1. no auto-reply
2. no auto-relay
3. no auto-directory creation
4. no auto-conversion into `single` or `group`

Classify these cases separately:

1. valid transport, invalid EHN content: log only
2. invalid or corrupted transport framing: drop and log

Recommended log fields:

1. timestamp
2. gateway_id
3. transport type
4. source endpoint
5. destination token if present
6. message snippet
7. reason code such as `unaddressed_text`, `legacy_prefix`, `unknown_target_prefix`, `empty_target`, `invalid_target`, or `missing_body`

## Current Reply Rule

The current default reply rule is conservative.

1. valid EHN `single` traffic may be replied to as `single`
2. valid EHN `group` traffic may be replied to as `group`
3. malformed or non-EHN traffic should not receive an automatic reply
4. operators may still choose to respond manually outside automatic routing policy

## Minimum Basestation Responsibilities

The basestation code set should implement at least these behaviors:

1. classify inbound traffic as `single`, `group`, sink-bound, registration, or rejected
2. resolve `@user-id`, `&group-id`, and `#sink-id` destinations
3. map `single` to direct mesh delivery where a MeshCore endpoint exists
4. map `group` to the gateway's designated EHN private channel on MeshCore
5. enforce ham plaintext-compliance checks before transmitting traffic onto ham-facing paths
6. perform local-cache then master-database lookup on first valid sender traffic
7. persist local copies and provisional records using explicit sender status and actor class
8. support both `person` and `device` actors without collapsing telemetry into ordinary chat records
9. log malformed traffic with reason codes and no automatic follow-up actions
10. preserve enough conversation state that replies inherit `single` or `group` scope cleanly across transports

## Deferred Delivery And Fallback

EHN should treat acceptance, storage, and delivery as separate states.

Rules:

1. a message addressed to a known `user_id` may be accepted even when no active route is currently available
2. when no acceptable immediate route exists, the basestation should store the message in a durable pending-delivery queue rather than dropping it silently
3. a stored message should remain bound to the canonical `target_user_id`, not to a transient visible name
4. route selection should follow the user's delivery policy and preferred route order before any fallback path is used
5. later presence or last-seen updates may make a queued message eligible for retry
6. if no primary route becomes available within the configured hold window, the basestation may trigger a fallback path such as email if that policy is enabled

Recommended durable delivery states:

1. `queued`
2. `waiting_for_path`
3. `attempting`
4. `delivered`
5. `fallback_sent`
6. `expired`
7. `cancelled`

Sender-facing rule:

1. if a message is accepted and stored rather than delivered immediately, the sender should receive an automatic acknowledgement such as `message stored` when the ingress transport supports replies

Adapter-boundary rule:

1. durable acceptance, queue state, retry, lease, and fallback policy belong to common basestation code rather than any one gateway adapter
2. SMS over Android HTTP is only the current edge carrier; a later USB-connected phone path should reuse the same common queue and policy model
3. gateway adapters should translate between common delivery attempts and transport-specific send or completion mechanics, not own separate long-lived delivery truth

## Operator Visibility For Stored Messages

Stored messages should not be casually exposed in operator-facing screens.

Current policy intent:

1. normal workbench and basestation UI views should show the existence of queued messages without showing plaintext content by default
2. default list payloads should expose metadata such as sender, target, queue state, age, preferred route, fallback deadline, and last-attempt time, but not the stored message body
3. the UI should not show preview snippets, hover text, or searchable plaintext for queued content in routine operations
4. logs and audit trails should refer to message IDs, route decisions, and policy outcomes rather than repeating queued plaintext unless a deeper diagnostic path is explicitly required
5. this is an operator-visibility control, not a cryptographic protection boundary

Operational consequence:

1. plaintext may still exist in durable storage for routing purposes, but it should not be returned by the common API or rendered in the common UI path

## Presence, Last-Seen, And Station Facts

Deferred delivery depends on better station and presence facts than the current baseline.

Required policy additions:

1. each basestation should have an authority-known station profile with stable station identity, role, capabilities, and location fields
2. user presence should record at least `last_seen_at`, `last_seen_station_id`, and `last_seen_via_network`
3. presence updates should be treated as delivery triggers, not just operator display hints
4. authority and field stations should converge on these facts through the same local-cache and background-sync model already used for directory hydration
5. basestation ownership, operator contacts, capabilities, and future trust material should live in a separate logical basestation-registry store rather than being mixed into ordinary user-directory rows

Queue-claim rule:

1. when more than one station may deliver a stored message, checkout should use a lease with expiry and renewal rather than a permanent lock

## Language-Sensitive Standard Replies

Standard system replies should move out of hardcoded English strings.

Rules:

1. user profiles should carry a `preferred_language` field
2. automated system replies such as `registered`, `unknown user`, and `message stored` should resolve through a template layer
3. reply selection should prefer the sender's language when the system is responding to that sender
4. missing translations should fall back to a default language deterministically rather than failing the workflow

## Current Baseline

The current working baseline is:

1. one routable EHN group per gateway
2. direct node messaging for all one-to-one MeshCore traffic
3. one designated private mesh channel for all group MeshCore traffic on that gateway
4. SMS and similar external transports normalized into the same `single` and `group` model
5. ham-facing transmissions must pass plaintext-compliance checks before relay
6. first valid traffic triggers local-cache lookup and local profile hydration
7. `device` actors such as weather or sensor nodes are first-class EHN participants
8. malformed or non-EHN traffic is logged only
9. accepted-but-undeliverable directed messages should move into durable deferred delivery rather than disappearing silently
10. stored-message plaintext should stay out of routine operator UI views by default

This is intentionally narrow. It aims to be usable before adding multi-group routing, richer federation, or more aggressive automation.