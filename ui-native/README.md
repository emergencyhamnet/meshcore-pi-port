# UI Native

This folder is the clean-start home for the new relocatable MeshCore UI.

Rules for this project:

1. use native MeshCore companion commands and replies as the only UI contract
2. do not depend on gateway-shaped JSON methods or Pi UI projection payloads
3. keep transport concerns isolated from screen composition and UI behavior
4. preserve a path to run the same UI in a browser during Windows development and on the Pi later
5. treat any temporary desktop harness as a development aid, not the product surface

Current scope:

1. reusable native companion client package
2. reusable native session broker for browser UI and future basestation-side native session ownership
2. native node-page read model built from donor-aligned replies
3. command-line entrypoint for local development, browser serving, and model inspection
4. temporary desktop harness for rapid workflow and behavior validation during development
5. browser UI with thin HTTP endpoints for the relocatable UI path

Architecture note:

`ui-native/src/meshcore_ui_native/native_session_broker.py` is now the shared native-backed session owner. It keeps the UI on native companion commands while giving future gateway-link work a reusable in-process broker instead of forcing secondary helper connections or UI-shaped RPCs.

Quick start from the repo root:

```powershell
$env:PYTHONPATH = "ui-native/src"
.\.venv\Scripts\python.exe -m meshcore_ui_native --host 192.168.1.219 --port 5040
Remove-Item Env:PYTHONPATH
```

Temporary desktop harness from the repo root after installing the optional UI dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install "PySide6>=6.8"
$env:PYTHONPATH = "ui-native/src"
.\.venv\Scripts\python.exe -m meshcore_ui_native --ui --host 127.0.0.1 --port 15040
Remove-Item Env:PYTHONPATH
```

Initial browser shell from the repo root:

```powershell
$env:PYTHONPATH = "ui-native/src"
.\.venv\Scripts\python.exe -m meshcore_ui_native --web --host 127.0.0.1 --port 15040 --listen-host 127.0.0.1 --listen-port 8099
Remove-Item Env:PYTHONPATH
```

Open `http://127.0.0.1:8099/` in a browser. The current browser UI serves Settings editing, contact direct-message history/send, active-channel history/send/edit/delete, an embedded Tools workspace, and SSE-backed live notices over the same native companion contract.

Current browser baseline:

1. stacked Settings editing with save and reboot actions
2. active channel list with per-channel history, send, edit, and delete flows
3. Contacts list with direct-message history and send actions
4. shared in-page menu and Tools workspace over the native companion session
5. SSE-backed live notices without front-end polling

Operational note: when validating through a local tunnel to the Pi companion bridge, keep one active local browser UI server attached to the tunnel at a time.

Tests from the repo root:

```powershell
.\.venv\Scripts\python.exe ui-native/tests/test_companion_client.py
.\.venv\Scripts\python.exe ui-native/tests/test_node_page_model.py
```

Future browser UI work should live in this folder and consume the native package instead of reaching back into `scripts/`.

Project handoff and architecture guardrails are captured in `docs/WINDOWS_UI_HANDOFF_2026-08-24.md`.