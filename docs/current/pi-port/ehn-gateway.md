# EHN Basestation Gateway

**Status:** integration-mode scope and acceptance draft, 2026-10-25.

## Ownership Boundary

The Pi port owns the MeshCore node, radio, native companion session, node storage and
Pi-hosted UI. The EHN basestation owns EHN identities, directory policy, routing, queues and
delivery orchestration. The EHN-facing gateway link adapts between those owners; it does not
turn the Pi node into the EHN directory or delivery authority.

The current local deployment record uses a Pi-hosted browser service with a gateway link on
port `7463`, but the bind address, transmit gate, and owning service depend on the installed
revision. Older docs describe a separate gateway-link systemd service; newer layouts host the
listener through the browser UI's shared native-session broker. Inspect the exact unit and
listener before starting, stopping, or changing either service.

## Configuration And Safety

1. Configure the basestation's MeshCore gateway endpoint to the Pi gateway-link address and
   port for that same tested revision.
2. Use a distinct gateway ID and the intended Pi node identity; do not clone state from the
   existing on-air node to create another station.
3. Keep the gateway-link transmit permission explicit. The basestation write gate controls
   writes through that link; it does not necessarily disable sends from the Pi UI or native
   companion client.
4. Confirm which process owns the radio session and gateway port. Do not run the standalone
   USB MeshCore broker, a second Pi gateway-link service, or another native client against the
   same owner unless the release design explicitly supports it.
5. Bind services only to the intended trusted network. A private LAN is not authentication
   or encryption; do not expose the browser UI or gateway link directly to the public internet.
6. Plan restarts and recovery with queues and radio identity in mind. Local gateway acceptance
   is not proof of RF delivery or recipient receipt.

## EHN Acceptance Checklist

Run these after the [standalone checks](standalone.md), recording exact versions and results:

1. basestation connects to the intended Pi gateway link and reports the expected node identity
2. read-only status and contact/channel refresh work without a competing serial/session owner
3. configured transmit permission is reported honestly and rejected when disabled
4. one authorized direct-message receive and send path is checked end to end, with recipient
   evidence distinguished from local acceptance
5. group receive/send behavior is tested separately from direct traffic where enabled
6. restart and connection loss recover without starting a duplicate listener or radio owner
7. basestation and Pi UI control surfaces remain understandable and do not imply shared
   authority or identical send permissions

The EHN link is an additional mode, not a reason to weaken native MeshCore compatibility or
make the basestation mandatory for normal MeshCore node operation.