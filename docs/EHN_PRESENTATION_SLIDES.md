# EHN Presentation Slides

This document is a slide-ready outline for introducing the current EHN basestation model.

## Slide 1: Title

EHN: A Local-First Messaging And Routing Basestation

Core message bridging across mesh, SMS, and external sink endpoints.

## Slide 2: What EHN Is

EHN is a basestation platform that connects local mesh users, external messaging endpoints, and operator-controlled delivery policy.

It provides:

1. local identity and endpoint awareness
2. message classification and routing
3. durable storage of message events
4. delayed delivery when an endpoint is not immediately available
5. a consistent operating model across multiple transport types

## Slide 3: Design Principle

EHN is local-first.

The basestation continues to operate as an autonomous working system even when internet access is limited or unavailable.

The authority database strengthens identity and synchronization, but live field operation does not depend on a constant remote connection.

## Slide 4: Problem It Solves

Field communication often spans mixed conditions:

1. some users are on mesh only
2. some users are reachable only by SMS
3. some devices submit telemetry rather than human messages
4. some delivery targets are temporarily offline

EHN allows one basestation to accept, store, route, and retry those communications without turning each gateway into its own routing brain.

## Slide 5: Core System Model

EHN has four main roles:

1. basestation core: routing, policy, storage, queueing, operator visibility
2. gateway adapters: mesh, SMS, or other transport-specific edges
3. authority directory: stronger shared identity and endpoint truth
4. endpoint targets: users, groups, and sink destinations

Gateways stay thin. The basestation owns decisions.

## Slide 6: Message Types

EHN works with three operator-visible target types:

1. `@user-id` for direct person or device delivery
2. `&group-id` for shared group delivery
3. `#sink-id` for sensor or device submissions routed to configured endpoints

This presentation uses that simplified address grammar as the operating message model.

## Slide 7: What Happens To A Message

When EHN receives a valid `@`, `&`, or `#` message it treats acceptance, storage, and delivery as separate steps.

Flow:

1. validate and classify the message
2. resolve the addressed target and sender identity
3. store the message event locally or in the shared delivery store
4. attempt immediate delivery on an available route
5. if delivery is not possible, queue the message for retry

A message does not disappear simply because the next hop is unavailable.

## Slide 8: Registration And Identity

EHN keeps `user_id` as the canonical routing identity.

Addressing and routing are not based on transport-native sender strings as the long-term model.

Operationally:

1. the basestation checks its local data first
2. if the sender is not known locally, it can consult the authority directory
3. if the sender is found, the basestation copies enough data locally to keep operating
4. if valid traffic comes from an unknown sender, the basestation can create a provisional local record for review

This keeps the system resilient without making unreviewed traffic permanent authority truth.

## Slide 9: Direct Messaging

Direct messaging uses `@user-id`.

The basestation resolves that addressed user into the best available endpoint path, such as MeshCore, SMS, or another configured route.

If the preferred path is not available, the basestation stores the message and retries later according to delivery policy.

## Slide 10: Group Messaging

Group messaging uses `&group-id`.

The basestation treats that explicit group address as one shared conversation while delivering through the transports that are valid for the group members.

This allows one conversation to span:

1. local mesh users
2. SMS participants
3. remote operators or observers on other allowed endpoints

## Slide 11: Sensor And Device Messaging

Device-originated traffic uses `#sink-id`.

This allows sensors, student devices, or telemetry nodes to submit structured or plain-text reports into EHN without pretending that every destination is a human chat target.

The basestation validates the submission, stores it, and forwards it to one or more configured sinks.

This keeps machine submissions separate from both direct person messaging and shared group chat.

## Slide 12: Delivery And Queueing

EHN assumes that endpoint availability changes.

For that reason it keeps a durable delivery queue with states such as:

1. queued
2. waiting for path
3. attempting
4. delivered
5. fallback sent

This means temporary loss of service does not force message loss.

## Slide 13: Storage Model

EHN stores more than a live transport event.

It stores:

1. message acceptance state
2. sender and target context
3. delivery attempts and outcomes
4. queue state when delivery is deferred
5. operator-visible audit and review facts

Stored messages can therefore support recovery, retry, inspection, and later synchronization.

## Slide 14: Operational Flow

A typical end-to-end flow is:

1. a user or device sends a message addressed as `@user-id`, `&group-id`, or `#sink-id` into a gateway
2. the gateway passes the traffic to EHN
3. EHN classifies the traffic as direct, group, or sink-bound
4. EHN resolves local identity and route policy
5. EHN stores the event before or alongside delivery attempts
6. EHN delivers immediately where possible
7. EHN queues and retries undelivered work until a valid route becomes available

This keeps transport mechanics separate from routing and operational control.

## Slide 15: Why This Architecture Matters

This model gives three practical advantages:

1. autonomy: a station keeps working locally
2. clarity: routing logic lives in one place
3. portability: the same policy model works on Windows or Pi with different gateway adapters

It is a stable foundation for field operation, staged deployment, and future expansion.

## Slide 16: Use Case 1, MeshCore To SMS Direct Messaging

A hiker carries a MeshCore device in poor cellular coverage while family members remain reachable by SMS.

Flow:

1. the hiker sends a direct message addressed to `@user-id`
2. EHN resolves the family member's available endpoint
3. EHN delivers through the SMS gateway when the phone path is available
4. replies from SMS return through EHN and are delivered back onto MeshCore
5. if either endpoint is temporarily unavailable, EHN stores and queues the message for later delivery

Key point:

EHN allows a mesh user and an SMS user to communicate across different transport conditions without manual relay.

## Slide 17: Use Case 2, Mixed-Transport Group Messaging

A field team works partly inside cell coverage and partly outside it. Some members use mesh devices, some use ordinary mobile phones, and some colleagues participate remotely.

Flow:

1. a sender posts to `&group-id`
2. EHN treats the message as one shared conversation
3. mesh participants receive it through mesh transport
4. phone participants receive it through SMS
5. remote participants receive it through their allowed endpoints
6. if one path is temporarily unavailable, EHN stores and queues undelivered copies until the route is usable

Key point:

One operational conversation can continue across mixed devices, mixed coverage, and mixed transports.

## Slide 18: Use Case 3, School Environmental Monitoring Project

A school runs a distributed project in which students monitor their home environment and submit data through mesh-connected devices.

Flow:

1. each student device sends a submission addressed to `#sink-id`
2. EHN validates the message and stores it as a durable event
3. EHN resolves the sink into one or more configured destinations
4. one destination preserves the submission for local EHN records
5. another destination forwards the submission to a school display, mailbox, or HTTP collector
6. if the school endpoint is unavailable, EHN queues the submission and retries later

Key point:

EHN is not only a chat bridge. It is also a trusted intake, storage, and forwarding point for sensor and project data.

## Slide 19: Closing

EHN provides one basestation model for:

1. direct messaging across transport boundaries
2. group communication across mixed coverage conditions
3. sensor and device submissions to external sinks
4. durable storage and delayed delivery when routes are unavailable

The result is a practical, explainable platform for resilient local communication.
