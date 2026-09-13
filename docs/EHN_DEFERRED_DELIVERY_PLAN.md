# EHN Deferred Delivery Plan

This note formalizes the next delivery-state expansion for the EHN basestation stack.

It covers four linked concerns:

1. basestation profiles and user last-seen facts
2. durable pending delivery with preferred-route and fallback policy
3. language-sensitive automated replies
4. operator-facing privacy by hiding queued message content in normal UI flows
5. a separate basestation-registry data store for station ownership, contact, capabilities, and future trust material

This is an implementation-planning note, not a final protocol specification.

## Design Goals

The next slice should preserve the current direction:

1. keep routing and policy in the basestation core, not in UI code and not in the phone gateway
2. keep `user_id` as the canonical identity for routing, storage, and queue ownership
3. treat `accepted`, `stored`, and `delivered` as distinct outcomes
4. allow delayed delivery when a user becomes reachable later
5. keep normal operator screens aware of queue existence without making queued plaintext easy to browse
6. avoid introducing cryptographic requirements into the first deferred-delivery slice
7. keep basestation identity and future inter-station trust material separated from ordinary user-directory rows

## Working Decisions

These decisions should be treated as the working baseline unless later testing disproves them.

1. the durable source of truth for deferred delivery should live in the main or authority DB
2. field basestations may cache queue summaries locally, but they should not each invent independent queue truth for the same message
3. email fallback should be modeled as a delivery endpoint plus policy, not as ordinary personal-profile text
4. standard replies such as `registered`, `unknown user`, and `message stored` should come from a template layer keyed by language and reply type
5. routine UI payloads should return queue metadata only; queued plaintext should be omitted from the normal workbench API surface
6. basestation profile data should live in a separate logical registry store, even if the first implementation keeps it in the same database engine
7. future station-to-authority or station-to-station secret keys should not be embedded into the ordinary user directory tables

## Separate Basestation Registry Store

The need for a separate basestation-details store should be treated as confirmed.

Reasoning:

1. station records have a different lifecycle from user records
2. station ownership, operator contacts, deployment status, and capability inventory are operational assets, not person-directory attributes
3. future inter-station trust material and keys need stronger separation and narrower exposure than everyday directory lookups
4. queue ownership and delivery claims will depend on stable station identity, so station metadata should not be an afterthought

Recommended first implementation shape:

1. define a dedicated basestation-registry schema or separate database now
2. keep it linked to the authority directory through stable `station_id` references
3. allow the first implementation to use the same SQLite engine if needed, but keep separate tables and access paths so it can later move to a distinct DB without rewriting the model

Recommended station-registry domains:

1. station identity and naming
2. owning organization or steward
3. operator contacts and escalation contacts
4. capability inventory and gateway roles
5. deployment location and status
6. future trust material and key metadata

This separation is especially important once encryption, signed sync, or trusted multi-station queue claims are added.

## Data Model Additions

The current implementation lacks durable storage for presence, queued delivery, route policy, and language preference. The next schema slice should add at least the following models.

### Basestation Registry

Suggested separate logical store: `basestation_registry`

Suggested tables:

1. `stations`
2. `station_contacts`
3. `station_capabilities`
4. `station_trust_material`

Suggested `stations` fields:

1. `station_id`
2. `station_name`
3. `station_role`
4. `owner_name`
5. `owner_org`
6. `deployment_status`
7. `location_label`
8. `location_lat`
9. `location_lon`
10. `notes`
11. `created_at`
12. `updated_at`

Suggested `station_contacts` fields:

1. `contact_id`
2. `station_id`
3. `contact_role`
4. `display_name`
5. `phone`
6. `email`
7. `preferred_contact_method`
8. `is_primary`
9. `updated_at`

Suggested `station_capabilities` fields:

1. `station_id`
2. `supports_meshcore`
3. `supports_sms_gateway`
4. `supports_meshtastic`
5. `supports_email_fallback`
6. `supports_queue_claims`
7. `supports_encrypted_sync`
8. `last_verified_at`

Suggested `station_trust_material` fields for later use:

1. `station_id`
2. `key_purpose`
3. `key_identifier`
4. `public_material`
5. `encrypted_private_material`
6. `material_status`
7. `rotation_due_at`
8. `updated_at`

Purpose:

1. keep ownership and contact metadata out of user-directory rows
2. support queue claims and retry decisions with a stable station identity source
3. provide a deliberate home for future encryption and trust rollout

### Station Profile

Suggested table: `station_profiles`

Suggested fields:

1. `station_id`
2. `station_name`
3. `station_role`
4. `capabilities_json` such as `meshcore`, `sms_gateway`, `meshtastic`, `email_fallback`
5. `location_label`
6. `location_lat`
7. `location_lon`
8. `status`
9. `last_reported_at`

Purpose:

1. identify where a user or endpoint was last observed
2. describe which stations can perform which delivery actions
3. support later routing decisions without pushing that logic into UI code

Relationship note:

1. `station_profiles` should be treated as runtime-presence or replicated-operational facts keyed by `station_id`, while the basestation registry holds longer-lived ownership, contact, capability, and trust records

### User Presence

Suggested table: `user_presence`

Suggested fields:

1. `user_id`
2. `last_seen_at`
3. `last_seen_station_id`
4. `last_seen_via_network`
5. `last_seen_endpoint_id`
6. `presence_state`
7. `presence_evidence` such as `register`, `message`, `advert`, `operator-confirmed`
8. `updated_at`

Purpose:

1. power the `Registered Users` view with stronger semantics
2. act as a delivery retry trigger
3. record where a user was last seen, not just when

### Delivery Policy

Suggested table: `delivery_policies`

Suggested fields:

1. `user_id`
2. `preferred_route_json` ordered list such as `meshcore`, `sms`, `meshtastic`, `email`
3. `fallback_email_enabled`
4. `fallback_hold_seconds`
5. `retry_interval_seconds`
6. `max_attempts`
7. `message_expiry_seconds`
8. `allow_group_fallback`
9. `updated_at`

Purpose:

1. separate identity data from delivery behavior
2. let the orchestrator decide whether to wait, retry, or force fallback

### Preferred Language

Suggested schema addition:

1. add `preferred_language` to `user_profiles`

Purpose:

1. drive standard replies and later operator-generated assisted replies

### Pending Messages

Suggested table: `pending_messages`

Suggested fields:

1. `message_id`
2. `sender_user_id`
3. `target_user_id`
4. `conversation_scope`
5. `message_class`
6. `plaintext_body`
7. `body_summary`
8. `delivery_state`
9. `selected_route`
10. `fallback_route`
11. `created_at`
12. `next_attempt_after`
13. `fallback_after`
14. `expires_at`
15. `last_attempt_at`
16. `last_error_code`
17. `accepted_station_id`
18. `owning_station_id`
19. `claim_token`
20. `claim_station_id`
21. `claim_expires_at`
22. `claim_heartbeat_at`

Purpose:

1. persist accepted messages that cannot yet be delivered
2. support retries and fallback without depending on in-memory state
3. allow UI visibility without exposing content by default
4. support leased queue claims across multiple stations

Suggested handling notes:

1. `plaintext_body` exists for routing and later delivery, but it should not be returned in the normal queue-list API
2. `body_summary` may be blank in the first slice if even a short summary is considered too revealing
3. if `body_summary` is used later, it should be generated deliberately by policy, not copied from the start of the message body
4. claim fields should be nullable until a station leases the message for active delivery work

### Queue Claims

The multi-station checkout rule should use leases rather than permanent locks.

Recommended claim behavior:

1. an eligible station claims a queued message by writing `claim_station_id`, `claim_token`, and `claim_expires_at`
2. only the station holding the active lease may perform delivery attempts for that queue item
3. a station may renew the lease by updating `claim_heartbeat_at` and extending `claim_expires_at` while an attempt is genuinely in progress
4. successful terminal completion should move the message to `delivered`, `fallback_sent`, `expired`, or `cancelled` and clear it from active retry selection
5. retryable failures should clear or allow expiry of the lease and return the message to `waiting_for_path` with a new `next_attempt_after`
6. crashed or disconnected stations should lose their claim automatically when the lease expires

Recommended timing rule:

1. keep the first lease window short, such as 30 to 120 seconds, and renew only while real work is active

Recommended idempotency rule:

1. every delivery attempt should carry the stable `message_id` and active `claim_token` so duplicate or late completions can be detected safely

### Delivery Attempts

Suggested table: `delivery_attempts`

Suggested fields:

1. `attempt_id`
2. `message_id`
3. `attempted_at`
4. `station_id`
5. `route_name`
6. `outcome`
7. `outcome_detail`
8. `gateway_request_id`

Purpose:

1. provide auditable delivery history
2. support retry and fallback policy decisions
3. keep operator logs about state transitions instead of queued plaintext

### Reply Templates

Suggested table: `reply_templates`

Suggested fields:

1. `template_key`
2. `language_code`
3. `template_text`
4. `version`
5. `updated_at`

Initial template keys:

1. `registered`
2. `unknown_user`
3. `message_stored`
4. `fallback_sent`
5. `delivery_expired`

## Queue Visibility Rules

The user requirement is clear: stored messages should not be easy for basestation operators to read in the normal UI, but full encryption is not required in this slice.

That should be implemented as an API and UI rule set:

1. queue list endpoints return only metadata, never `plaintext_body`
2. the Messages or queue panel shows counts, state, age, route plan, and fallback timing, but not content
3. search and filter operations on the workbench should work on IDs, states, targets, stations, and timestamps, not on queued plaintext
4. audit rows should reference `message_id` and route outcomes rather than echoing the message body
5. any later operator-reveal workflow should be explicit, rare, and separately justified; it should not be built into the first routine workbench path

Important limitation:

1. this reduces casual exposure but does not secure the content from anyone with DB or host-level access

## Delivery Lifecycle

Recommended flow for directed private messages:

1. validate and classify inbound traffic
2. resolve sender and `target_user_id`
3. read the target user's delivery policy
4. evaluate current reachable routes in preferred order
5. if a valid route exists now, attempt immediate delivery
6. if no valid route exists, create a `pending_messages` row and record a `message_stored` reply if the ingress path supports it
7. on future presence updates, route-status changes, or retry windows, reevaluate queued messages for that user
8. if the hold window expires and fallback is enabled, attempt email delivery and record the result
9. if expiry is reached without successful delivery, mark the message expired and optionally send a sender-facing failure notice later if policy allows

### Gateway Edge Portability

The durable delivery model should be transport-agnostic above the gateway edge.

Working rule:

1. `pending_messages`, `delivery_attempts`, `delivery_policies`, and `user_presence` are common basestation concerns, not SMS-over-HTTP concerns
2. a gateway adapter may expose its own carrier-specific mechanics such as HTTP polling, USB serial exchange, local modem commands, or a future daemon protocol, but those are only the edge-delivery mechanism
3. the common orchestrator and queue logic should hand an adapter a delivery attempt and receive completion or retry outcome back, regardless of whether the phone is reached over HTTP, USB, Bluetooth, or some later transport
4. changing the phone link from Android HTTP callbacks to a USB-attached phone service should not require changing queue ownership, delivery states, lease rules, or policy evaluation
5. gateway-specific code may keep short-lived local buffers for immediate device interaction, but durable accepted work should live in the common delivery store rather than in gateway-specific in-memory queues

## Ownership And Sync Model

The main queue design question is ownership.

Recommended working answer:

1. authority DB owns the durable pending-message truth
2. field basestations publish useful facts upward such as presence, last seen, and provisional user evidence
3. field basestations may pull queue work relevant to their reachable users or local gateways
4. delivery attempts should use station claims or leases so two stations do not send the same queued message at once
5. station identity for claims should come from the separate basestation registry, not from ad hoc runtime labels

Without explicit ownership and claim rules, deferred delivery will become race-prone once more than one station can reach the same user.

## DB-First Implementation Plan

The next implementation should start with persistence and contracts, not UI.

### Step 1: Basestation Registry Schema

1. add the separate logical basestation-registry tables for stations, contacts, capabilities, and trust-material metadata
2. assign stable `station_id` values and require all station-facing queue or presence writes to use them
3. keep secret material fields present but unused if the first rollout is still non-encrypted

### Step 2: Authority Delivery Schema

1. add `user_presence`, `delivery_policies`, `pending_messages`, `delivery_attempts`, and `reply_templates`
2. add claim-lease fields to `pending_messages`
3. add `preferred_language` to `user_profiles`

### Step 3: Core APIs And Store Layer

1. implement CRUD and query operations for station registry data
2. implement queue-create, queue-claim, queue-renew, queue-complete, and queue-release operations
3. implement presence upsert operations keyed by `station_id`
4. implement reply-template lookup with deterministic fallback language
5. keep the store and orchestrator contracts independent from any one gateway carrier so adapter swaps such as HTTP-to-USB do not force a queue redesign

## Concrete Schema Draft

This section turns the earlier model into a first implementation draft with table ownership, primary keys, and likely indexes.

### Registry Database

Recommended database path family:

1. `EHN_BASESTATION_REGISTRY_DB_PATH`
2. default authority path: `var/authority/registry/ehn-basestation-registry.db`

Recommended tables:

1. `stations`
2. `station_contacts`
3. `station_capabilities`
4. `station_trust_material`
5. `station_audit_log`

Suggested `stations` columns:

1. `station_id TEXT PRIMARY KEY`
2. `station_name TEXT NOT NULL`
3. `station_role TEXT NOT NULL`
4. `owner_name TEXT NOT NULL DEFAULT ''`
5. `owner_org TEXT NOT NULL DEFAULT ''`
6. `deployment_status TEXT NOT NULL`
7. `location_label TEXT NOT NULL DEFAULT ''`
8. `location_lat REAL`
9. `location_lon REAL`
10. `notes TEXT NOT NULL DEFAULT ''`
11. `created_at TEXT NOT NULL`
12. `updated_at TEXT NOT NULL`

Suggested indexes:

1. `UNIQUE INDEX idx_stations_name ON stations(station_name)`
2. `INDEX idx_stations_role_status ON stations(station_role, deployment_status)`

Suggested `station_contacts` columns:

1. `contact_id TEXT PRIMARY KEY`
2. `station_id TEXT NOT NULL`
3. `contact_role TEXT NOT NULL`
4. `display_name TEXT NOT NULL`
5. `phone TEXT NOT NULL DEFAULT ''`
6. `email TEXT NOT NULL DEFAULT ''`
7. `preferred_contact_method TEXT NOT NULL DEFAULT ''`
8. `is_primary INTEGER NOT NULL DEFAULT 0`
9. `updated_at TEXT NOT NULL`

Suggested indexes:

1. `INDEX idx_station_contacts_station ON station_contacts(station_id)`
2. `INDEX idx_station_contacts_primary ON station_contacts(station_id, is_primary)`

Suggested `station_capabilities` columns:

1. `station_id TEXT PRIMARY KEY`
2. `supports_meshcore INTEGER NOT NULL DEFAULT 0`
3. `supports_sms_gateway INTEGER NOT NULL DEFAULT 0`
4. `supports_meshtastic INTEGER NOT NULL DEFAULT 0`
5. `supports_email_fallback INTEGER NOT NULL DEFAULT 0`
6. `supports_queue_claims INTEGER NOT NULL DEFAULT 0`
7. `supports_encrypted_sync INTEGER NOT NULL DEFAULT 0`
8. `last_verified_at TEXT`
9. `updated_at TEXT NOT NULL`

Suggested `station_trust_material` columns:

1. `trust_material_id TEXT PRIMARY KEY`
2. `station_id TEXT NOT NULL`
3. `key_purpose TEXT NOT NULL`
4. `key_identifier TEXT NOT NULL`
5. `public_material TEXT NOT NULL DEFAULT ''`
6. `encrypted_private_material TEXT NOT NULL DEFAULT ''`
7. `material_status TEXT NOT NULL`
8. `rotation_due_at TEXT`
9. `updated_at TEXT NOT NULL`

Suggested indexes:

1. `INDEX idx_station_trust_station ON station_trust_material(station_id)`
2. `UNIQUE INDEX idx_station_trust_key ON station_trust_material(station_id, key_purpose, key_identifier)`

Suggested `station_audit_log` columns:

1. `event_id TEXT PRIMARY KEY`
2. `event_ts TEXT NOT NULL`
3. `actor TEXT NOT NULL`
4. `action TEXT NOT NULL`
5. `station_id TEXT NOT NULL`
6. `summary TEXT NOT NULL`
7. `details_json TEXT NOT NULL`

### Authority Delivery Database

Recommended database path family:

1. reuse `EHN_BASESTATION_AUTHORITY_DIRECTORY_DB_PATH` for the first cut if fewer moving parts are needed
2. or introduce `EHN_BASESTATION_DELIVERY_DB_PATH`
3. default authority path if separated: `var/authority/delivery/ehn-delivery.db`

Recommended tables:

1. `station_profiles`
2. `user_presence`
3. `delivery_policies`
4. `pending_messages`
5. `delivery_attempts`
6. `reply_templates`

Suggested `station_profiles` columns:

1. `station_id TEXT PRIMARY KEY`
2. `runtime_status TEXT NOT NULL`
3. `last_reported_at TEXT NOT NULL`
4. `last_seen_ip TEXT NOT NULL DEFAULT ''`
5. `software_version TEXT NOT NULL DEFAULT ''`
6. `capabilities_json TEXT NOT NULL DEFAULT '{}'`
7. `health_summary TEXT NOT NULL DEFAULT ''`

Suggested `user_presence` columns:

1. `user_id TEXT PRIMARY KEY`
2. `last_seen_at TEXT NOT NULL`
3. `last_seen_station_id TEXT NOT NULL`
4. `last_seen_via_network TEXT NOT NULL`
5. `last_seen_endpoint_id TEXT NOT NULL DEFAULT ''`
6. `presence_state TEXT NOT NULL`
7. `presence_evidence TEXT NOT NULL`
8. `updated_at TEXT NOT NULL`

Suggested indexes:

1. `INDEX idx_user_presence_station ON user_presence(last_seen_station_id)`
2. `INDEX idx_user_presence_network ON user_presence(last_seen_via_network)`
3. `INDEX idx_user_presence_seen_at ON user_presence(last_seen_at)`

Suggested `delivery_policies` columns:

1. `user_id TEXT PRIMARY KEY`
2. `preferred_route_json TEXT NOT NULL DEFAULT '[]'`
3. `fallback_email_enabled INTEGER NOT NULL DEFAULT 0`
4. `fallback_hold_seconds INTEGER NOT NULL DEFAULT 0`
5. `retry_interval_seconds INTEGER NOT NULL DEFAULT 300`
6. `max_attempts INTEGER NOT NULL DEFAULT 10`
7. `message_expiry_seconds INTEGER NOT NULL DEFAULT 86400`
8. `allow_group_fallback INTEGER NOT NULL DEFAULT 0`
9. `updated_at TEXT NOT NULL`

Suggested `pending_messages` columns:

1. `message_id TEXT PRIMARY KEY`
2. `sender_user_id TEXT NOT NULL`
3. `target_user_id TEXT NOT NULL`
4. `conversation_scope TEXT NOT NULL`
5. `message_class TEXT NOT NULL`
6. `plaintext_body TEXT NOT NULL`
7. `body_summary TEXT NOT NULL DEFAULT ''`
8. `delivery_state TEXT NOT NULL`
9. `selected_route TEXT NOT NULL DEFAULT ''`
10. `fallback_route TEXT NOT NULL DEFAULT ''`
11. `created_at TEXT NOT NULL`
12. `next_attempt_after TEXT`
13. `fallback_after TEXT`
14. `expires_at TEXT`
15. `last_attempt_at TEXT`
16. `last_error_code TEXT NOT NULL DEFAULT ''`
17. `accepted_station_id TEXT NOT NULL`
18. `owning_station_id TEXT NOT NULL`
19. `claim_token TEXT NOT NULL DEFAULT ''`
20. `claim_station_id TEXT NOT NULL DEFAULT ''`
21. `claim_expires_at TEXT`
22. `claim_heartbeat_at TEXT`
23. `created_by_event_id TEXT NOT NULL DEFAULT ''`
24. `updated_at TEXT NOT NULL`

Suggested indexes:

1. `INDEX idx_pending_target_state ON pending_messages(target_user_id, delivery_state)`
2. `INDEX idx_pending_next_attempt ON pending_messages(next_attempt_after)`
3. `INDEX idx_pending_claim_expiry ON pending_messages(claim_expires_at)`
4. `INDEX idx_pending_owner_state ON pending_messages(owning_station_id, delivery_state)`
5. `INDEX idx_pending_created_at ON pending_messages(created_at)`

Suggested `delivery_attempts` columns:

1. `attempt_id TEXT PRIMARY KEY`
2. `message_id TEXT NOT NULL`
3. `claim_token TEXT NOT NULL DEFAULT ''`
4. `attempted_at TEXT NOT NULL`
5. `station_id TEXT NOT NULL`
6. `route_name TEXT NOT NULL`
7. `outcome TEXT NOT NULL`
8. `outcome_detail TEXT NOT NULL DEFAULT ''`
9. `gateway_request_id TEXT NOT NULL DEFAULT ''`
10. `updated_at TEXT NOT NULL`

Suggested indexes:

1. `INDEX idx_delivery_attempts_message ON delivery_attempts(message_id)`
2. `INDEX idx_delivery_attempts_station ON delivery_attempts(station_id)`
3. `INDEX idx_delivery_attempts_outcome ON delivery_attempts(outcome)`

Suggested `reply_templates` columns:

1. `template_key TEXT NOT NULL`
2. `language_code TEXT NOT NULL`
3. `template_text TEXT NOT NULL`
4. `version INTEGER NOT NULL DEFAULT 1`
5. `updated_at TEXT NOT NULL`
6. `PRIMARY KEY (template_key, language_code)`

## Store-Layer Mapping To Current Basestation Code

This is the concrete mapping from the current ehn-basestation code to the new DB-first structure.

### Keep As-Is With Extension

1. `DirectoryStore` remains the owner of user, identity, endpoint, and ordinary profile rows
2. `authority_server.py` remains the authority HTTP entry surface for user-directory administration
3. `BasestationSettings` remains the environment-backed path and station-identity source

### Add New Stores

1. add `StationRegistryStore` beside `directory_store.py`
2. add `DeliveryStore` beside `directory_store.py`
3. keep these stores separate rather than overloading `DirectoryStore` with queue, lease, trust, and station-registry concerns

Recommended implementation files in the sibling basestation repo:

1. `src/ehn_basestation/directory/station_registry_store.py`
2. `src/ehn_basestation/directory/delivery_store.py`
3. `src/ehn_basestation/core/reply_templates.py`

### Settings Additions

Recommended `BasestationSettings` additions:

1. `registry_db_path`
2. `delivery_db_path`
3. `station_id`

Recommended environment variable names:

1. `EHN_BASESTATION_STATION_ID`
2. `EHN_BASESTATION_REGISTRY_DB_PATH`
3. `EHN_BASESTATION_DELIVERY_DB_PATH`

Reasoning:

1. the current settings object already owns station name, role, and DB paths
2. adding stable `station_id` here gives the router, queue layer, and presence updates one shared identity source

### Authority Server Expansion

Recommended additions to the existing authority server layer:

1. keep current directory endpoints for user CRUD
2. add station-registry endpoints under `/api/authority/stations`
3. add delivery-admin endpoints under `/api/authority/delivery`
4. keep queue claim routes available for station services even if the first UI does not expose them

### Orchestrator Change Boundary

`DeliveryOrchestrator.send_directed_private()` is the first code path that should change.

Recommended behavior change:

1. keep ham plaintext gate first
2. attempt immediate delivery only when a currently valid route exists
3. if no valid route exists, create a queued message through `DeliveryStore`
4. return an `accepted_but_queued` style result instead of a generic failed send
5. record sender-facing reply work separately from queue creation

## API Contract Draft

The first API contract should be narrow and DB-first.

### Station Registry Admin

1. `GET /api/authority/stations`
2. `POST /api/authority/stations`
3. `GET /api/authority/stations/{station_id}`
4. `POST /api/authority/stations/{station_id}/contacts`
5. `POST /api/authority/stations/{station_id}/capabilities`

### Presence And Policy

1. `POST /api/authority/presence`
2. `GET /api/authority/presence/{user_id}`
3. `POST /api/authority/delivery/policies/{user_id}`
4. `GET /api/authority/delivery/policies/{user_id}`

### Queue Operations

1. `POST /api/authority/delivery/messages`
2. `GET /api/authority/delivery/messages`
3. `POST /api/authority/delivery/messages/{message_id}/claim`
4. `POST /api/authority/delivery/messages/{message_id}/renew`
5. `POST /api/authority/delivery/messages/{message_id}/complete`
6. `POST /api/authority/delivery/messages/{message_id}/release`

### Claim Request Contract

Suggested request body for claim:

```json
{
	"station_id": "station-nnj-01",
	"route_name": "meshcore",
	"claim_window_seconds": 60
}
```

Suggested successful response:

```json
{
	"ok": true,
	"message_id": "msg-abc123",
	"claim_token": "claim-7fd0",
	"claim_station_id": "station-nnj-01",
	"claim_expires_at": "2026-09-06T18:30:00Z",
	"delivery_state": "attempting"
}
```

### Renew Request Contract

Suggested request body:

```json
{
	"station_id": "station-nnj-01",
	"claim_token": "claim-7fd0",
	"claim_window_seconds": 60
}
```

### Complete Request Contract

Suggested request body:

```json
{
	"station_id": "station-nnj-01",
	"claim_token": "claim-7fd0",
	"outcome": "delivered",
	"route_name": "meshcore",
	"gateway_request_id": "gw-req-44",
	"outcome_detail": "accepted by mesh gateway"
}
```

Terminal outcomes for completion:

1. `delivered`
2. `fallback_sent`
3. `expired`
4. `cancelled`

### Release Request Contract

Suggested request body:

```json
{
	"station_id": "station-nnj-01",
	"claim_token": "claim-7fd0",
	"outcome": "retryable_failure",
	"route_name": "meshcore",
	"next_attempt_after": "2026-09-06T18:35:00Z",
	"outcome_detail": "target not currently reachable"
}
```

Release rules:

1. release should clear the active claim fields
2. release should append a `delivery_attempts` row
3. release should move the queue item back to `waiting_for_path` or another retryable state

### Queue List Response Contract

Normal operator queue lists should include:

1. `message_id`
2. `sender_user_id`
3. `target_user_id`
4. `delivery_state`
5. `selected_route`
6. `fallback_route`
7. `created_at`
8. `next_attempt_after`
9. `fallback_after`
10. `claim_station_id`
11. `claim_expires_at`
12. `last_attempt_at`
13. `last_error_code`

Normal operator queue lists should exclude:

1. `plaintext_body`
2. any implied preview snippet generated from `plaintext_body`
3. trust-material fields

### Step 4: Orchestrator Logic

1. split immediate send from queued acceptance
2. use the claim-lease model for multi-station retries
3. only remove queue items on terminal outcomes
4. record every attempt in `delivery_attempts`

### Step 5: UI After DB And API Stability

1. show station registry details in admin views only after the model is stable
2. show queue counts and states without queued plaintext
3. show claim owner, claim age, and fallback deadlines so operators can understand why a message is waiting

## Suggested Implementation Order

### Phase 0: Station Identity Foundation

1. create the separate basestation-registry store and stable `station_id` model
2. define how authority DB tables reference station rows
3. reserve future trust-material fields now so encryption later extends the model instead of replacing it

### Phase 1: Persistence

1. extend the authority schema with station profile, presence, delivery policy, pending message, delivery attempt, and reply-template support
2. add `preferred_language` to the user profile schema
3. add lease fields and queue-claim rules with timeout support
4. keep the current local DB changes minimal until queue ownership is settled

### Phase 2: Core Delivery Logic

1. split `accepted` from `delivered` in the orchestrator
2. add queue-write and retry-decision logic
3. make presence updates and route-health changes trigger retry eligibility
4. keep standard replies behind a small template resolver instead of hardcoded strings

### Phase 3: Background Workers

1. add a durable retry worker or scheduled pass that does not depend on the UI being open
2. add authority-to-field synchronization for queue work, station facts, and presence facts
3. add claim or lease handling for multi-station delivery attempts
4. add lease-expiry cleanup and orphaned-claim recovery

### Phase 4: Operator UI

1. add queue counts and queue-state summaries to the workbench
2. show per-user waiting-message counts and oldest pending age
3. keep message content hidden in normal list and detail views for queued items
4. expose policy and status clearly enough that operators can understand why a message is waiting without reading its body
5. keep basestation-registry admin surfaces separate from ordinary message operations

## Immediate Gaps

These are the immediate gaps between the current implementation and this plan.

1. the current event store is in memory only, so queued delivery would be lost on restart
2. the current directory schema has no station-profile, last-seen-station, delivery-policy, or preferred-language model
3. the current orchestrator attempts immediate delivery only and has no durable queue or retry worker
4. current standard replies are still hardcoded and not language-aware
5. current workbench and authority screens do not have an authenticated role model, so hidden-content behavior is convenience and privacy, not access control
6. there is no separate basestation-registry store yet for ownership, contacts, capabilities, or future trust material
7. there is no queue-claim or lease API yet, so multi-station retry behavior would currently race

## Immediate Risks

These risks should shape the first implementation decisions.

1. if queue ownership is not explicit, multiple basestations can race and duplicate delivery
2. if queued plaintext leaks into existing event logs, API payloads, or debug panels, the new privacy rule will fail despite the queue UI looking correct
3. if presence updates are weak or delayed, stored messages may wait too long even when a user is actually reachable
4. email fallback semantics are still underspecified for consent, allowed message classes, and bounce handling
5. sender acknowledgements are transport-dependent, so `message stored` cannot be guaranteed on every ingress path
6. MeshCore group inbound currently lacks strong per-sender identity in the available companion envelope, which limits how confidently some presence events can be attributed
7. plaintext at rest in SQLite is still readable to anyone with host or DB access; that is accepted for now, but it remains a real privacy boundary
8. stale duplicate Windows listeners can produce misleading validation results if the rollout is tested against the wrong running process
9. if basestation trust material is stored in the same casual access path as ordinary directory data, later encryption rollout will inherit avoidable exposure and migration pain

## First Concrete Outcome

The first usable milestone should be modest:

1. a separate basestation-registry store holds station ownership, contacts, capabilities, and future trust-material metadata
2. authority DB stores station profiles, presence, delivery policy, preferred language, and queued messages
3. queue items use a lease-based claim model for multi-station delivery attempts
4. immediate delivery still works where possible
5. otherwise the message is stored durably
6. sender gets `message stored` when possible
7. operators see queued-message existence, state, and age, but not content

That milestone would move the basestation from best-effort forwarding to a real store-and-forward model without violating the current thin-UI direction.