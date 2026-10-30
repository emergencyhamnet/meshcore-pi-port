# Windows UI Handoff 2026-08-24

This note is the quick restart point if the chat history disappears.

## Current Position

The new UI direction has been reset and clarified.

The intended product path is now:

1. build new UI code in `ui-native/`
2. make this the only new node UI being developed
3. keep it browser-based and relocatable
4. use native MeshCore companion commands and replies as the only UI contract
5. keep the UI pipe transport-only
6. avoid expanding the Pi-side pipe into a second application API

The old drift was building UI behavior on top of a gateway-shaped JSON contract and treating the existing Pi web UI as something to extend. That is no longer the intended architecture.

## Core Intent

The new relocatable browser UI must talk native MeshCore semantics.

That means:

1. field meaning comes from the companion protocol and donor runtime behavior
2. UI wording, validation, presentation, and workflow logic live in the new UI codebase
3. the UI must be relocatable between Windows development and Pi-hosted deployment without changing product behavior
4. the transport layer may carry bytes, frame requests, and reconnect sessions, but it must not define product behavior

If a future transport is needed for convenience, it must still behave like a thin carrier for native commands and replies.

## Pipe Rules

Keep these surfaces separate:

1. `127.0.0.1:5040` is the native MeshCore companion endpoint in app mode
2. `tcp://<pi-host>:7463` is the basestation-facing gateway pipe
3. `http://<pi-host>:8099` is the intended final Pi-hosted browser UI for this same relocatable surface

Important rule:

The new Windows UI must not treat `7463` as its product API unless that pipe is only relaying native MeshCore command and reply semantics.

Do not grow the UI pipe into any of these:

1. synthetic snapshot API
2. Pi-specific projection API
3. browser-shaped workflow verbs
4. helper-derived UI payloads on the normal read path

The UI pipe should stay simple.

Allowed responsibilities:

1. open a connection
2. frame bytes
3. send native commands
4. receive native replies
5. reconnect cleanly

Not allowed:

1. invent UI-facing fields
2. combine native calls into a custom product payload
3. move screen logic into the Pi transport layer
4. create a second stable API just for one Windows screen

## New Code Anchor

The clean-start relocatable UI code lives in `ui-native/`.

Current files of interest:

1. `ui-native/src/meshcore_ui_native/companion_client.py`
2. `ui-native/src/meshcore_ui_native/native_session_broker.py`
3. `ui-native/src/meshcore_ui_native/node_page_model.py`
4. `ui-native/src/meshcore_ui_native/cli.py`
5. `ui-native/src/meshcore_ui_native/web_app.py`
6. `ui-native/tests/test_companion_client.py`
7. `ui-native/tests/test_node_page_model.py`

This folder is now the correct place for future UI work.

New broker rule:

1. if the basestation-facing gateway link needs a persistent native session owner, reuse `ui-native/src/meshcore_ui_native/native_session_broker.py` or move that broker further downward into a shared native layer
2. do not push basestation behavior into the UI transport contract just to share state
3. do not reintroduce helper-script side channels that open a second companion session for normal reads

The `scripts/` native client remains useful as a probe and reference, but the new UI should not be built by layering more behavior onto older probe or gateway-link experiments.

The current PySide6 desktop app is a development harness for proving behavior quickly on Windows. It is not the intended product surface.

## What Has Been Validated

These points have been proven in the current workspace:

1. a clean `ui-native/` package exists and is self-contained
2. local tests for the new package pass
3. the package can connect from Windows to the live Pi native companion endpoint through an SSH tunnel
4. the native snapshot path returns real identity, battery, contacts, channels, and device information
5. a fixed-width channel-name parsing bug was found during live validation and corrected
6. public channel send and receive work in the current development UI harness
7. the current development UI harness keeps one persistent native session and can auto-drain `PACKET_MESSAGES_WAITING` notices into message history
8. the current development UI harness exposes real native tools for stats, live debug-log capture, and guarded reboot
9. the browser UI on `http://127.0.0.1:8099/` is now the canonical local preview surface
10. browser Contacts open into direct-message history/detail views and direct message TX/RX has been proven there
11. browser Channels support per-channel history/send plus edit and delete flows
12. the browser UI uses a persistent server-side session plus `/api/events` SSE instead of front-end polling for live notices

This means the native path is real and working.

## Practical Progress Checks

The most practical way to see progress is to use checks that prove the clean path still works without reintroducing a custom UI API.

Use this order:

1. run the `ui-native` unit tests to confirm the native client and model still behave as expected
2. run the CLI preview against a reachable native endpoint to confirm real node data still flows
3. only after a real browser UI screen exists, use that screen as the main visual progress check

Today, the fastest concrete checks are:

1. `python ui-native/tests/test_companion_client.py`
2. `python -m meshcore_ui_native --host 127.0.0.1 --port 15040` when an SSH tunnel is open to the Pi native companion port
3. `python ui-native/tests/test_node_page_model.py`
4. `python -m meshcore_ui_native --web --host 127.0.0.1 --port 15040 --listen-host 127.0.0.1 --listen-port 8099` followed by opening `http://127.0.0.1:8099/`

What progress should look like in practice:

1. more behavior appears under `ui-native/`, not under gateway-link helpers
2. new read and write flows are expressed in terms of native companion commands
3. the Windows side gains UI behavior without needing new Pi-side JSON methods

## Current Interface Position

There is now a canonical local browser preview URL for the clean-start architecture.

Current validated interfaces are:

1. CLI preview: `python -m meshcore_ui_native`
2. Windows-to-Pi tunnel example: `127.0.0.1:15040` forwarded to Pi localhost `5040`
3. Pi native companion endpoint: `127.0.0.1:5040` on the Pi side
4. canonical local browser preview: `http://127.0.0.1:8099/` via `python -m meshcore_ui_native --web`
5. temporary Windows desktop harness: `python -m meshcore_ui_native --ui`

Important distinction:

1. `http://127.0.0.1:18098` is the canonical Windows workbench port for the basestation preview and Android SMS gateway contract
2. `http://127.0.0.1:8099/` is now the correct local browser preview surface for the clean-start UI path
3. the clean-start path should converge on one new browser UI, not preserve multiple parallel UI products
4. the current desktop harness is temporary and should not be mistaken for the final deployment surface

## Current Ownership Snapshot

Confirmed live ownership on 2026-09-04:

1. `127.0.0.1:18098` is served by the sibling `d:\Projects\ehn-basestation` repo through `dev\windows\start-workbench-preview.ps1`, which must resolve one Python interpreter and an absolute `PYTHONPATH` to `d:\Projects\ehn-basestation\src`
2. the `18098` page content comes from `d:\Projects\ehn-basestation\ui\static\workbench-preview.html`, `workbench-preview.css`, and `workbench-preview.js`
3. `127.0.0.1:8105` is the separate authority directory console from the same `ehn-basestation` repo through `dev\windows\start-authority-console.ps1`, which must use `authority-station.env` and the same absolute-source import path
4. `http://<pi-host>:8099/` is the Pi-hosted MeshCore browser UI from this `meshcore-pi-port` repo, backed by `ui-native/src/meshcore_ui_native/web_app.py`
5. `tcp://<pi-host>:7463` is the basestation-facing MeshCore gateway link and should remain a transport seam, not the Windows product UI API
6. `127.0.0.1:5040` on the Pi is the native companion endpoint owned by the live runtime service

Practical consequence:

1. changes to the Windows workbench at `18098` must be made in `ehn-basestation`, not in `meshcore-pi-port`
2. changes to the Pi browser UI at `8099` belong in `ui-native/` in this repo
3. changes to the gateway transport on `7463` belong in the shared-broker or gateway-link path, not in the Windows workbench assets

## Restart And Recovery

Use these commands when the Windows workbench needs a clean restart:

```powershell
cd D:\Projects\ehn-basestation
$env:PYTHONPATH = 'D:\Projects\ehn-basestation\src'
d:/Projects/meshcore-pi-port/.venv/Scripts/python.exe -m ehn_basestation.app.cli --env-file .\dev\windows\env\local-station.env run-workbench-preview --host 0.0.0.0 --port 18098
```

Use this command for the authority-only console:

```powershell
cd D:\Projects\ehn-basestation
$env:PYTHONPATH = 'D:\Projects\ehn-basestation\src'
d:/Projects/meshcore-pi-port/.venv/Scripts/python.exe -m ehn_basestation.app.cli --env-file .\dev\windows\env\authority-station.env run-authority-console --root . --host 127.0.0.1 --port 8105
```

If `18098` or `8105` looks stale, contradictory, or partly updated:

1. check for duplicate Python listeners on the affected port before changing code
2. kill all old listeners for that port so only one process remains bound
3. restart one clean instance from `ehn-basestation` with the exact interpreter and env file above
4. then reload with a cache-busting query string

Repeatable cleanup command:

```powershell
cd D:\Projects\meshcore-pi-port
.\scripts\repair-windows-ehn-preview.ps1 -Mode status
.\scripts\repair-windows-ehn-preview.ps1 -Mode workbench -Restart
.\scripts\repair-windows-ehn-preview.ps1 -Mode authority -Restart
.\scripts\repair-windows-ehn-preview.ps1 -Mode both -Restart
```

Recommended habit when touching Windows basestation code:

1. before editing, run `scripts/repair-windows-ehn-preview.ps1 -Mode status` and note any extra listeners on `18098`, `18101`, `8105`, or old `8098`
2. after backend edits in `ehn-basestation`, run `scripts/repair-windows-ehn-preview.ps1 -Mode workbench -Restart`
3. after authority-console edits, run `scripts/repair-windows-ehn-preview.ps1 -Mode authority -Restart`
4. if both surfaces were touched or behavior looks mixed, run `scripts/repair-windows-ehn-preview.ps1 -Mode both -Restart`
5. treat `18101` as a temporary comparison port only; the cleanup script clears it when returning to the canonical `18098` workflow

What the cleanup script does:

1. inspects the known preview ports and reports listener PIDs plus command lines
2. stops listeners only on the known Windows preview ports
3. clears Python `__pycache__` directories under `d:\Projects\ehn-basestation\src`
4. restarts the canonical workbench and or authority process with the shared venv interpreter, absolute `PYTHONPATH`, `-B`, and the correct env file

Port policy note:

1. `18098` is intentionally offset from the common local preview range so the Windows workbench is less likely to collide with ad hoc browser tools or stale localhost previews
2. the Android SMS gateway app should use `http://<windows-host>:18098` as its base URL after this change

Authority delete incident lessons from 2026-09-04:

1. Windows allowed three separate Python processes to listen on `127.0.0.1:8105` at the same time
2. that produced mixed behavior where the browser loaded current `authority-console.js` but some HTTP requests hit older handlers
3. the symptom was `POST /api/authority/users/<id>/delete` returning `404` and fallback `DELETE` returning `501`
4. the fix was not another UI change; it was clearing all duplicate `8105` listeners and restarting one clean authority process
5. after the cleanup, the authority console showed `Users 8` and an audit event `delete_authority_user` for `Authority Test User`, which is the expected known-good reference state

Operational caveat:

1. keep one active local browser UI server attached to the `15040 -> 5040` tunnel at a time, because the current Pi companion bridge effectively serves one external client session

## What Is Disposable Or Secondary

The following work is not the target architecture for the new Windows UI:

1. `scripts/gateway_link_client.py`
2. `scripts/windows_node_page.py`
3. `scripts/run-node-page-preview.py`
4. directed-private preview code that depends on the current gateway-link JSON contract

That work may still be useful for basestation compatibility, probing, or temporary migration checks, but it should not pull the new UI back toward a custom Pi API.

## Live Environment Facts

Known current environment:

1. live Pi host: `192.168.1.219`
2. SSH alias: `meshcorebasestation`
3. native companion service listens on Pi localhost by default
4. `5040` is available on the Pi localhost side and was reached from Windows through SSH tunneling
5. `7463` is active for the basestation-facing gateway pipe and should be left alone for UI simplification
6. the older `8088` management UI should be retired when the Pi-hosted browser UI on `8099` is installed

## Guidance On `8081`

Do not treat `http://192.168.1.219:8081/` as part of the new UI path.

Current recommendation:

1. do not extend it for Windows UI work
2. do not rely on it as the product interface for the clean-start UI
3. keep it running only if it is still useful for basestation work, compatibility checks, or diagnostics

So the default answer is: do not disable it just because the Windows UI is being reset.

Disable or stop it only if one of these is true:

1. it is causing confusion during development
2. it is consuming resources you need back on the Pi
3. you want to enforce discipline by removing an easy path back to the wrong interface

If it stays up, treat it as separate infrastructure, not as the feed for the new UI.

## Recommended Next Steps

Resume from here in this order:

1. keep new UI work inside `ui-native/`
2. treat the current desktop app as a temporary behavior harness, not the destination
3. keep the browser UI on `8099` as the baseline validation surface
4. keep adding carefully chosen native write flows only through that contract
5. move the same browser UI onto the Pi only after the local Windows browser baseline is considered stable
6. if remote access is needed, expose a dedicated UI-facing native pipe as a thin relay or direct companion listener, without changing the role of `7463`

## Pi Relocation Scope

Moving the browser UI to its final home on the Pi should not require a different product API.

What is involved:

1. install the `ui-native/` package and Python runtime dependencies on the Pi
2. run `python -m meshcore_ui_native --web` locally on the Pi against the native companion endpoint at `127.0.0.1:5040`
3. choose the serving model: direct bind on a Pi-local port or reverse-proxy it behind an existing local web server
4. create a persistent service unit so the browser UI restarts cleanly and does not depend on a terminal session
5. preserve the current thin-contract rule: the Pi-hosted browser UI may move location, but it must still talk native companion semantics rather than a new helper API
6. validate that the single-session behavior of the current companion bridge is still acceptable when the UI runs co-located on the Pi

What should not be required:

1. a new Pi-side JSON product API
2. a rewrite of the browser UI workflows
3. a separate Windows-only and Pi-only UI split

## Agreed UI Direction

The intended layout direction is closer to the published MeshCore UI shape, but still powered by the native companion contract.

The published web UI should now be treated as the primary requirements reference for layout and workflow shape.

Reference sources:

1. `D:\Projects\meshcore-pi-port-clean\ui\static\index.html`
2. `D:\Projects\meshcore-pi-port-clean\ui\static\app.js`
3. `D:\Projects\meshcore-pi-port-clean\ui\pi_node_ui_server.py`

Use those files for:

1. screen grouping
2. operator workflow expectations
3. wording and emphasis
4. which surfaces deserve first-class UI treatment

Do not use those files as permission to copy the old browser transport contract.

The split stays:

1. published web UI shape is the UX requirements source
2. native companion protocol is the data and command source
3. `ui-native/` is the implementation home for the new relocatable browser UI

Current agreed structure:

1. a `Settings` tab with sections for public info, radio settings, network settings, other settings, extra tools, and device info
2. a `Contacts` tab for contact browsing, direct/private conversation history, and direct send
3. a `Channels` tab where selecting a specific channel leads to viewing and sending messages on that channel, with live queue-drain updates folded into the conversation view
4. a `Map` tab if native location data proves useful enough to justify it

Important rule:

This is a layout and workflow decision, not permission to move message semantics or settings semantics into a custom Pi-side API.

## Published UI Requirements Extract

From the recovered published web UI, the key product expectations are:

1. a strong top-level status area for runtime health and refresh state
2. a settings-oriented node area covering profile, radio, and runtime-related facts
3. first-class contacts visibility with recent adverts and location hints
4. first-class messaging workflows, including public channel activity and send flows
5. first-class channels visibility as named provisioned groups
6. first-class logs or maintenance visibility for operator confidence

When translating that into the new UI:

1. keep the same workflow intent where it is useful
2. prefer tabs or panes over one long page when that improves usability in both desktop-browser development and Pi-hosted deployment
3. continue deriving all state from native MeshCore semantics rather than Pi helper payloads

## Reserved Meaning Of Extra Tools

`Extra Tools` is expected to become a maintenance and operations area.

Planned examples include:

1. import
2. export
3. purge data
4. debug logs
5. reboot and similar maintenance actions

Current implemented native Tools actions are:

1. stats refresh using `CMD_GET_STATS`
2. live debug-log display from `PACKET_LOG_DATA`
3. guarded reboot using `CMD_REBOOT`

Those tools should remain explicitly separate from normal settings sections so the main configuration UI stays understandable.

## Pi Bring-Up Lessons

The Pi-hosted browser UI and runtime path are now proven, and the build/debug path taught a few specific lessons worth preserving.

Important operational lessons:

1. copying updated source files to the Pi is not enough when the live runtime depends on `bin/pi-live-runtime`; the clock fix did not become real until that binary was rebuilt successfully
2. reinstalling or restarting `meshcore-pi-live-runtime.service` only changes behavior if the rebuild actually produced a fresh runtime binary
3. checking the timestamp of `bin/pi-live-runtime` on the Pi is a cheap sanity check; when the file still showed the old June timestamp, the service was still effectively on old runtime code
4. the live app-mode service launches a Python wrapper plus a `pi-live-runtime` child process; both should be visible when the runtime is healthy
5. the Pi runtime build exposed missing compatibility shims in this repo, not just deployment issues

Specific code learned from the rebuild:

1. `main/pi_donor_host_contracts.h` needed `../platform/pi_board.h` so `BoardProfile` and `RadioPathMode` resolve during the Pi live-runtime build
2. the Pi shim layer needed more Arduino-compatible `Stream` support, including `printf()`, `print(char)`, `println(char)`, and default `available()`, `peek()`, and `flush()` methods
3. the Pi shim layer also needed more Arduino-compatible `File` support, including `available()`, `peek()`, `flush()`, `isDirectory()`, `name()`, `size()`, `openNextFile()`, and `rewindDirectory()`
4. the active clock fix remains in `main/pi_donor_host_contracts.cpp`: `set_current_time()` stores a system-time offset and `get_current_time()` returns `system_time + offset`, so time continues advancing after sync

What has now been proven on the Pi:

1. `meshcore-pi-browser-ui.service` runs the `ui-native` browser UI on `0.0.0.0:8099`
2. `meshcore-pi-live-runtime.service` serves the native companion endpoint used by that UI
3. after the runtime rebuild succeeded, device time started advancing on each refresh instead of freezing at the last set value
4. `8081` is not the old MeshCore node-management UI; it belongs to `/home/n2dh/meshtastic-basestation/app.py` and should be treated as separate basestation infrastructure

## MeshCore UI Change List

This is the practical list of user-visible MeshCore browser UI changes now in place.

Implemented and validated:

1. browser-only MeshCore UI under `ui-native/`, with `http://127.0.0.1:8099/` as the canonical preview and `http://<pi-host>:8099/` as the Pi-hosted target
2. published-style top-level layout with `Settings`, `Contacts`, `Adverts`, `Channels`, `Map`, and `Tools`
3. persistent browser session broker with SSE live updates instead of front-end polling
4. direct contact conversations: contact list, click-through detail view, message history, send, and clear-history flow
5. active channel list with click-through channel conversations, send, edit, and delete flows
6. advert controls for zero-hop send, flood send, and advert-to-clipboard
7. recent adverts surfaced in their own tab with live event visibility and contact metadata refresh
8. settings editing for the agreed native-backed fields, including working `Use PC UTC now`
9. operator tools for native stats, debug-log visibility, and guarded reboot
10. Pi-hosted deployment path with `meshcore-pi-browser-ui.service`

Near-term UI follow-up list when work returns to MeshCore UI:

1. re-check advert timing behavior on adjacent nodes now that Pi runtime time is advancing correctly
2. confirm longer-duration clock stability, not just immediate refresh advancement
3. review whether any Tools actions should move from useful minimum to fuller maintenance coverage without expanding the native contract
4. keep cleanup focused on removing temporary test/probe leftovers, not on changing the browser contract shape
5. plan a move of the Pi host to a 64-bit OS as an operational follow-up item
6. add an explicit `share position in advert` option to the MeshCore browser UI, because that control is currently absent

## Restart Commands

From the repo root, run package tests:

```powershell
$env:PYTHONPATH = "ui-native/src"
.\.venv\Scripts\python.exe -m unittest discover ui-native/tests
Remove-Item Env:PYTHONPATH
```

To run the current CLI preview against a reachable native companion endpoint:

```powershell
$env:PYTHONPATH = "ui-native/src"
.\.venv\Scripts\python.exe -m meshcore_ui_native --host 127.0.0.1 --port 15040
Remove-Item Env:PYTHONPATH
```

That `15040` example assumes an SSH tunnel like this:

```powershell
ssh -L 15040:127.0.0.1:5040 meshcorebasestation -N
```

## One Sentence Summary

Use new code in `ui-native/`, build one relocatable browser UI over a thin native command pipe, and do not let the implementation drift back into depending on a custom Pi-side JSON API.