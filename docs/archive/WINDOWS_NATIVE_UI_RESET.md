# Windows Native UI Reset

This document resets the Windows UI direction to the intended MeshCore model.

## Goal

The new Windows UI must speak the native MeshCore companion API.

The same UI should work against any MeshCore node, including:

1. Pi runtime in app mode
2. Android node
3. any future node exposing the same native companion contract

Only the transport adapter may change between targets.

## Core Rule

The pipe is transport only.

It must not become:

1. a second application API
2. a Pi-specific projection layer
3. the place where UI semantics are defined

The Windows UI owns screen behavior, wording, defaults, validation, and workflows.

## Interface Split

This repo must keep three different surfaces distinct.

1. `127.0.0.1:5040` is the native MeshCore companion endpoint in app mode.
2. `tcp://<pi-host>:7463` is the basestation-facing gateway pipe.
3. `http://<pi-host>:8099` is the intended Pi-hosted browser UI for the new relocatable surface.

The new Windows UI is not allowed to treat `7463` as its product API unless that pipe is carrying native MeshCore command and reply semantics.

That means:

1. the Windows UI model must be derived from native MeshCore commands and replies
2. `7463` may be used as a carrier for the Windows UI only when it behaves as a thin native relay
3. browser-shaped methods such as synthetic snapshots or Pi-specific node projections are basestation compatibility behavior, not the Windows UI contract
4. the older `8088` management UI should be considered retired when the Pi-hosted browser UI on `8099` is installed

## Required Architecture

There are only three layers:

1. native MeshCore companion API
2. thin transport adapter
3. Windows UI

### Native MeshCore Companion API

The UI should read and write node state through the existing companion protocol and donor-aligned runtime behavior.

Primary examples:

1. `APP_START`
2. `DEVICE_QUERY`
3. `GET_DEVICE_TIME`
4. `GET_CONTACTS`
5. channel read operations
6. native write operations already supported by the runtime

Field meaning must come from the native contract, not from Pi-side browser helpers.

### Thin Transport Adapter

A transport adapter may be backed by:

1. TCP
2. BLE
3. USB serial
4. Android bridge
5. Pi localhost bridge

Its responsibilities are limited to:

1. connect
2. frame bytes
3. send requests
4. receive replies
5. handle reconnect and session lifecycle

It must not:

1. invent new UI-facing fields
2. merge multiple native calls into a synthetic browser payload
3. shell out to helper scripts on the hot read path
4. expose Pi-only gateway verbs as if they were product API

### Windows UI

The Windows UI must be self-contained.

It owns:

1. screen composition
2. capability wording
3. missing-data handling
4. optimistic or pessimistic save behavior
5. feature gating based on native capability data

If the UI needs a new concept, the first question is whether that concept already exists in the native API.

## What To Keep

Keep only the code that is genuinely transport or runtime-host facing.

Examples:

1. Pi runtime bring-up and service install
2. app-mode bridge on `127.0.0.1:5040`
3. transport framing and endpoint handling
4. runtime lifecycle protection needed to keep one live runtime healthy

## What To Stop Building

Do not continue growing the basestation-style gateway contract as the main UI API.

That means no more expansion of browser-shaped methods such as:

1. synthetic snapshot endpoints
2. Pi-specific node projection payloads
3. helper-derived device payloads on the normal polling path
4. custom gateway verbs created only for one screen workflow

## Reset Plan

### Phase 1

Freeze the current gateway-shaped UI API.

Do not add more feature methods to it except temporary maintenance needed to keep existing experiments running.

Treat the current JSON gateway-link contract on `7463` as basestation-facing compatibility behavior, not as the new Windows UI API.

### Phase 2

Define the exact native companion operations the Windows UI will use first.

Initial minimum surface:

1. session start and self info
2. device info
3. contacts
4. channels
5. messages and send actions
6. writable node settings already supported by the native runtime

This phase must also define the rules for fields that are not plain text values.

Examples:

1. fields with runtime-enforced min and max values
2. fields whose UI wording depends on capability rather than stored preference
3. fields that are readable but not writable on every target

### Phase 3

Build a Windows transport client that talks native companion frames directly.

The first Windows UI milestone should use that client instead of the gateway-shaped JSON API.

The client should separate three concerns:

1. transport session and framing
2. native command execution
3. UI-facing interpretation helpers kept on Windows

### Phase 4

Move UI behavior into Windows.

Examples:

1. GPS wording
2. TX power presentation
3. capability display
4. validation messages
5. screen refresh behavior

This includes all logic for:

1. choosing labels like `Not supported`
2. deciding when to disable controls
3. deciding when to show current, allowed, and requested values
4. handling partial or unavailable native data without collapsing the whole UI

### Phase 5

Reduce the Pi gateway to one of these roles only:

1. thin framed relay
2. temporary compatibility shim during migration
3. removable legacy path

The preferred end state is:

1. `7463` remains available for basestation integration
2. any Windows UI use of `7463` is limited to thin transport of native MeshCore semantics
3. the local Pi UI on `8088` can be started or stopped independently without affecting either the Windows UI or the basestation pipe

## Success Test

The reset is successful when the same Windows UI can connect to different MeshCore nodes with only a transport change.

Examples:

1. Pi app-mode runtime
2. Android node
3. future USB or BLE-connected node

If a feature works only because the Pi gateway invented a special method, the architecture is still wrong.

## Clean Start Implementation Plan

The clean start should be built in thin vertical slices.

### Slice 1: Native Session And Read Path

Deliver a Windows client that can:

1. connect to a MeshCore node over one transport adapter
2. perform `APP_START`
3. perform `DEVICE_QUERY`
4. perform contact and channel reads
5. surface raw native values without Pi-side projection

Success condition:

The first Windows screen can show raw node identity, radio settings, and device facts from native replies.

#### Slice 1 Native Command Set

The first Windows native client should implement this command set exactly.

1. `CMD_APP_START` (`0x01`)
2. `CMD_DEVICE_QUERY` (`0x16 0x03`)
3. `CMD_GET_DEVICE_TIME` (`0x05`)
4. `CMD_SET_DEVICE_TIME` (`0x06`)
5. `CMD_GET_CONTACTS` (`0x04`)
6. `CMD_GET_CHANNEL` (`0x1F`, repeated by slot)
7. `CMD_SYNC_NEXT_MESSAGE` (`0x0A`)
8. `CMD_GET_BATT_AND_STORAGE` (`0x14`)
9. `CMD_GET_CUSTOM_VARS` (`0x28`) where the target supports it

This set is enough to build the first useful Windows session without inventing a second API.

#### Required Response Handling

The first client must parse at least these native replies and notifications:

1. `PACKET_SELF_INFO` (`0x05`)
2. `PACKET_DEVICE_INFO` (`0x0D`)
3. `PACKET_CURRENT_TIME` (`0x09`)
4. `PACKET_CONTACT_START` (`0x02`)
5. `PACKET_CONTACT` (`0x03`)
6. `PACKET_CONTACT_END` (`0x04`)
7. `PACKET_CHANNEL_INFO` (`0x12`)
8. `PACKET_CHANNEL_MSG_RECV` (`0x08`) and `PACKET_CHANNEL_MSG_RECV_V3` (`0x11`)
9. `PACKET_CONTACT_MSG_RECV` (`0x07`) and `PACKET_CONTACT_MSG_RECV_V3` (`0x10`)
10. `PACKET_CHANNEL_DATA_RECV` (`0x1B`)
11. `PACKET_MESSAGES_WAITING` (`0x83`)
12. `PACKET_BATTERY` (`0x0C`)
13. `PACKET_CUSTOM_VARS` (`0x15`)
14. `PACKET_OK` (`0x00`)
15. `PACKET_ERROR` (`0x01`)

#### First Windows Read Model

The Windows client should derive the first screen model from native replies only.

Map the initial read model like this:

1. node identity, radio settings, TX power, max TX power, advert policy, telemetry modes, and node name from `PACKET_SELF_INFO`
2. firmware version, model, max contacts, max channels, BLE pin, client repeat, and path hash mode from `PACKET_DEVICE_INFO`
3. current device time from `PACKET_CURRENT_TIME`
4. contact list from the `PACKET_CONTACT_START` -> `PACKET_CONTACT` -> `PACKET_CONTACT_END` sequence
5. channel list from repeated `CMD_GET_CHANNEL` requests returning `PACKET_CHANNEL_INFO`
6. queued and incoming messages from `PACKET_*_MSG_RECV`, `PACKET_CHANNEL_DATA_RECV`, and `PACKET_MESSAGES_WAITING`
7. battery and storage from `PACKET_BATTERY`
8. target-specific capability hints from `PACKET_CUSTOM_VARS` when available

#### First Session Sequence

The first Windows session should use this startup order:

1. connect transport
2. send `CMD_APP_START`
3. send `CMD_DEVICE_QUERY`
4. send `CMD_SET_DEVICE_TIME`
5. optionally confirm with `CMD_GET_DEVICE_TIME`
6. send `CMD_GET_CONTACTS`
7. send `CMD_GET_CHANNEL` for each slot
8. send `CMD_GET_BATT_AND_STORAGE`
9. send `CMD_GET_CUSTOM_VARS` if supported by the target or protocol version in use
10. begin passive message handling and use `CMD_SYNC_NEXT_MESSAGE` when messages are queued

#### Slice 1 Interpretation Rules

Even on the first read-only slice, the Windows client must apply a few semantic rules deliberately.

1. preserve falsy native values exactly; do not use fallback chains that collapse `0`, `0.0`, or `false` into missing data
2. treat `PACKET_SELF_INFO` as the authority for current TX power and max TX power
3. treat `PACKET_DEVICE_INFO` as the authority for firmware and broad device capacity
4. treat `PACKET_CUSTOM_VARS` as a capability hint, not as a replacement for core node state
5. treat missing optional replies as partial data, not as session failure

#### Special Cases Required In Slice 1

These special cases must be built into the first command set design so later screens do not re-open protocol questions.

1. TX power
	Current value and maximum value come from `PACKET_SELF_INFO`.
	The later write path must respect the runtime-enforced range of `-9` through `MAX_LORA_TX_POWER`.

2. GPS
	GPS support must not be inferred from blank coordinates or blank prefs.
	If available, use `PACKET_CUSTOM_VARS` and native runtime facts as support hints.
	The UI must keep separate concepts for support, enablement, and current location.

3. Contacts iteration state
	`CMD_GET_CONTACTS` can return a busy/error condition if an iterator is already running.
	The Windows client must treat this as a recoverable protocol state, not as a fatal disconnect.

4. Message retrieval
	`PACKET_MESSAGES_WAITING` is only a signal.
	Actual message fetch still requires `CMD_SYNC_NEXT_MESSAGE` until `PACKET_NO_MORE_MSGS` is returned.

### Slice 2: Capability Model On Windows

Before adding editable controls, define a Windows-side capability model.

The model should distinguish:

1. value currently reported by the node
2. value range enforced by the runtime
3. whether the setting is writable on this target
4. whether the setting is supported at all

This model must come from native replies where possible and from explicit client rules only when the native contract does not carry the answer directly.

### Slice 3: First Writable Setting

Use TX power as the first write slice.

Requirements:

1. read current TX power from the native node reply
2. read maximum TX power from the native node reply
3. validate proposed values on Windows before send
4. send the native write command
5. refresh and confirm the resulting value from the node

UI behavior:

1. show current value
2. show max allowed value
3. reject out-of-range edits before send when the range is known
4. still show runtime rejection if the node refuses the value

Important rule:

The power limit is part of node capability and runtime behavior, not a UI constant.

### Slice 4: Special-Logic Fields

Handle fields like GPS as explicit semantic cases.

Requirements:

1. separate support from enablement
2. do not infer support from a blank stored value
3. allow wording such as `Not supported` when capability is absent
4. avoid presenting unsupported controls as editable settings

Examples:

1. GPS support may depend on build or hardware
2. `gps_enabled` may exist as a preference even when the target does not actually support GPS

Important rule:

A special field should still be modeled on Windows from native facts, not from Pi-side synthetic payloads.

### Slice 5: Partial-Failure Behavior

The new UI must not fail closed when one operation is unavailable.

Requirements:

1. load screens from the specific native data they need
2. isolate read failures to the affected panel or field
3. keep the rest of the session usable when one command fails
4. surface transport errors separately from capability or validation errors

### Slice 6: Transport Expansion

Once the first read and write slices work over one transport, add more transport adapters.

Examples:

1. Pi app-mode bridge
2. USB serial
3. BLE
4. Android bridge

Success condition:

The same Windows UI and Windows-side logic works unchanged while only the transport adapter changes.

## First Build Rules

To keep the restart clean, follow these rules from the first commit:

1. no browser-shaped gateway snapshot API
2. no Pi-side screen projection logic
3. no helper subprocesses on normal read paths
4. no UI constants for values that the node already reports natively
5. no special-case target logic above the transport adapter

## Current Implication

The current gateway-link and basestation projection work should be treated as temporary scaffolding, not the target product architecture.

The authoritative direction is:

1. native MeshCore API first
2. transport pipe second
3. UI logic in Windows