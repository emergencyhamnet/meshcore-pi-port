from __future__ import annotations

from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any
from urllib.parse import parse_qs, unquote_plus, urlparse

from .companion_client import (
  CompanionDeviceError,
  CompanionProtocolError,
)
from .gateway_link_server import GatewayLinkConfig, GatewayLinkServer
from .native_session_broker import NativeSessionBroker


HTML_PAGE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>MeshCore UI</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f3efe6;
      --panel: #fffaf2;
      --surface: #ffffff;
      --ink: #1d2a33;
      --muted: #6b7a86;
      --line: #d8ccba;
      --accent: #0c6d62;
      --accent-strong: #094d46;
      --accent-2: #b24c2c;
      --chip: #e6f0ed;
      --shadow: rgba(35, 36, 38, 0.06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: linear-gradient(180deg, #efe7d9 0%, var(--bg) 100%);
      color: var(--ink);
    }
    header {
      padding: 20px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 250, 242, 0.94);
      position: sticky;
      top: 0;
      backdrop-filter: blur(8px);
      z-index: 2;
    }
    h1 { margin: 0 0 8px; font-size: 28px; }
    h2 { margin: 0 0 8px; }
    h3 { margin: 0 0 10px; font-size: 16px; }
    .sub { color: var(--muted); font-size: 14px; }
    .toolbar, .row, .tabbar, .settings-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    .toolbar, .tabbar { margin-top: 16px; }
    .toolbar {
      justify-content: space-between;
    }
    .toolbar-main {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    button, input, select, textarea {
      font: inherit;
      border-radius: 10px;
      border: 1px solid var(--line);
      padding: 10px 12px;
      background: var(--surface);
      color: var(--ink);
    }
    button {
      cursor: pointer;
      min-height: 42px;
    }
    button.primary {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    button.primary:hover { background: var(--accent-strong); }
    button.warn {
      background: var(--accent-2);
      color: #fff;
      border-color: var(--accent-2);
    }
    button.active { background: var(--ink); color: #fff; border-color: var(--ink); }
    button.linklike {
      width: 100%;
      text-align: left;
      background: var(--surface);
    }
    input, select, textarea { width: 100%; }
    textarea {
      min-height: 120px;
      resize: vertical;
    }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 20px;
      display: grid;
      gap: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 8px 24px var(--shadow);
    }
    .settings-shell { display: grid; gap: 18px; }
    .settings-actions {
      justify-content: space-between;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }
    .section-card {
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
    }
    .field { display: grid; gap: 6px; margin-bottom: 14px; }
    .field label, .hint, .meta { font-size: 13px; color: var(--muted); }
    .mono { font-family: Consolas, "Courier New", monospace; word-break: break-all; }
    .kv { display: grid; grid-template-columns: 180px 1fr; gap: 8px 14px; }
    .kv div:nth-child(odd) { color: var(--muted); }
    .list { display: grid; gap: 10px; }
    .item {
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface);
    }
    .item strong { display: block; margin-bottom: 4px; }
    .chip {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: var(--chip);
      color: var(--accent);
      font-size: 12px;
      margin-right: 8px;
    }
    .status {
      padding: 10px 12px;
      border-radius: 12px;
      background: #fff;
      border: 1px solid var(--line);
      color: var(--muted);
      min-height: 44px;
      min-width: min(100%, 420px);
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
    }
    .status-pill.warn {
      background: #fff2df;
      border-color: #e4bf86;
      color: #8a5a00;
    }
    .status-pill.ok {
      background: #e6f0ed;
      border-color: #b6d3cb;
      color: var(--accent);
    }
    .hidden { display: none; }
    .messages {
      display: grid;
      gap: 10px;
      min-height: 220px;
      align-content: start;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.6);
    }
    .message {
      max-width: min(720px, 100%);
      padding: 10px 12px;
      border-radius: 14px;
      background: #fff;
      border: 1px solid var(--line);
    }
    .message.outgoing {
      margin-left: auto;
      background: #e8f4f1;
      border-color: #b6d3cb;
    }
    .message .meta { margin-top: 6px; }
    .empty-state {
      padding: 18px;
      border: 1px dashed var(--line);
      border-radius: 12px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.35);
    }
    .heading-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 12px;
    }
    .subtle-divider {
      height: 1px;
      background: var(--line);
      margin: 4px 0;
    }
    .menu-shell {
      position: relative;
    }
    .shared-menu-shell {
      margin-left: auto;
    }
    .menu-panel {
      position: absolute;
      right: 0;
      top: calc(100% + 8px);
      min-width: 220px;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface);
      box-shadow: 0 12px 30px var(--shadow);
      display: grid;
      gap: 8px;
      z-index: 3;
    }
    .menu-panel.hidden {
      display: none;
    }
    .menu-panel button {
      width: 100%;
      text-align: left;
      min-height: 38px;
    }
    .menu-title {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      padding: 4px 6px 0;
    }
    .menu-subhint {
      font-size: 12px;
      color: var(--muted);
      padding: 0 6px 6px;
    }
    .menu-back {
      border-bottom: 1px solid var(--line);
      border-radius: 8px;
      margin-bottom: 4px;
      padding-bottom: 10px;
    }
    .action-workspace {
      display: block;
      width: 100%;
      padding: 0;
      background: transparent;
      backdrop-filter: none;
      margin-top: 18px;
    }
    .action-workspace.hidden {
      display: none;
    }
    .action-card {
      width: 100%;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 8px 24px var(--shadow);
      padding: 18px;
      display: grid;
      gap: 14px;
    }
    .action-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }
    .action-view {
      display: grid;
      gap: 14px;
    }
    .action-view.hidden {
      display: none;
    }
    .action-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .action-error {
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid #d6a38f;
      background: #fff1ec;
      color: #8c2b10;
    }
    .readonly-box {
      width: 100%;
      min-height: 110px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fff;
      padding: 12px;
    }
    .tool-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }
    .tool-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.78);
      padding: 14px;
      display: grid;
      gap: 6px;
    }
    .tool-card strong {
      font-size: 22px;
      line-height: 1.1;
    }
    .tool-card.active {
      border-color: var(--accent);
      box-shadow: inset 0 0 0 1px var(--accent);
    }
    .tool-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .tool-sections {
      display: grid;
      gap: 14px;
    }
    .tool-section {
      display: grid;
      gap: 12px;
    }
    @media (max-width: 760px) {
      .kv { grid-template-columns: 1fr; }
      .settings-actions { justify-content: flex-start; }
      .heading-row { align-items: flex-start; }
      .shared-menu-shell { margin-left: 0; }
      .action-header { align-items: flex-start; }
      .action-actions { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <header>
    <h1>MeshCore UI</h1>
    <div class=\"sub\">Browser shell over the same thin native companion contract.</div>
    <div class=\"toolbar\">
      <div class=\"toolbar-main\">
        <button id=\"refresh\" class=\"primary\">Refresh</button>
        <span id=\"status\" class=\"status\">Loading node state...</span>
        <span id="gateway-status" class="status-pill">Gateway status loading...</span>
      </div>
      <div id=\"shared-menu-shell\" class=\"menu-shell shared-menu-shell hidden\">
        <button id=\"shared-advert-toggle\">Advert</button>
        <div id=\"shared-advert-root\" class=\"menu-panel hidden\">
          <button class=\"shared-advert-action\" data-action=\"advert-zero-hop\">Advert Zero Hop</button>
          <button class=\"shared-advert-action\" data-action=\"advert-flood\">Advert Flood</button>
          <button class=\"shared-advert-action\" data-action=\"advert-copy\">Advert To Clipboard</button>
        </div>
        <button id=\"shared-menu-toggle\">Menu</button>
        <div id=\"shared-menu-root\" class=\"menu-panel hidden\">
          <button class=\"shared-menu-nav\" data-menu-view=\"add-contact-menu\">Add Contact</button>
          <button class=\"shared-menu-nav\" data-menu-view=\"add-channel-menu\">Add Channel</button>
          <button class=\"shared-menu-action\" data-action=\"discover-contacts\">Discover Contacts</button>
          <button class=\"shared-menu-action\" data-action=\"contact-code\">My Contact Code</button>
          <button class=\"shared-menu-action\" data-action=\"internet-map\">Internet Map</button>
          <button class=\"shared-menu-nav\" data-menu-view=\"tools-menu\">Tools</button>
          <button class=\"shared-menu-action\" data-action=\"about\">About MeshCore</button>
        </div>
        <div id=\"add-contact-menu\" class=\"menu-panel hidden\">
          <button class=\"shared-menu-back menu-back\" data-menu-view=\"shared-menu-root\">Back</button>
          <div class=\"menu-title\">Add Contact</div>
          <div class=\"menu-subhint\">Choose how to add the contact.</div>
          <button class=\"shared-menu-action\" data-action=\"contact-import\">Import Contact Code</button>
          <button class=\"shared-menu-action\" data-action=\"contact-manual\">Manual Contact</button>
        </div>
        <div id=\"add-channel-menu\" class=\"menu-panel hidden\">
          <button class=\"shared-menu-back menu-back\" data-menu-view=\"shared-menu-root\">Back</button>
          <div class=\"menu-title\">Add Channel</div>
          <div class=\"menu-subhint\">Published-style channel actions.</div>
          <button class=\"shared-menu-action\" data-action=\"create-channel\">Create Channel</button>
          <button class=\"shared-menu-action\" data-action=\"join-private-channel\">Join Private Channel</button>
        </div>
        <div id="tools-menu" class="menu-panel hidden\">
          <button class="shared-menu-back menu-back" data-menu-view="shared-menu-root">Back</button>
          <div class="menu-title">Tools</div>
          <div class="menu-subhint">Current native-backed tools and diagnostics.</div>
          <button class="shared-menu-action" data-action="tool-overview">Node Overview</button>
          <button class="shared-menu-action" data-action="tool-radio">Radio Stats</button>
          <button class="shared-menu-action" data-action="tool-packets">Packet Stats</button>
          <button class="shared-menu-action" data-action="refresh">Refresh Node State</button>
          <button class="shared-menu-action" data-action="reboot">Reboot Device</button>
        </div>
      </div>
    </div>
    <div class=\"tabbar\">
      <button class=\"tab active\" data-tab=\"settings\">Settings</button>
      <button class=\"tab\" data-tab=\"contacts\">Contacts</button>
      <button class=\"tab\" data-tab=\"adverts\">Adverts</button>
      <button class=\"tab\" data-tab=\"channels\">Channels</button>
      <button class=\"tab\" data-tab=\"map\">Map</button>
    </div>
  </header>
  <main>
    <section id=\"settings\" class=\"tab-panel\">
      <div class=\"panel settings-shell\">
        <div class=\"settings-actions\">
          <div>
            <h2>Settings</h2>
            <div class=\"hint\">All settings are stacked in one page. Use Save all settings to apply the edited values.</div>
          </div>
          <div class=\"row\">
            <button id=\"save-settings\" class=\"primary\">Save all settings</button>
            <button id=\"reboot-device\" class=\"warn\">Reboot device</button>
          </div>
        </div>

        <div class=\"section-card\">
          <h3>Public Info</h3>
          <div class=\"field\">
            <label for=\"node-name\">Name</label>
            <input id=\"node-name\" type=\"text\">
          </div>
          <div class=\"field\">
            <label for=\"device-time\">Device time (UTC)</label>
            <div class=\"row\">
              <input id=\"device-time\" type=\"text\" placeholder=\"YYYY-MM-DD HH:MM:SS\">
              <button id=\"use-now\">Use PC UTC now</button>
            </div>
          </div>
          <div class=\"field\">
            <label>Advert location</label>
            <div class=\"row\">
              <input id=\"advert-lat\" type=\"text\" placeholder=\"Latitude\">
              <input id=\"advert-lon\" type=\"text\" placeholder=\"Longitude\">
            </div>
          </div>
          <div class=\"kv\">
            <div>Public key</div><div id=\"public-key\" class=\"mono\">-</div>
            <div>Current scope location</div><div id=\"scope-location\">-</div>
            <div>Custom vars</div><div id=\"custom-vars\">-</div>
          </div>
        </div>

        <div class=\"section-card\">
          <h3>Radio Settings</h3>
          <div class=\"field\">
            <label for=\"radio-preset\">Preset</label>
            <select id=\"radio-preset\"></select>
          </div>
          <div class=\"field\">
            <label for=\"tx-power\">TX power</label>
            <input id=\"tx-power\" type=\"number\" step=\"1\">
          </div>
          <div class=\"field\">
            <label><input id=\"repeat-mode\" type=\"checkbox\"> Enable repeat mode</label>
          </div>
          <div class=\"kv\">
            <div>Max TX</div><div id=\"max-tx\">-</div>
            <div>Frequency</div><div id=\"frequency\">-</div>
            <div>Current</div><div id=\"radio-current\">-</div>
            <div>Note</div><div id=\"radio-note\">Presets keep the current frequency and change only bandwidth, SF, and CR.</div>
          </div>
        </div>

        <div class=\"section-card\">
          <h3>Network Settings</h3>
          <div class=\"kv\" id=\"network-settings\"></div>
        </div>

        <div class=\"section-card\">
          <h3>Other Settings</h3>
          <div class=\"kv\" id=\"other-settings\"></div>
        </div>

        <div id=\"gateway-access-card\" class=\"section-card hidden\">
          <h3>Gateway Access</h3>
          <div class=\"hint\">Controls the embedded basestation gateway listener hosted by this browser UI process.</div>
          <div class=\"field\">
            <label><input id=\"gateway-allow-tx\" type=\"checkbox\"> Allow basestation transmit through gateway link</label>
          </div>
          <div class=\"row\">
            <button id=\"save-gateway-access\">Apply gateway access</button>
          </div>
          <div class=\"kv\" id=\"gateway-access-settings\"></div>
          <div id=\"gateway-access-note\" class=\"hint\" style=\"margin-top:12px\"></div>
        </div>

        <div class=\"section-card\">
          <h3>Device Info</h3>
          <div class=\"kv\" id=\"device-info\"></div>
          <div class=\"hint\" style=\"margin-top:12px\">Some radio and network changes may need a reboot before they fully take effect.</div>
        </div>
      </div>
    </section>

    <section id=\"contacts\" class=\"tab-panel hidden\">
      <div id=\"contacts-list-view\" class=\"panel\">
        <div class=\"heading-row\">
          <div>
            <h2>Contacts</h2>
            <div class=\"hint\">Open a contact to read direct-message history or send a message.</div>
          </div>
        </div>
        <div id=\"contacts-list\" class=\"list\"></div>
      </div>

      <div id="contact-detail-view" class="panel hidden">
        <div class="heading-row">
          <div>
            <button id="back-to-contacts">Back to contacts</button>
            <h2 id="contact-detail-heading" style="margin-top:12px">Contact</h2>
            <div id="contact-detail-meta" class="hint"></div>
          </div>
          <div class="row">
            <button id="clear-contact-messages">Clear messages</button>
            <button id="refresh-contact-messages">Check messages</button>
          </div>
        </div>
        <div id="contact-messages" class="messages"></div>
        <div class="subtle-divider"></div>
        <div class="field">
          <label for="contact-message-input">Send direct message</label>
          <textarea id="contact-message-input" placeholder="Type a direct message"></textarea>
        </div>
        <div class="row">
          <button id="send-contact-message" class="primary">Send message</button>
        </div>
      </div>
    </section>

    <section id=\"adverts\" class=\"tab-panel hidden\">
      <div class=\"panel\">
        <div class=\"heading-row\">
          <div>
            <h2>Recent Adverts</h2>
            <div class=\"hint\">Most recent observed adverts from known contacts.</div>
          </div>
        </div>
        <div id=\"recent-adverts\" class=\"list\"></div>
      </div>
    </section>

    <section id=\"channels\" class=\"tab-panel hidden\">
      <div id=\"channels-list-view\" class=\"panel\">
        <div class=\"heading-row\">
          <div>
            <h2>Channels</h2>
            <div class=\"hint\">Only active channels are listed. Open one to read or send messages.</div>
          </div>
        </div>
        <div id=\"channels-list\" class=\"list\"></div>
      </div>

      <div id=\"channel-detail-view\" class=\"panel hidden\">
        <div class=\"heading-row\">
          <div>
            <button id=\"back-to-channels\">Back to channels</button>
            <h2 id=\"channel-detail-heading\" style=\"margin-top:12px\">Channel</h2>
            <div id=\"channel-detail-meta\" class=\"hint\"></div>
          </div>
          <div class=\"row\">
            <button id=\"edit-channel\">Edit channel</button>
            <button id=\"delete-channel\" class=\"warn\">Delete channel</button>
            <button id=\"refresh-channel-messages\">Check messages</button>
          </div>
        </div>
        <div id=\"channel-messages\" class=\"messages\"></div>
        <div class=\"subtle-divider\"></div>
        <div class=\"field\">
          <label for=\"channel-message-input\">Send to selected channel</label>
          <textarea id=\"channel-message-input\" placeholder=\"Type a channel message\"></textarea>
        </div>
        <div class=\"row\">
          <button id=\"send-channel-message\" class=\"primary\">Send message</button>
        </div>
      </div>
    </section>

    <section id=\"map\" class=\"tab-panel hidden\">
      <div class=\"panel\">
        <div class=\"heading-row\">
          <div>
            <h2>Map</h2>
          </div>
        </div>
        <p id=\"map-summary\">No location data loaded.</p>
      </div>
    </section>

    <div id="action-workspace" class="action-workspace hidden">
      <div class="action-card">
        <div class="action-header">
          <div>
            <h3 id="action-title">Action Workspace</h3>
            <div id="action-subtitle" class="hint"></div>
          </div>
          <button id="hide-action-workspace">Done</button>
        </div>
        <div id="action-error" class="action-error hidden"></div>

        <div id="action-contact-import" class="action-view hidden">
          <div class="section-card">
            <h4>Import Contact</h4>
            <div class="hint">Paste the exported MeshCore contact code to add the contact through the native companion path.</div>
            <div class="field">
              <label for="action-contact-code">Contact code</label>
              <textarea id="action-contact-code" placeholder="Paste the MeshCore contact code"></textarea>
            </div>
          </div>
          <div class="action-actions">
            <button id="action-submit-contact-import" class="primary">Import Contact</button>
          </div>
        </div>

        <div id="action-contact-manual" class="action-view hidden">
          <div class="section-card">
            <h4>Manual Contact</h4>
            <div class="hint">Use this when you have a known public key and want to create the contact directly.</div>
            <div class="field">
              <label for="action-contact-name">Contact name</label>
              <input id="action-contact-name" type="text" placeholder="Friendly contact name">
            </div>
            <div class="field">
              <label for="action-contact-public-key">Public key</label>
              <textarea id="action-contact-public-key" class="mono" placeholder="Paste the full public key hex"></textarea>
            </div>
          </div>
          <div class="action-actions">
            <button id="action-submit-contact-manual" class="primary">Save Contact</button>
          </div>
        </div>

        <div id="action-channel-create" class="action-view hidden">
          <div class="section-card">
            <h4>Create Private Channel</h4>
            <div class="hint">Create a new private channel slot and generate a shareable invite URL.</div>
            <div class="field">
              <label for="action-channel-name">Private channel name</label>
              <input id="action-channel-name" type="text" placeholder="Channel name">
            </div>
            <div id="action-channel-created" class="field hidden">
              <label for="action-channel-invite">Invite URL</label>
              <textarea id="action-channel-invite" class="mono readonly-box" readonly></textarea>
            </div>
          </div>
          <div class="action-actions">
            <button id="action-submit-channel-create" class="primary">Create Channel</button>
          </div>
        </div>

        <div id="action-channel-join" class="action-view hidden">
          <div class="section-card">
            <h4>Join Private Channel</h4>
            <div class="hint">Paste an invite or enter the manual channel details below.</div>
            <div class="field">
              <label for="action-channel-invite-input">Invite or QR text</label>
              <textarea id="action-channel-invite-input" placeholder="Paste meshcore://channel/add?... if you have it"></textarea>
            </div>
            <div class="hint">Or enter the manual details below.</div>
            <div class="field">
              <label for="action-channel-join-name">Channel name</label>
              <input id="action-channel-join-name" type="text" placeholder="Private channel name">
            </div>
            <div class="field">
              <label for="action-channel-secret">Private channel secret</label>
              <textarea id="action-channel-secret" class="mono" placeholder="32 hex characters"></textarea>
            </div>
          </div>
          <div class="action-actions">
            <button id="action-submit-channel-join" class="primary">Join Channel</button>
          </div>
        </div>

        <div id="action-channel-edit" class="action-view hidden">
          <div class="section-card">
            <h4>Edit Channel</h4>
            <div class="hint">Update the selected channel name or secret for this slot.</div>
            <div class="field">
              <label for="action-channel-edit-name">Channel name</label>
              <input id="action-channel-edit-name" type="text" placeholder="Channel name">
            </div>
            <div class="field">
              <label for="action-channel-edit-secret">Channel secret</label>
              <textarea id="action-channel-edit-secret" class="mono" placeholder="32 hex characters"></textarea>
            </div>
          </div>
          <div class="action-actions">
            <button id="action-submit-channel-edit" class="primary">Save Channel</button>
          </div>
        </div>

        <div id="action-channel-delete" class="action-view hidden">
          <div class="section-card">
            <h4>Delete Channel</h4>
            <div id="action-channel-delete-text" class="hint">Remove the selected channel from this device.</div>
          </div>
          <div class="action-actions">
            <button id="action-submit-channel-delete" class="warn">Delete Channel</button>
          </div>
        </div>

        <div id="action-tools" class="action-view hidden">
          <div class="tool-sections">
            <div class="section-card tool-section">
              <h4>Diagnostics</h4>
              <div class="tool-grid">
                <div id="tool-card-overview" class="tool-card">
                  <div class="meta">Battery</div>
                  <strong id="tool-battery">-</strong>
                  <div class="hint">Uptime: <span id="tool-uptime">-</span></div>
                  <div class="hint">Queue: <span id="tool-queue">-</span></div>
                </div>
                <div id="tool-card-radio" class="tool-card">
                  <div class="meta">Radio</div>
                  <strong id="tool-rssi">-</strong>
                  <div class="hint">Noise floor: <span id="tool-noise">-</span></div>
                  <div class="hint">Last SNR: <span id="tool-snr">-</span></div>
                </div>
                <div id="tool-card-packets" class="tool-card">
                  <div class="meta">Packets</div>
                  <strong id="tool-packets-recv">-</strong>
                  <div class="hint">Sent: <span id="tool-packets-sent">-</span></div>
                  <div class="hint">Errors: <span id="tool-packets-errors">-</span></div>
                </div>
              </div>
            </div>
            <div class="section-card tool-section">
              <h4>Data & Identity</h4>
              <div class="tool-actions">
                <button id="action-tools-contact-code">My Contact Code</button>
                <button id="action-tools-import-contact">Import Contact Code</button>
                <button id="action-tools-discover">Discover Contacts</button>
              </div>
            </div>
            <div class="section-card tool-section">
              <h4>Maintenance</h4>
              <div class="tool-actions">
                <button id="action-tools-refresh-stats">Refresh Stats</button>
                <button id="action-tools-refresh-node">Refresh Node State</button>
                <button id="clear-tool-output">Clear Output</button>
                <button id="action-tools-reboot" class="warn">Reboot Device</button>
              </div>
            </div>
            <div class="field">
              <label for="tool-output">Tool output</label>
              <textarea id="tool-output" class="readonly-box mono" readonly></textarea>
            </div>
            <div class="field">
              <label for="tool-logs">Live debug logs</label>
              <textarea id="tool-logs" class="readonly-box mono" readonly></textarea>
            </div>
          </div>
        </div>

        <div id="action-info" class="action-view hidden">
          <div id="action-info-text" class="hint"></div>
          <textarea id="action-info-value" class="readonly-box mono hidden" readonly></textarea>
        </div>

        <div id="action-reboot" class="action-view hidden">
          <div class="hint">Reboot the device now? This interrupts the current session and some settings changes may need it to take effect.</div>
          <div class="action-actions">
            <button id="action-submit-reboot" class="warn">Reboot Device</button>
          </div>
        </div>
      </div>
    </div>
  </main>
  <script>
    const radioPresets = [
      { key: 'default', label: 'MeshCore default', bw_khz: 250.0, sf: 11, cr: 5 },
      { key: 'balanced', label: 'Balanced', bw_khz: 250.0, sf: 10, cr: 5 },
      { key: 'long_range', label: 'Long range', bw_khz: 125.0, sf: 12, cr: 5 },
      { key: 'fast', label: 'Fast', bw_khz: 250.0, sf: 9, cr: 5 },
    ];

    let currentModel = null;
    let selectedContactKey = null;
    let selectedChannelIndex = null;
    let activeMenuView = 'shared-menu-root';
    let liveEventSource = null;
    let liveToolLogs = [];
    let recentAdvertEvents = [];
    let currentGatewayAccess = null;

    function setStatus(text) {
      document.getElementById('status').textContent = text;
    }

    function clearActionError() {
      const errorBox = document.getElementById('action-error');
      errorBox.textContent = '';
      errorBox.classList.add('hidden');
    }

    function setActionError(text) {
      const errorBox = document.getElementById('action-error');
      errorBox.textContent = text;
      errorBox.classList.remove('hidden');
    }

    function resetActionWorkspace() {
      clearActionError();
      document.getElementById('action-contact-code').value = '';
      document.getElementById('action-contact-name').value = '';
      document.getElementById('action-contact-public-key').value = '';
      document.getElementById('action-channel-name').value = '';
      document.getElementById('action-channel-invite').value = '';
      document.getElementById('action-channel-created').classList.add('hidden');
      document.getElementById('action-channel-invite-input').value = '';
      document.getElementById('action-channel-join-name').value = '';
      document.getElementById('action-channel-secret').value = '';
      document.getElementById('action-info-text').textContent = '';
      document.getElementById('action-info-value').value = '';
      document.getElementById('action-info-value').classList.add('hidden');
    }

    function showActionWorkspace(panelId, title, subtitle = '') {
      resetActionWorkspace();
      document.querySelectorAll('.action-view').forEach(panel => {
        panel.classList.toggle('hidden', panel.id !== panelId);
      });
      document.getElementById('action-title').textContent = title;
      document.getElementById('action-subtitle').textContent = subtitle;
      const shell = document.getElementById('action-workspace');
      shell.classList.remove('hidden');
      shell.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function hideActionWorkspace() {
      document.getElementById('action-workspace').classList.add('hidden');
      clearActionError();
    }

    function updateSharedMenuVisibility() {
      const activeTab = document.querySelector('.tab.active')?.dataset.tab;
      const sharedMenuShell = document.getElementById('shared-menu-shell');
      const shouldShow = activeTab === 'contacts' || activeTab === 'adverts' || activeTab === 'channels' || activeTab === 'map';
      sharedMenuShell.classList.toggle('hidden', !shouldShow);
      if (!shouldShow) {
        closeAllMenus();
      }
    }

    function formatTimestamp(value) {
      if (!value) return 'Unknown time';
      const date = new Date(value * 1000);
      const pad = part => String(part).padStart(2, '0');
      return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())} UTC`;
    }

    function isDeviceClockStale(deviceTime) {
      if (!deviceTime) return false;
      const nowSeconds = Math.floor(Date.now() / 1000);
      return Math.abs(nowSeconds - Number(deviceTime)) > 24 * 60 * 60;
    }

    function formatNodeClockTimestamp(value) {
      const text = formatTimestamp(value);
      if (!value) {
        return text;
      }
      return isDeviceClockStale(currentModel?.identity?.device_time) ? `${text} (node clock looks stale)` : text;
    }

    function formatLocation(lat, lon) {
      if (lat === null || lon === null || lat === undefined || lon === undefined) return 'Unavailable';
      return `${Number(lat).toFixed(6)}, ${Number(lon).toFixed(6)}`;
    }

    function formatRadioTuple(freq, bw, sf, cr) {
      return `${Number(freq).toFixed(3)} MHz, ${Number(bw).toFixed(1)} kHz, SF${sf}, CR${cr}`;
    }

    function renderKv(targetId, entries) {
      const target = document.getElementById(targetId);
      target.innerHTML = '';
      entries.forEach(([label, value]) => {
        const left = document.createElement('div');
        left.textContent = label;
        const right = document.createElement('div');
        right.textContent = value;
        target.append(left, right);
      });
    }

    function renderGatewayAccess(access) {
      const card = document.getElementById('gateway-access-card');
      const note = document.getElementById('gateway-access-note');
      const checkbox = document.getElementById('gateway-allow-tx');
      const statusPill = document.getElementById('gateway-status');
      if (!access || !access.enabled) {
        currentGatewayAccess = null;
        card.classList.add('hidden');
        checkbox.checked = false;
        renderKv('gateway-access-settings', []);
        note.textContent = 'Embedded gateway listener is not active in this UI process.';
        statusPill.textContent = 'Gateway inactive';
        statusPill.className = 'status-pill';
        return;
      }
      currentGatewayAccess = access;
      card.classList.remove('hidden');
      checkbox.checked = Boolean(access.gateway_tx_allowed);
      renderKv('gateway-access-settings', [
        ['Mode', access.gateway_access_mode || 'unknown'],
        ['Current TX', access.gateway_tx_allowed ? 'Allowed' : 'Blocked'],
        ['Default TX', access.default_gateway_tx_allowed ? 'Allowed' : 'Blocked'],
        ['Gateway link', access.link_endpoint || 'Unavailable'],
        ['Runtime target', access.runtime_endpoint || 'Unavailable'],
      ]);
      note.textContent = access.persistence_note || 'Applies to the running browser UI process.';
      if (access.gateway_tx_allowed) {
        statusPill.textContent = 'Gateway connected, TX enabled';
        statusPill.className = 'status-pill ok';
      } else {
        statusPill.textContent = 'Gateway connected, TX disabled';
        statusPill.className = 'status-pill warn';
      }
    }

    async function refreshGatewayAccess() {
      try {
        const payload = await callApi('/api/gateway/access');
        renderGatewayAccess(payload);
      } catch (error) {
        renderGatewayAccess({ enabled: false });
      }
    }

    async function saveGatewayAccess() {
      if (!currentGatewayAccess) {
        setStatus('Embedded gateway listener is not active in this UI process.');
        return;
      }
      const allowBasestationTx = document.getElementById('gateway-allow-tx').checked;
      setStatus('Applying gateway access...');
      try {
        const payload = await callApi('/api/gateway/access', 'POST', { allow_basestation_tx: allowBasestationTx });
        renderGatewayAccess(payload);
        await refreshModel('Refreshing node state...');
        setStatus(allowBasestationTx ? 'Gateway transmit access enabled.' : 'Gateway transmit access disabled.');
      } catch (error) {
        setStatus(String(error));
      }
    }

    function isActiveChannel(channel) {
      const secret = String(channel.secret_hex || '');
      return Boolean((channel.name || '').trim()) || Array.from(secret).some(char => char !== '0');
    }

    function getActiveChannels() {
      if (!currentModel) return [];
      return (currentModel.channels || []).filter(channel => channel && isActiveChannel(channel));
    }

    function getSelectedChannel() {
      return getActiveChannels().find(channel => Number(channel.index) === Number(selectedChannelIndex)) || null;
    }

    function getContacts() {
      if (!currentModel) return [];
      return (currentModel.contacts || []).filter(contact => contact && contact.public_key);
    }

    function getSelectedContact() {
      return getContacts().find(contact => String(contact.public_key) === String(selectedContactKey)) || null;
    }

    function populatePresets(model) {
      const select = document.getElementById('radio-preset');
      select.innerHTML = '';
      const current = radioPresets.find(preset => Math.abs(preset.bw_khz - model.radio.bw_khz) < 0.05 && preset.sf === model.radio.sf && preset.cr === model.radio.cr);
      if (!current) {
        const option = document.createElement('option');
        option.value = 'custom';
        option.textContent = `Current custom (${formatRadioTuple(model.radio.freq_mhz, model.radio.bw_khz, model.radio.sf, model.radio.cr)})`;
        option.dataset.bw = model.radio.bw_khz;
        option.dataset.sf = model.radio.sf;
        option.dataset.cr = model.radio.cr;
        select.appendChild(option);
      }
      radioPresets.forEach(preset => {
        const option = document.createElement('option');
        option.value = preset.key;
        option.textContent = `${preset.label} (${preset.bw_khz.toFixed(1)} kHz / SF${preset.sf} / CR${preset.cr})`;
        option.dataset.bw = preset.bw_khz;
        option.dataset.sf = preset.sf;
        option.dataset.cr = preset.cr;
        if (current && current.key === preset.key) {
          option.selected = true;
        }
        select.appendChild(option);
      });
      updateRadioNote();
    }

    function updateRadioNote() {
      if (!currentModel) return;
      const option = document.getElementById('radio-preset').selectedOptions[0];
      if (!option) return;
      const bw = Number(option.dataset.bw);
      const sf = Number(option.dataset.sf);
      const cr = Number(option.dataset.cr);
      document.getElementById('radio-note').textContent = `Selected preset will apply ${formatRadioTuple(currentModel.radio.freq_mhz, bw, sf, cr)}. Repeat mode may be rejected by the device on unsupported frequencies.`;
    }

    function formatMessageKind(routeType, direction) {
      if (!routeType) return 'No message history yet';
      const label = routeType === 'direct' ? 'Direct' : routeType === 'flood' ? 'Flood' : 'Unknown';
      return `${label} ${direction === 'outgoing' ? 'sent' : 'received'}`;
    }

    function renderContacts(model) {
      const contactsList = document.getElementById('contacts-list');
      contactsList.innerHTML = '';
      if (!model.contacts.length) {
        contactsList.innerHTML = '<div class="empty-state">No contacts are configured yet.</div>';
        return;
      }
      model.contacts.forEach(contact => {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'item linklike';
        const lastMessageLine = contact.last_message_timestamp
          ? `Last message: ${formatTimestamp(contact.last_message_timestamp)} • ${formatMessageKind(contact.last_message_route, contact.last_message_direction)}`
          : 'Last message: No direct message history yet.';
        item.innerHTML = `<strong>${contact.name || 'Unnamed contact'}</strong><div class=\"mono\">${contact.public_key}</div><div class=\"hint\">${lastMessageLine}</div>`;
        item.addEventListener('click', () => openContact(contact.public_key));
        contactsList.appendChild(item);
      });
    }

    function renderRecentAdverts(model) {
      const advertsList = document.getElementById('recent-adverts');
      const recentContacts = (model.contacts || [])
        .filter(contact => Number(contact.last_advert_timestamp || 0) > 0)
        .sort((left, right) => Number(right.lastmod || right.last_advert_timestamp || 0) - Number(left.lastmod || left.last_advert_timestamp || 0))
        .slice(0, 8);
      advertsList.innerHTML = '';
      if (!recentContacts.length && !recentAdvertEvents.length) {
        advertsList.innerHTML = '<div class="empty-state">No recent adverts are visible yet. When adverts are seen from other nodes, they will appear here.</div>';
        return;
      }
      recentAdvertEvents.forEach(entry => {
        const item = document.createElement('div');
        item.className = 'item';
        item.innerHTML = `<strong>Observed advert</strong><div class="hint">Advert received: ${formatTimestamp(entry.received_at)}</div><div class="hint">Waiting for refreshed contact details.</div>`;
        advertsList.appendChild(item);
      });
      recentContacts.forEach(contact => {
        const item = document.createElement('div');
        item.className = 'item';
        const locationLine = (contact.gps_lat || contact.gps_lon)
          ? `Location: ${formatLocation(contact.gps_lat, contact.gps_lon)}`
          : 'Location: Unavailable';
        const recordUpdateLine = contact.lastmod
          ? `Record updated on node clock: ${formatNodeClockTimestamp(contact.lastmod)}`
          : 'Record updated on node clock: Unknown';
        item.innerHTML = `<strong>${contact.name || 'Unnamed contact'}</strong><div class="mono">${contact.public_key}</div><div class="hint">Advert clock: ${formatTimestamp(contact.last_advert_timestamp)}</div><div class="hint">${recordUpdateLine}</div><div class="hint">${locationLine}</div>`;
        advertsList.appendChild(item);
      });
    }

    function renderChannelList() {
      const channelsList = document.getElementById('channels-list');
      channelsList.innerHTML = '';
      const activeChannels = getActiveChannels();
      if (!activeChannels.length) {
        channelsList.innerHTML = '<div class="empty-state">No active channels are configured.</div>';
        return;
      }
      activeChannels.forEach(channel => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'item linklike';
        const lastMessageLine = channel.last_message_timestamp
          ? `Last message: ${formatTimestamp(channel.last_message_timestamp)}`
          : 'Last message: No channel traffic yet.';
        button.innerHTML = `<span class=\"chip\">${channel.index}</span><strong>${channel.name || 'Unnamed channel'}</strong><div class=\"hint\">${lastMessageLine}</div>`;
        button.addEventListener('click', () => openChannel(channel.index));
        channelsList.appendChild(button);
      });
    }

    function render(model) {
      currentModel = model;
      document.getElementById('node-name').value = model.identity.name || '';
      document.getElementById('device-time').value = model.identity.device_time ? formatTimestamp(model.identity.device_time).replace(' UTC', '') : '';
      document.getElementById('advert-lat').value = model.identity.advert_lat == null ? '' : Number(model.identity.advert_lat).toFixed(6);
      document.getElementById('advert-lon').value = model.identity.advert_lon == null ? '' : Number(model.identity.advert_lon).toFixed(6);
      document.getElementById('public-key').textContent = model.identity.public_key || '-';
      document.getElementById('scope-location').textContent = formatLocation(model.identity.advert_lat, model.identity.advert_lon);
      document.getElementById('custom-vars').textContent = Object.keys(model.custom_vars || {}).length ? Object.keys(model.custom_vars).join(', ') : 'None';
      document.getElementById('tx-power').value = model.radio.tx_power_dbm;
      document.getElementById('repeat-mode').checked = Boolean(model.capabilities.client_repeat);
      document.getElementById('max-tx').textContent = `${model.radio.max_tx_power_dbm} dBm`;
      document.getElementById('frequency').textContent = `${Number(model.radio.freq_mhz).toFixed(3)} MHz`;
      document.getElementById('radio-current').textContent = formatRadioTuple(model.radio.freq_mhz, model.radio.bw_khz, model.radio.sf, model.radio.cr);
      populatePresets(model);
      renderKv('network-settings', [
        ['Max contacts', String(model.capabilities.max_contacts ?? 'Unavailable')],
        ['Max channels', String(model.capabilities.max_channels ?? 'Unavailable')],
        ['Client repeat', model.capabilities.client_repeat ? 'Enabled' : 'Disabled'],
        ['Path hash mode', String(model.capabilities.path_hash_mode ?? 'Unavailable')],
        ['Manual add contacts', model.capabilities.manual_add_contacts ? 'Enabled' : 'Disabled'],
        ['Provisioned channels', String(model.provisioned_channel_count)],
        ['Contact count', String(model.contacts.length)],
      ]);
      renderKv('other-settings', [
        ['GPS mode', String(model.custom_vars.gps ?? 'Unavailable')],
        ['GPS interval', String(model.custom_vars.gps_interval ?? 'Unavailable')],
        ['Advert policy', String(model.radio.advert_loc_policy)],
        ['Telemetry base', String(model.radio.telemetry_mode_base)],
        ['Telemetry location', String(model.radio.telemetry_mode_loc)],
        ['Telemetry environment', String(model.radio.telemetry_mode_env)],
      ]);
      renderKv('device-info', [
        ['Model', model.identity.model || 'Unknown'],
        ['Firmware version', model.identity.firmware_version || 'Unknown'],
        ['Firmware build', model.identity.firmware_build || 'Unknown'],
        ['Clock status', isDeviceClockStale(model.identity.device_time) ? 'Node clock differs from browser time by more than 24 hours' : 'Node clock is close to browser time'],
        ['BLE pin', String(model.capabilities.ble_pin ?? 'Unavailable')],
        ['Battery', `${model.battery.battery_mv} mV`],
        ['Storage', model.battery.used_kb == null || model.battery.total_kb == null ? 'Unavailable' : `${model.battery.used_kb} / ${model.battery.total_kb} kB`],
      ]);
      renderRecentAdverts(model);
      renderContacts(model);
      renderChannelList();
      document.getElementById('map-summary').textContent = `Node location: ${formatLocation(model.identity.advert_lat, model.identity.advert_lon)}. Contacts with location: ${model.contacts_with_location_count}. Provisioned channels: ${model.provisioned_channel_count}.`;
      if (selectedChannelIndex !== null && !getSelectedChannel()) {
        closeChannelDetail();
      }
    }

    function setActiveTab(tabName) {
      document.querySelectorAll('.tab').forEach(button => {
        button.classList.toggle('active', button.dataset.tab === tabName);
      });
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('hidden', panel.id !== tabName);
      });
      updateSharedMenuVisibility();
    }

    function showChannelList() {
      document.getElementById('channels-list-view').classList.remove('hidden');
      document.getElementById('channel-detail-view').classList.add('hidden');
    }

    function showContactList() {
      document.getElementById('contacts-list-view').classList.remove('hidden');
      document.getElementById('contact-detail-view').classList.add('hidden');
    }

    function showContactDetail() {
      document.getElementById('contacts-list-view').classList.add('hidden');
      document.getElementById('contact-detail-view').classList.remove('hidden');
    }

    function showChannelDetail() {
      document.getElementById('channels-list-view').classList.add('hidden');
      document.getElementById('channel-detail-view').classList.remove('hidden');
    }

    function closeChannelDetail() {
      selectedChannelIndex = null;
      document.getElementById('channel-message-input').value = '';
      showChannelList();
    }

    function closeContactDetail() {
      selectedContactKey = null;
      document.getElementById('contact-message-input').value = '';
      showContactList();
    }

    function renderContactMessages(messages) {
      const container = document.getElementById('contact-messages');
      container.innerHTML = '';
      if (!messages.length) {
        container.innerHTML = '<div class="empty-state">No direct messages loaded yet.</div>';
        return;
      }
      messages.forEach(message => {
        const card = document.createElement('div');
        card.className = `message ${message.direction === 'outgoing' ? 'outgoing' : 'incoming'}`;
        const text = document.createElement('div');
        text.textContent = message.text || '(non-text payload)';
        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = `${message.direction === 'outgoing' ? 'Sent' : 'Received'} • ${formatTimestamp(message.timestamp)} • ${formatMessageKind(message.route_type, message.direction)}${message.snr == null ? '' : ` • SNR ${message.snr}`}`;
        card.append(text, meta);
        container.appendChild(card);
      });
    }

    function renderChannelMessages(messages) {
      const container = document.getElementById('channel-messages');
      container.innerHTML = '';
      if (!messages.length) {
        container.innerHTML = '<div class="empty-state">No channel messages loaded yet. Live notices now refresh this view when traffic arrives, and Refresh still forces a manual reload.</div>';
        return;
      }
      messages.forEach(message => {
        const card = document.createElement('div');
        card.className = `message ${message.direction === 'outgoing' ? 'outgoing' : 'incoming'}`;
        const text = document.createElement('div');
        text.textContent = message.text || '(non-text payload)';
        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = `${message.direction === 'outgoing' ? 'Sent' : 'Received'} • ${formatTimestamp(message.timestamp)}${message.snr == null ? '' : ` • SNR ${message.snr}`}`;
        card.append(text, meta);
        container.appendChild(card);
      });
    }

    function updateSelectedChannelHeading() {
      const channel = getSelectedChannel();
      if (!channel) return;
      document.getElementById('channel-detail-heading').textContent = channel.name || `Channel ${channel.index}`;
      document.getElementById('channel-detail-meta').textContent = `Channel slot ${channel.index} • ${channel.secret_hex}`;
    }

    function updateSelectedContactHeading() {
      const contact = getSelectedContact();
      if (!contact) return;
      document.getElementById('contact-detail-heading').textContent = contact.name || 'Unnamed contact';
      const advertClock = contact.last_advert_timestamp ? formatTimestamp(contact.last_advert_timestamp) : 'Unknown';
      const localUpdate = contact.lastmod ? formatNodeClockTimestamp(contact.lastmod) : 'Unknown';
      document.getElementById('contact-detail-meta').textContent = `${contact.public_key} • Advert clock ${advertClock} • Record updated on node clock ${localUpdate}`;
    }

    function populateChannelEditForm(channel) {
      document.getElementById('action-channel-edit-name').value = channel.name || '';
      document.getElementById('action-channel-edit-secret').value = channel.secret_hex || '';
      document.getElementById('action-channel-delete-text').textContent = `Remove ${channel.name || `channel ${channel.index}`} from slot ${channel.index} on this device.`;
    }

    async function callApi(path, method = 'GET', body = null) {
      const response = await fetch(path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : null,
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || `Request failed with status ${response.status}`);
      }
      return payload;
    }

    function showMenuView(menuId) {
      activeMenuView = menuId;
      document.querySelectorAll('.menu-panel').forEach(panel => {
        panel.classList.toggle('hidden', panel.id !== menuId);
      });
    }

    function closeAllMenus() {
      document.querySelectorAll('.menu-panel').forEach(panel => panel.classList.add('hidden'));
      activeMenuView = 'shared-menu-root';
    }

    async function copyTextToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
      const temporaryInput = document.createElement('textarea');
      temporaryInput.value = text;
      temporaryInput.setAttribute('readonly', 'readonly');
      temporaryInput.style.position = 'fixed';
      temporaryInput.style.left = '-9999px';
      document.body.appendChild(temporaryInput);
      temporaryInput.select();
      temporaryInput.setSelectionRange(0, temporaryInput.value.length);
      try {
        const ok = document.execCommand('copy');
        document.body.removeChild(temporaryInput);
        return ok;
      } catch (error) {
        document.body.removeChild(temporaryInput);
        return false;
      }
    }

    function setInfoPanel(text, value = '') {
      document.getElementById('action-info-text').textContent = text;
      const valueBox = document.getElementById('action-info-value');
      if (value) {
        valueBox.value = value;
        valueBox.classList.remove('hidden');
      } else {
        valueBox.value = '';
        valueBox.classList.add('hidden');
      }
    }

    function writeToolOutput(text) {
      document.getElementById('tool-output').value = text;
    }

    function clearToolOutput() {
      writeToolOutput('');
    }

    function formatToolLogLine(entry) {
      const stamp = entry.received_at ? formatTimestamp(entry.received_at) : 'Unknown time';
      const snr = entry.snr == null ? 'n/a' : entry.snr;
      const rssi = entry.rssi == null ? 'n/a' : entry.rssi;
      return `${stamp} • RSSI ${rssi} dBm • SNR ${snr} • ${entry.payload_hex || ''}`;
    }

    function renderToolLogs(entries) {
      const logBox = document.getElementById('tool-logs');
      liveToolLogs = Array.isArray(entries) ? entries.slice(-200) : [];
      logBox.value = liveToolLogs.length ? liveToolLogs.map(formatToolLogLine).join('\\n') : 'No live debug frames received yet.';
      logBox.scrollTop = logBox.scrollHeight;
    }

    function appendToolLog(entry) {
      liveToolLogs.push(entry);
      if (liveToolLogs.length > 200) {
        liveToolLogs = liveToolLogs.slice(-200);
      }
      renderToolLogs(liveToolLogs);
    }

    function connectEventStream() {
      if (liveEventSource) {
        return;
      }
      liveEventSource = new EventSource('/api/events');
      liveEventSource.addEventListener('session-status', event => {
        const payload = JSON.parse(event.data);
        if (payload.status) {
          setStatus(payload.status);
        }
      });
      liveEventSource.addEventListener('messages-waiting', async event => {
        const payload = JSON.parse(event.data);
        if (selectedChannelIndex !== null && payload.channel_index === selectedChannelIndex) {
          await refreshChannelMessages('New channel traffic arrived...');
          return;
        }
        if (payload.channel_index === null || payload.channel_index === undefined) {
          if (selectedContactKey !== null) {
            await refreshContactMessages('New direct traffic arrived...');
            return;
          }
          setStatus('New direct message traffic is waiting. Open a contact to load it.');
          return;
        }
        setStatus(`New traffic arrived on channel ${payload.channel_index}.`);
      });
      liveEventSource.addEventListener('channel-message', async event => {
        const payload = JSON.parse(event.data);
        if (payload.direction === 'incoming') {
          writeToolOutput(`Incoming channel message on slot ${payload.channel_index}.`);
        }
        await refreshModel('Refreshing channel activity...');
        if (selectedChannelIndex !== null && payload.channel_index === selectedChannelIndex) {
          await refreshChannelMessages('Refreshing channel after new traffic...');
        }
      });
      liveEventSource.addEventListener('contact-message', async event => {
        const payload = JSON.parse(event.data);
        writeToolOutput(`Incoming direct message for ${payload.public_key_ref.slice(0, 12)}.`);
        await refreshModel('Refreshing contact activity...');
        if (selectedContactKey !== null && payload.public_key_ref === selectedContactKey) {
          await refreshContactMessages('Refreshing contact after new traffic...');
        }
      });
      liveEventSource.addEventListener('advert-sent', event => {
        const payload = JSON.parse(event.data);
        const advertMode = payload.flood ? 'Flood advert' : 'Zero-hop advert';
        const when = payload.sent_at ? formatTimestamp(payload.sent_at) : 'Unknown time';
        writeToolOutput(`${advertMode} sent at ${when}.`);
        setStatus(`${advertMode} sent at ${when}.`);
      });
      liveEventSource.addEventListener('advertisement', async event => {
        const payload = JSON.parse(event.data);
        const when = payload.received_at ? formatTimestamp(payload.received_at) : 'Unknown time';
        recentAdvertEvents = [{ received_at: payload.received_at || Math.floor(Date.now() / 1000) }, ...recentAdvertEvents]
          .slice(0, 8);
        if (currentModel) {
          renderRecentAdverts(currentModel);
        }
        writeToolOutput(`Advert received at ${when}. Refreshing contacts...`);
        setStatus(`Advert received at ${when}. Refreshing contacts...`);
        await refreshModel('Refreshing after received advert...');
      });
      liveEventSource.addEventListener('log-frame', event => {
        appendToolLog(JSON.parse(event.data));
      });
      liveEventSource.onerror = () => {
        setStatus('Live event stream reconnecting...');
      };
    }

    function highlightToolCard(section) {
      document.getElementById('tool-card-overview').classList.toggle('active', section === 'overview');
      document.getElementById('tool-card-radio').classList.toggle('active', section === 'radio');
      document.getElementById('tool-card-packets').classList.toggle('active', section === 'packets');
    }

    function renderTools(payload) {
      const core = payload.core || {};
      const radio = payload.radio || {};
      const packets = payload.packets || {};
      document.getElementById('tool-battery').textContent = `${core.battery_mv ?? '-'} mV`;
      document.getElementById('tool-uptime').textContent = `${core.uptime_secs ?? '-'} s`;
      document.getElementById('tool-queue').textContent = String(core.queue_len ?? '-');
      document.getElementById('tool-rssi').textContent = radio.last_rssi == null ? 'Unavailable' : `${radio.last_rssi} dBm`;
      document.getElementById('tool-noise').textContent = radio.noise_floor == null ? 'Unavailable' : String(radio.noise_floor);
      document.getElementById('tool-snr').textContent = radio.last_snr == null ? 'Unavailable' : String(radio.last_snr);
      document.getElementById('tool-packets-recv').textContent = String(packets.packets_recv ?? '-');
      document.getElementById('tool-packets-sent').textContent = String(packets.packets_sent ?? '-');
      document.getElementById('tool-packets-errors').textContent = String(packets.recv_errors ?? '-');
      writeToolOutput('Live tool stats loaded from the native companion path.');
      renderToolLogs(payload.logs || []);
    }

    async function showContactCode() {
      showActionWorkspace('action-info', 'My Contact Code', 'Share this code with another MeshCore user.');
      setStatus('Loading self contact code...');
      try {
        const payload = await callApi('/api/actions/export-contact-code');
        setInfoPanel('Share this code with another MeshCore user.', payload.contact_code);
        writeToolOutput('Loaded self contact code into the action workspace.');
        setStatus('Loaded self contact code.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function copyAdvertToClipboard() {
      closeAllMenus();
      setStatus('Loading self advert for clipboard...');
      try {
        const payload = await callApi('/api/actions/export-contact-code');
        const copied = await copyTextToClipboard(payload.contact_code);
        if (copied) {
          writeToolOutput('Copied self advert to the clipboard.');
          setStatus('Self advert copied to clipboard.');
          return;
        }
        showActionWorkspace('action-info', 'Advert To Clipboard', 'Clipboard access was unavailable, so the advert text is shown here.');
        setInfoPanel('Copy this self advert manually.', payload.contact_code);
        writeToolOutput('Clipboard access was unavailable; displayed the self advert for manual copy.');
        setStatus('Clipboard access unavailable. Self advert shown for manual copy.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function sendAdvert(flood) {
      closeAllMenus();
      setStatus(flood ? 'Sending flood advert...' : 'Sending zero-hop advert...');
      try {
        await callApi('/api/actions/discover-contacts', 'POST', { flood });
        writeToolOutput(flood ? 'Sent a flood self advert through the native companion path.' : 'Sent a zero-hop self advert through the native companion path.');
        setStatus(flood ? 'Flood advert sent.' : 'Zero-hop advert sent.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    function showAbout() {
      showActionWorkspace('action-info', 'About MeshCore', 'Current browser-shell direction.');
      setInfoPanel('MeshCore UI browser shell. Thin companion-protocol browser path under ui-native.');
      writeToolOutput('Displayed the current browser-shell direction in the action workspace.');
    }

    async function showTools(section = 'overview') {
      showActionWorkspace('action-tools', 'Tools', 'Native-backed diagnostics and maintenance actions.');
      highlightToolCard(section);
      setStatus('Loading tool statistics...');
      try {
        const payload = await callApi('/api/actions/tools-summary');
        renderTools(payload);
        setStatus('Loaded tool statistics.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function addContact(mode) {
      if (mode === 'code') {
        showActionWorkspace('action-contact-import', 'Import Contact Code', 'Paste the contact code exported from another device.');
        writeToolOutput('Ready to import a MeshCore contact code.');
        return;
      }
      showActionWorkspace('action-contact-manual', 'Manual Contact', 'Enter the contact name and full public key.');
      writeToolOutput('Ready to add a manual contact.');
    }

    async function submitContactImport() {
      try {
        const contactCode = document.getElementById('action-contact-code').value.trim();
        if (!contactCode) {
          setActionError('Contact code is required.');
          return;
        }
        setStatus('Importing contact...');
        await callApi('/api/contacts', 'POST', { contact_code: contactCode });
        await refreshModel('Refreshing after contact change...');
        hideActionWorkspace();
        writeToolOutput('Imported a contact from MeshCore contact code.');
        setStatus('Contact added.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function submitContactManual() {
      try {
        const name = document.getElementById('action-contact-name').value.trim();
        const publicKey = document.getElementById('action-contact-public-key').value.trim();
        if (!name || !publicKey) {
          setActionError('Both contact name and public key are required.');
          return;
        }
        setStatus('Adding contact...');
        await callApi('/api/contacts', 'POST', { name, public_key_hex: publicKey });
        await refreshModel('Refreshing after contact change...');
        hideActionWorkspace();
        writeToolOutput(`Saved contact ${name}.`);
        setStatus('Contact added.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function addChannel() {
      showActionWorkspace('action-channel-create', 'Create Channel', 'Create a new private channel and copy its invite URL.');
      writeToolOutput('Ready to create a private channel.');
    }

    async function submitChannelCreate() {
      const name = document.getElementById('action-channel-name').value.trim();
      if (!name) {
        setActionError('Channel name is required.');
        return;
      }
      try {
        setStatus('Creating private channel...');
        const payload = await callApi('/api/channels', 'POST', { name });
        await refreshModel('Refreshing after channel change...');
        document.getElementById('action-channel-created').classList.remove('hidden');
        document.getElementById('action-channel-invite').value = payload.channel.invite_url;
        writeToolOutput(`Created private channel ${payload.channel.name} in slot ${payload.channel.index}.`);
        setStatus(`Channel created in slot ${payload.channel.index}.`);
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function joinPrivateChannel() {
      showActionWorkspace('action-channel-join', 'Join Private Channel', 'Paste an invite or enter the manual channel details.');
      writeToolOutput('Ready to join a private channel.');
    }

    async function editSelectedChannel() {
      const channel = getSelectedChannel();
      if (!channel) {
        setStatus('Select a channel first.');
        return;
      }
      showActionWorkspace('action-channel-edit', 'Edit Channel', 'Update the selected channel name or secret.');
      populateChannelEditForm(channel);
      writeToolOutput(`Ready to edit channel ${channel.name || channel.index}.`);
    }

    async function submitChannelEdit() {
      const channel = getSelectedChannel();
      if (!channel) {
        setStatus('Select a channel first.');
        return;
      }
      const name = document.getElementById('action-channel-edit-name').value.trim();
      const secretHex = document.getElementById('action-channel-edit-secret').value.trim();
      if (!name || !secretHex) {
        setActionError('Both channel name and secret are required.');
        return;
      }
      try {
        setStatus('Saving channel changes...');
        await callApi(`/api/channels/${channel.index}`, 'POST', { name, secret_hex: secretHex });
        await refreshModel('Refreshing after channel update...');
        updateSelectedChannelHeading();
        hideActionWorkspace();
        writeToolOutput(`Updated channel ${name} in slot ${channel.index}.`);
        setStatus('Channel updated.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function deleteSelectedChannel() {
      const channel = getSelectedChannel();
      if (!channel) {
        setStatus('Select a channel first.');
        return;
      }
      if (Number(channel.index) === 0) {
        setStatus('The public channel cannot be deleted.');
        return;
      }
      showActionWorkspace('action-channel-delete', 'Delete Channel', 'Remove the selected channel from this device.');
      populateChannelEditForm(channel);
      writeToolOutput(`Ready to delete channel ${channel.name || channel.index}.`);
    }

    async function confirmDeleteChannel() {
      const channel = getSelectedChannel();
      if (!channel) {
        setStatus('Select a channel first.');
        return;
      }
      try {
        setStatus('Deleting channel...');
        await callApi(`/api/channels/${channel.index}`, 'DELETE');
        hideActionWorkspace();
        closeChannelDetail();
        await refreshModel('Refreshing after channel removal...');
        writeToolOutput(`Deleted channel from slot ${channel.index}.`);
        setStatus('Channel deleted.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function submitJoinPrivateChannel() {
      try {
        let body;
        const invite = document.getElementById('action-channel-invite-input').value.trim();
        const name = document.getElementById('action-channel-join-name').value.trim();
        const secret = document.getElementById('action-channel-secret').value.trim();
        if (invite) {
          if (!invite.toLowerCase().startsWith('meshcore://channel/add?')) {
            setActionError('Invite text must start with meshcore://channel/add?... or be left blank for manual join.');
            return;
          }
          body = { invite };
        } else {
          if (!name || !secret) {
            setActionError('Manual join needs both a channel name and a private secret.');
            return;
          }
          body = { name, secret_hex: secret };
        }
        setStatus('Joining private channel...');
        const payload = await callApi('/api/channels', 'POST', body);
        await refreshModel('Refreshing after channel change...');
        hideActionWorkspace();
        writeToolOutput(`Joined private channel ${payload.channel.name} in slot ${payload.channel.index}.`);
        setStatus(`Joined private channel in slot ${payload.channel.index}.`);
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function discoverContacts() {
      await sendAdvert(true);
    }

    function handleMenuAction(action) {
      closeAllMenus();
      if (action === 'contact-import') {
        addContact('code');
        return;
      }
      if (action === 'contact-manual') {
        addContact('manual');
        return;
      }
      if (action === 'create-channel') {
        addChannel();
        return;
      }
      if (action === 'join-private-channel') {
        joinPrivateChannel();
        return;
      }
      if (action === 'discover-contacts') {
        discoverContacts();
        return;
      }
      if (action === 'advert-zero-hop') {
        sendAdvert(false);
        return;
      }
      if (action === 'advert-flood') {
        sendAdvert(true);
        return;
      }
      if (action === 'advert-copy') {
        copyAdvertToClipboard();
        return;
      }
      if (action === 'refresh') {
        refreshModel();
        return;
      }
      if (action === 'channels') {
        closeChannelDetail();
        setActiveTab('channels');
        return;
      }
      if (action === 'contact-code') {
        showContactCode();
        return;
      }
      if (action === 'tool-overview') {
        showTools('overview');
        return;
      }
      if (action === 'tool-radio') {
        showTools('radio');
        return;
      }
      if (action === 'tool-packets') {
        showTools('packets');
        return;
      }
      if (action === 'internet-map') {
        setActiveTab('map');
        return;
      }
      if (action === 'tools') {
        showTools();
        return;
      }
      if (action === 'reboot') {
        rebootDevice();
        return;
      }
      if (action === 'about') {
        showAbout();
        return;
      }
    }

    async function refreshModel(statusText = 'Refreshing node state...') {
      setStatus(statusText);
      try {
        const payload = await callApi('/api/node-page');
        render(payload.node_page);
        await refreshGatewayAccess();
        if (selectedContactKey !== null) {
          if (getSelectedContact()) {
            updateSelectedContactHeading();
          } else {
            closeContactDetail();
          }
        }
        if (selectedChannelIndex !== null) {
          if (getSelectedChannel()) {
            updateSelectedChannelHeading();
          } else {
            closeChannelDetail();
          }
        }
        setStatus('Loaded current node state.');
      } catch (error) {
        setStatus(String(error));
      }
    }

    function buildSettingsPayload() {
      if (!currentModel) {
        throw new Error('Refresh node state first.');
      }
      const rawTime = document.getElementById('device-time').value.trim();
      const date = new Date(rawTime.replace(' ', 'T') + 'Z');
      if (Number.isNaN(date.getTime())) {
        throw new Error('Device time must use YYYY-MM-DD HH:MM:SS in UTC.');
      }
      const rawLat = document.getElementById('advert-lat').value.trim();
      const rawLon = document.getElementById('advert-lon').value.trim();
      if ((rawLat && !rawLon) || (!rawLat && rawLon)) {
        throw new Error('Set both latitude and longitude, or leave both blank.');
      }
      const lat = rawLat ? Number(rawLat) : 0;
      const lon = rawLon ? Number(rawLon) : 0;
      if (Number.isNaN(lat) || Number.isNaN(lon)) {
        throw new Error('Advert location must use numeric latitude and longitude values.');
      }
      const option = document.getElementById('radio-preset').selectedOptions[0];
      return {
        name: document.getElementById('node-name').value.trim(),
        timestamp: Math.floor(date.getTime() / 1000),
        lat,
        lon,
        freq_mhz: currentModel.radio.freq_mhz,
        bw_khz: Number(option.dataset.bw),
        sf: Number(option.dataset.sf),
        cr: Number(option.dataset.cr),
        repeat: document.getElementById('repeat-mode').checked,
        tx_power_dbm: Number(document.getElementById('tx-power').value.trim()),
      };
    }

    async function saveAllSettings() {
      try {
        const body = buildSettingsPayload();
        setStatus('Saving edited settings...');
        const payload = await callApi('/api/settings/apply', 'POST', body);
        await refreshModel('Refreshing after settings save...');
        setStatus(payload.reboot_recommended ? 'Settings saved. Some radio changes may need a reboot.' : 'Settings saved.');
      } catch (error) {
        setStatus(String(error));
      }
    }

    async function usePcUtcNow() {
      const date = new Date();
      const pad = part => String(part).padStart(2, '0');
      const timestamp = Math.floor(date.getTime() / 1000);
      document.getElementById('device-time').value = `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}`;
      setStatus('Setting device time from browser UTC...');
      try {
        await callApi('/api/settings/time', 'POST', { timestamp });
        await refreshModel('Refreshing after time sync...');
        setStatus('Device time synced from browser UTC.');
      } catch (error) {
        setStatus(String(error));
      }
    }

    async function rebootDevice() {
      showActionWorkspace('action-reboot', 'Reboot Device', 'This sends a reboot command through the native companion path.');
    }

    async function confirmRebootDevice() {
      setStatus('Sending reboot command...');
      try {
        await callApi('/api/actions/reboot', 'POST', {});
        hideActionWorkspace();
        writeToolOutput('Reboot command sent through the native companion path.');
        setStatus('Reboot command sent. The device may take a short time to return.');
      } catch (error) {
        setActionError(String(error));
        setStatus(String(error));
      }
    }

    async function openChannel(index) {
      selectedChannelIndex = Number(index);
      updateSelectedChannelHeading();
      showChannelDetail();
      setActiveTab('channels');
      await refreshChannelMessages('Checking selected channel...');
    }

    async function refreshChannelMessages(statusText = 'Checking channel messages...') {
      if (selectedChannelIndex === null) {
        setStatus('Select a channel first.');
        return;
      }
      setStatus(statusText);
      try {
        const payload = await callApi(`/api/channels/${selectedChannelIndex}/messages`);
        renderChannelMessages(payload.messages || []);
        updateSelectedChannelHeading();
        setStatus(`Loaded ${payload.messages.length} message${payload.messages.length === 1 ? '' : 's'} for the selected channel.`);
      } catch (error) {
        setStatus(String(error));
      }
    }

    async function sendChannelMessage() {
      if (selectedChannelIndex === null) {
        setStatus('Select a channel first.');
        return;
      }
      const text = document.getElementById('channel-message-input').value.trim();
      if (!text) {
        setStatus('Channel message must not be empty.');
        return;
      }
      setStatus('Sending channel message...');
      try {
        const payload = await callApi(`/api/channels/${selectedChannelIndex}/messages`, 'POST', { text });
        document.getElementById('channel-message-input').value = '';
        renderChannelMessages(payload.messages || []);
        setStatus('Channel message sent.');
      } catch (error) {
        setStatus(String(error));
      }
    }

    async function openContact(publicKey) {
      selectedContactKey = publicKey;
      showContactDetail();
      updateSelectedContactHeading();
      await refreshContactMessages('Checking selected contact...');
    }

    async function refreshContactMessages(statusText = 'Checking direct messages...') {
      if (!selectedContactKey) {
        setStatus('Select a contact first.');
        return;
      }
      setStatus(statusText);
      try {
        const payload = await callApi(`/api/contacts/${selectedContactKey}/messages`);
        renderContactMessages(payload.messages || []);
        updateSelectedContactHeading();
        setStatus(`Loaded ${payload.messages.length} direct message${payload.messages.length === 1 ? '' : 's'} for the selected contact.`);
      } catch (error) {
        setStatus(String(error));
      }
    }

    async function sendContactMessage() {
      if (!selectedContactKey) {
        setStatus('Select a contact first.');
        return;
      }
      const text = document.getElementById('contact-message-input').value.trim();
      if (!text) {
        setStatus('Direct message must not be empty.');
        return;
      }
      setStatus('Sending direct message...');
      try {
        const payload = await callApi(`/api/contacts/${selectedContactKey}/messages`, 'POST', { text });
        document.getElementById('contact-message-input').value = '';
        renderContactMessages(payload.messages || []);
        await refreshModel('Refreshing contact activity...');
        setStatus('Direct message sent.');
      } catch (error) {
        setStatus(String(error));
      }
    }

    async function clearContactMessages() {
      if (!selectedContactKey) {
        setStatus('Select a contact first.');
        return;
      }
      setStatus('Clearing direct-message history...');
      try {
        await callApi(`/api/contacts/${selectedContactKey}/messages`, 'DELETE');
        renderContactMessages([]);
        await refreshModel('Refreshing contact activity...');
        setStatus('Direct-message history cleared from the browser session.');
      } catch (error) {
        setStatus(String(error));
      }
    }

    document.getElementById('edit-channel').addEventListener('click', editSelectedChannel);
    document.getElementById('delete-channel').addEventListener('click', deleteSelectedChannel);

    document.querySelectorAll('.tab').forEach(button => {
      button.addEventListener('click', () => {
        closeAllMenus();
        setActiveTab(button.dataset.tab);
      });
    });

    document.getElementById('shared-menu-toggle').addEventListener('click', event => {
      event.stopPropagation();
      const rootMenu = document.getElementById('shared-menu-root');
      const shouldShow = rootMenu.classList.contains('hidden');
      closeAllMenus();
      if (shouldShow) {
        showMenuView('shared-menu-root');
      }
    });

    document.getElementById('shared-advert-toggle').addEventListener('click', event => {
      event.stopPropagation();
      const advertMenu = document.getElementById('shared-advert-root');
      const shouldShow = advertMenu.classList.contains('hidden');
      closeAllMenus();
      if (shouldShow) {
        advertMenu.classList.remove('hidden');
      }
    });

    document.querySelectorAll('.shared-menu-nav').forEach(button => {
      button.addEventListener('click', event => {
        event.stopPropagation();
        showMenuView(button.dataset.menuView);
      });
    });

    document.querySelectorAll('.shared-menu-back').forEach(button => {
      button.addEventListener('click', event => {
        event.stopPropagation();
        showMenuView(button.dataset.menuView);
      });
    });

    document.querySelectorAll('.shared-menu-action').forEach(button => {
      button.addEventListener('click', () => handleMenuAction(button.dataset.action));
    });

    document.querySelectorAll('.shared-advert-action').forEach(button => {
      button.addEventListener('click', event => {
        event.stopPropagation();
        handleMenuAction(button.dataset.action);
      });
    });

    document.addEventListener('click', () => closeAllMenus());
    document.getElementById('hide-action-workspace').addEventListener('click', hideActionWorkspace);
    document.getElementById('action-submit-contact-import').addEventListener('click', submitContactImport);
    document.getElementById('action-submit-contact-manual').addEventListener('click', submitContactManual);
    document.getElementById('action-submit-channel-create').addEventListener('click', submitChannelCreate);
    document.getElementById('action-submit-channel-join').addEventListener('click', submitJoinPrivateChannel);
    document.getElementById('action-submit-channel-edit').addEventListener('click', submitChannelEdit);
    document.getElementById('action-submit-channel-delete').addEventListener('click', confirmDeleteChannel);
    document.getElementById('action-submit-reboot').addEventListener('click', confirmRebootDevice);
    document.getElementById('action-tools-refresh-stats').addEventListener('click', () => showTools('overview'));
    document.getElementById('action-tools-contact-code').addEventListener('click', showContactCode);
    document.getElementById('action-tools-import-contact').addEventListener('click', () => addContact('code'));
    document.getElementById('action-tools-discover').addEventListener('click', discoverContacts);
    document.getElementById('action-tools-refresh-node').addEventListener('click', () => refreshModel('Refreshing node state...'));
    document.getElementById('action-tools-reboot').addEventListener('click', rebootDevice);
    document.getElementById('clear-tool-output').addEventListener('click', clearToolOutput);

    document.getElementById('refresh').addEventListener('click', () => refreshModel());
    document.getElementById('save-settings').addEventListener('click', saveAllSettings);
    document.getElementById('save-gateway-access').addEventListener('click', saveGatewayAccess);
    document.getElementById('reboot-device').addEventListener('click', rebootDevice);
    document.getElementById('use-now').addEventListener('click', usePcUtcNow);
    document.getElementById('radio-preset').addEventListener('change', updateRadioNote);
    document.getElementById('back-to-contacts').addEventListener('click', closeContactDetail);
    document.getElementById('refresh-contact-messages').addEventListener('click', () => refreshContactMessages());
    document.getElementById('clear-contact-messages').addEventListener('click', clearContactMessages);
    document.getElementById('send-contact-message').addEventListener('click', sendContactMessage);
    document.getElementById('back-to-channels').addEventListener('click', closeChannelDetail);
    document.getElementById('refresh-channel-messages').addEventListener('click', () => refreshChannelMessages());
    document.getElementById('send-channel-message').addEventListener('click', sendChannelMessage);

    updateSharedMenuVisibility();
    connectEventStream();
    refreshModel();
  </script>
</body>
</html>
"""


def _parse_channel_messages_path(path: str) -> int | None:
    parts = urlparse(path).path.strip("/").split("/")
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "channels" and parts[3] == "messages":
        return int(parts[2])
    return None


def _parse_contact_messages_path(path: str) -> str | None:
    parts = urlparse(path).path.strip("/").split("/")
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "contacts" and parts[3] == "messages":
        public_key = str(parts[2]).strip().lower()
        if len(public_key) == 64 and all(char in "0123456789abcdef" for char in public_key):
            return public_key
        raise ValueError("contact key must be 64 hex characters")
    return None


def _parse_channel_slot_path(path: str) -> int | None:
    parts = urlparse(path).path.strip("/").split("/")
    if len(parts) == 3 and parts[0] == "api" and parts[1] == "channels":
        return int(parts[2])
    return None


def _request_path(path: str) -> str:
    return urlparse(path).path or "/"


def _parse_channel_invite(invite: str) -> tuple[str, str]:
  parsed = urlparse(str(invite).strip())
  if parsed.scheme != "meshcore" or parsed.netloc != "channel" or parsed.path != "/add":
    raise ValueError("channel invite must use meshcore://channel/add?name=...&secret=...")
  query = parse_qs(parsed.query)
  name = unquote_plus((query.get("name") or [""])[0]).strip()
  secret_hex = ((query.get("secret") or [""])[0]).strip()
  if not name:
    raise ValueError("channel invite is missing a name")
  if not secret_hex:
    raise ValueError("channel invite is missing a secret")
  return name, secret_hex


def launch_web_app(
    *,
    host: str,
    port: int,
    app_name: str,
    protocol_version: int,
    timeout_seconds: float,
    bind_host: str,
    bind_port: int,
  gateway_link_host: str | None = None,
  gateway_link_port: int | None = None,
  gateway_link_allow_basestation_tx: bool = False,
  gateway_link_service_name: str = "meshcore-pi-live-runtime.service",
) -> int:
    native_config = {
        "host": host,
        "port": port,
        "app_name": app_name,
        "protocol_version": protocol_version,
        "timeout_seconds": timeout_seconds,
    }
    channel_history: dict[int, list[dict[str, Any]]] = {}
    contact_history: dict[str, list[dict[str, Any]]] = {}
    session_broker = NativeSessionBroker(native_config, channel_history, contact_history)
    session_broker.start()
    gateway_link_server: GatewayLinkServer | None = None
    if gateway_link_host and gateway_link_port:
      gateway_link_server = GatewayLinkServer(
        GatewayLinkConfig(
          host=gateway_link_host,
          port=int(gateway_link_port),
          native_host=host,
          native_port=int(port),
          app_name="meshcore-gateway-link",
          protocol_version=int(protocol_version),
          timeout_seconds=float(timeout_seconds),
          allow_basestation_tx=bool(gateway_link_allow_basestation_tx),
          service_name=gateway_link_service_name,
        ),
        broker=session_broker,
      )
      gateway_link_server.start(raise_on_bind_error=False)

    class RequestHandler(BaseHTTPRequestHandler):
        server_version = "MeshCoreUiNative/0.1"

        def do_GET(self) -> None:  # noqa: N802
            try:
                request_path = _request_path(self.path)
                if request_path in {"/", "/index.html"}:
                    self._send_html(HTML_PAGE)
                    return
                if request_path == "/api/events":
                    self._stream_events()
                    return
                if request_path == "/api/node-page":
                    self._send_json(session_broker.collect_node_page())
                    return
                if request_path == "/api/actions/export-contact-code":
                    self._send_json(session_broker.export_contact_code())
                    return
                if request_path == "/api/actions/tools-summary":
                    self._send_json(session_broker.tools_summary())
                    return
                if request_path == "/api/gateway/access":
                  payload = gateway_link_server.get_access_state() if gateway_link_server is not None else {
                    "enabled": False,
                    "gateway_tx_allowed": False,
                    "gateway_access_mode": "disabled",
                    "default_gateway_tx_allowed": False,
                    "runtime_endpoint": "",
                    "link_endpoint": "",
                    "service_name": "",
                    "persistence_note": "Embedded gateway listener is not active in this UI process.",
                  }
                  self._send_json({"ok": True, **payload})
                  return
                contact_key = _parse_contact_messages_path(self.path)
                if contact_key is not None:
                    self._send_json(session_broker.get_contact_messages(contact_key))
                    return
                channel_index = _parse_channel_messages_path(self.path)
                if channel_index is not None:
                    self._send_json(session_broker.get_channel_messages(channel_index))
                    return
                self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            except (CompanionDeviceError, CompanionProtocolError, OSError, ValueError, KeyError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        def do_DELETE(self) -> None:  # noqa: N802
            try:
                request_path = _request_path(self.path)
                contact_key = _parse_contact_messages_path(self.path)
                if contact_key is not None:
                    self._send_json(session_broker.clear_contact_messages(contact_key))
                    return
                channel_index = _parse_channel_slot_path(request_path)
                if channel_index is not None:
                    self._send_json(session_broker.delete_channel(channel_index))
                    return
                self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            except (CompanionDeviceError, CompanionProtocolError, OSError, ValueError, KeyError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        def do_POST(self) -> None:  # noqa: N802
            try:
                request_path = _request_path(self.path)
                body = self._read_json_body()
                contact_key = _parse_contact_messages_path(self.path)
                if contact_key is not None:
                    self._send_json(session_broker.send_contact_message(contact_key, body))
                    return
                channel_index = _parse_channel_messages_path(request_path)
                if channel_index is not None:
                    self._send_json(session_broker.send_channel_message(channel_index, body))
                    return
                channel_slot_index = _parse_channel_slot_path(request_path)
                if channel_slot_index is not None:
                    self._send_json(session_broker.update_channel(channel_slot_index, body))
                    return
                if request_path == "/api/contacts":
                    self._send_json(session_broker.add_contact(body))
                    return
                if request_path == "/api/channels":
                    self._send_json(session_broker.add_channel(body))
                    return
                if request_path == "/api/actions/discover-contacts":
                    self._send_json(session_broker.discover_contacts(body))
                    return
                if request_path == "/api/settings/apply":
                    self._send_json(session_broker.apply_settings(body))
                    return
                if request_path == "/api/settings/name":
                    self._send_json(session_broker.set_name(str(body.get("name") or "")))
                    return
                if request_path == "/api/settings/time":
                    self._send_json(session_broker.set_time(int(body["timestamp"])))
                    return
                if request_path == "/api/settings/location":
                    self._send_json(session_broker.set_location(float(body["lat"]), float(body["lon"])))
                    return
                if request_path == "/api/settings/radio":
                    self._send_json(session_broker.set_radio(body))
                    return
                if request_path == "/api/actions/reboot":
                    self._send_json(session_broker.reboot())
                    return
                if request_path == "/api/gateway/access":
                  if gateway_link_server is None:
                    raise ValueError("Embedded gateway listener is not active in this UI process.")
                  self._send_json({"ok": True, **gateway_link_server.set_allow_basestation_tx(bool(body.get("allow_basestation_tx")))})
                  return
                self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            except (CompanionDeviceError, CompanionProtocolError, OSError, ValueError, KeyError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _stream_events(self) -> None:
            last_event_id_header = self.headers.get("Last-Event-ID") or "0"
            try:
                last_event_id = int(last_event_id_header)
            except ValueError:
                last_event_id = 0

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                while True:
                    events = session_broker.wait_for_events(last_event_id, timeout_seconds=15.0)
                    if not events:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                        continue
                    for event in events:
                        frame = (
                            f"id: {event['id']}\n"
                            f"event: {event['type']}\n"
                            f"data: {json.dumps(event['data'])}\n\n"
                        ).encode("utf-8")
                        self.wfile.write(frame)
                        self.wfile.flush()
                        last_event_id = int(event["id"])
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return

        def _read_json_body(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("request body must be a JSON object")
            return parsed

        def _send_html(self, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer((bind_host, bind_port), RequestHandler)
    print(f"MeshCore browser UI listening on http://{bind_host}:{bind_port}/")
    print(f"Native companion target: {host}:{port}")
    try:
      server.serve_forever()
    except KeyboardInterrupt:
      return 0
    finally:
      if gateway_link_server is not None:
        gateway_link_server.stop()
      session_broker.stop()
      server.server_close()
    return 0
