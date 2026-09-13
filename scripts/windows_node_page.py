from __future__ import annotations

from dataclasses import asdict, dataclass
from html import escape
from typing import Any


@dataclass(frozen=True, slots=True)
class NodeIdentityCard:
  display_name: str
  local_id: str
  status: str
  connected: bool
  model: str
  firmware_version: str
  firmware_build: str
  public_key: str | None
  observed_nodes_count: int


@dataclass(frozen=True, slots=True)
class RadioCard:
  tx_power_dbm: int | None
  freq_mhz: float | None
  bw_khz: float | None
  sf: int | None
  cr: int | None
  advert_loc_policy: int | None
  telemetry_mode_base: int | None
  telemetry_mode_loc: int | None
  telemetry_mode_env: int | None


@dataclass(frozen=True, slots=True)
class RuntimeCard:
  interface_mode: str
  transport: str
  runtime_endpoint: str
  link_endpoint: str
  transport_ready: bool
  service_state: str
  gateway_tx_allowed: bool
  browser_send_allowed: bool
  helper_tx_allowed: bool


@dataclass(frozen=True, slots=True)
class AccessCard:
  overall_state: str
  runtime_state: str
  gateway_tx_state: str
  browser_send_state: str
  helper_send_state: str


@dataclass(frozen=True, slots=True)
class BatteryCard:
  battery_mv: int | None
  total_kb: int | None
  used_kb: int | None


@dataclass(frozen=True, slots=True)
class CapabilityCard:
  ble_pin: int | None
  client_repeat: int | None
  path_hash_mode: int | None
  gps_enabled: bool | None
  gps_interval_s: int | None
  max_contacts: int | None
  max_channels: int | None


@dataclass(frozen=True, slots=True)
class ComposeActionCard:
  send_allowed: bool
  target_count: int
  default_target_public_key: str | None
  default_target_name: str | None
  status_text: str


def _as_dict(value: Any) -> dict[str, Any]:
  return value if isinstance(value, dict) else {}


def _to_bool(value: Any) -> bool:
  return bool(value)


def _service_state_label(service: dict[str, Any]) -> str:
  active_state = str(service.get("active_state") or "").strip()
  sub_state = str(service.get("sub_state") or "").strip()
  if active_state and sub_state and sub_state != active_state:
    return f"{active_state}:{sub_state}"
  if active_state:
    return active_state
  return "unknown"


def _access_state(connected: bool, transport_ready: bool, gateway_tx_allowed: bool) -> str:
  if not connected:
    return "Disconnected"
  if not transport_ready:
    return "Connected, runtime unavailable"
  if gateway_tx_allowed:
    return "Connected, writes enabled"
  return "Connected, writes disabled"


def build_node_page_model(
  snapshot_result: dict[str, Any],
  device_result: dict[str, Any],
  channels_result: dict[str, Any],
  observed_nodes_result: dict[str, Any],
) -> dict[str, Any]:
  snapshot = _as_dict(snapshot_result.get("snapshot"))
  device = _as_dict(device_result.get("device"))
  device_query = _as_dict(snapshot.get("device_query") or device.get("device_query"))
  identity = _as_dict(snapshot.get("identity"))
  runtime_status = _as_dict(snapshot.get("runtime_status"))
  battery = _as_dict(snapshot.get("battery") or device.get("battery"))
  channels = channels_result.get("channels") if isinstance(channels_result.get("channels"), list) else []
  observed_nodes = (
    observed_nodes_result.get("observed_nodes")
    if isinstance(observed_nodes_result.get("observed_nodes"), list)
    else []
  )
  reachable_nodes = [node for node in observed_nodes if isinstance(node, dict) and node.get("public_key")]
  default_target = reachable_nodes[0] if reachable_nodes else None
  gateway_tx_allowed = _to_bool(runtime_status.get("gateway_tx_allowed"))
  transport_ready = _to_bool(runtime_status.get("transport_ready"))
  connected = _to_bool(snapshot.get("connected"))
  service_state = _service_state_label(_as_dict(runtime_status.get("service")))
  browser_send_allowed = _to_bool(runtime_status.get("browser_send_allowed"))
  helper_tx_allowed = _to_bool(runtime_status.get("helper_tx_allowed"))

  model = {
    "identity": asdict(
      NodeIdentityCard(
        display_name=str(snapshot.get("display_name") or identity.get("display_name") or "MeshCore Node"),
        local_id=str(identity.get("local_id") or ""),
        status=str(snapshot.get("status") or "unknown"),
        connected=connected,
        model=str(device_query.get("model") or "Unknown model"),
        firmware_version=str(device_query.get("version") or "Unknown version"),
        firmware_build=str(device_query.get("firmware_build") or "Unknown build"),
        public_key=str(identity.get("public_key")) if identity.get("public_key") else None,
        observed_nodes_count=int(snapshot.get("observed_nodes_count") or len(observed_nodes)),
      )
    ),
    "radio": asdict(
      RadioCard(
        tx_power_dbm=int(runtime_status.get("tx_power_dbm")) if runtime_status.get("tx_power_dbm") is not None else None,
        freq_mhz=float(runtime_status.get("freq_mhz")) if runtime_status.get("freq_mhz") is not None else None,
        bw_khz=float(runtime_status.get("bw_khz")) if runtime_status.get("bw_khz") is not None else None,
        sf=int(runtime_status.get("sf")) if runtime_status.get("sf") is not None else None,
        cr=int(runtime_status.get("cr")) if runtime_status.get("cr") is not None else None,
        advert_loc_policy=int(identity.get("advert_loc_policy")) if identity.get("advert_loc_policy") is not None else None,
        telemetry_mode_base=int(identity.get("telemetry_mode_base")) if identity.get("telemetry_mode_base") is not None else None,
        telemetry_mode_loc=int(identity.get("telemetry_mode_loc")) if identity.get("telemetry_mode_loc") is not None else None,
        telemetry_mode_env=int(identity.get("telemetry_mode_env")) if identity.get("telemetry_mode_env") is not None else None,
      )
    ),
    "runtime": asdict(
      RuntimeCard(
        interface_mode=str(runtime_status.get("interface_mode") or "unknown"),
        transport=str(runtime_status.get("transport") or "unknown"),
        runtime_endpoint=str(runtime_status.get("runtime_endpoint") or ""),
        link_endpoint=str(runtime_status.get("link_endpoint") or ""),
        transport_ready=transport_ready,
        service_state=service_state,
        gateway_tx_allowed=gateway_tx_allowed,
        browser_send_allowed=browser_send_allowed,
        helper_tx_allowed=helper_tx_allowed,
      )
    ),
    "access": asdict(
      AccessCard(
        overall_state=_access_state(connected, transport_ready, gateway_tx_allowed),
        runtime_state="Ready" if transport_ready else "Unavailable",
        gateway_tx_state="Writes enabled" if gateway_tx_allowed else "Writes disabled",
        browser_send_state="Allowed" if browser_send_allowed else "Hidden",
        helper_send_state="Allowed" if helper_tx_allowed else "Blocked",
      )
    ),
    "battery": asdict(
      BatteryCard(
        battery_mv=int(battery.get("battery_mv")) if battery.get("battery_mv") is not None else None,
        total_kb=int(battery.get("total_kb")) if battery.get("total_kb") is not None else None,
        used_kb=int(battery.get("used_kb")) if battery.get("used_kb") is not None else None,
      )
    ),
    "capabilities": asdict(
      CapabilityCard(
        ble_pin=int(identity.get("ble_pin") or device_query.get("ble_pin")) if (identity.get("ble_pin") or device_query.get("ble_pin")) is not None else None,
        client_repeat=int(identity.get("client_repeat") or device_query.get("client_repeat")) if (identity.get("client_repeat") or device_query.get("client_repeat")) is not None else None,
        path_hash_mode=int(device_query.get("path_hash_mode")) if device_query.get("path_hash_mode") is not None else None,
        gps_enabled=bool(identity.get("gps_enabled")) if identity.get("gps_enabled") is not None else None,
        gps_interval_s=int(identity.get("gps_interval_s")) if identity.get("gps_interval_s") is not None else None,
        max_contacts=int(device_query.get("max_contacts")) if device_query.get("max_contacts") is not None else None,
        max_channels=int(device_query.get("max_channels")) if device_query.get("max_channels") is not None else None,
      )
    ),
    "compose": asdict(
      ComposeActionCard(
        send_allowed=gateway_tx_allowed and bool(reachable_nodes),
        target_count=len(reachable_nodes),
        default_target_public_key=(str(default_target.get("public_key")) if default_target else None),
        default_target_name=(
          str(default_target.get("display_name") or default_target.get("short_name") or "") if default_target else None
        ),
        status_text=(
          "Ready to send directed private messages"
          if gateway_tx_allowed and reachable_nodes
          else "Waiting for a reachable target or TX permission"
        ),
      )
    ),
    "channels": channels,
    "observed_nodes": observed_nodes,
  }
  return model


def _fmt(value: Any, suffix: str = "") -> str:
  if value is None or value == "":
    return "Unavailable"
  return f"{value}{suffix}"


def render_node_page_html(model: dict[str, Any]) -> str:
  identity = _as_dict(model.get("identity"))
  radio = _as_dict(model.get("radio"))
  runtime = _as_dict(model.get("runtime"))
  access = _as_dict(model.get("access"))
  battery = _as_dict(model.get("battery"))
  capabilities = _as_dict(model.get("capabilities"))
  compose = _as_dict(model.get("compose"))
  channels = model.get("channels") if isinstance(model.get("channels"), list) else []
  observed_nodes = model.get("observed_nodes") if isinstance(model.get("observed_nodes"), list) else []

  hero_state = "Connected" if identity.get("connected") else "Disconnected"
  if identity.get("connected") and not runtime.get("transport_ready"):
    hero_state = "Degraded"
  elif identity.get("connected") and not runtime.get("gateway_tx_allowed"):
    hero_state = "Connected, writes disabled"

  channel_cards = "".join(
    (
      "<li><strong>"
      + escape(str(channel.get("name") or f"Channel {channel.get('index', '?')}"))
      + "</strong><span>"
      + escape("Gateway send allowed" if channel.get("gateway_send_allowed") else "Read only")
      + "</span></li>"
    )
    for channel in channels
    if isinstance(channel, dict) and not channel.get("is_empty")
  ) or "<li><strong>No provisioned channels</strong><span>Empty</span></li>"

  observed_cards = "".join(
    (
      "<li><strong>"
      + escape(str(node.get("display_name") or node.get("short_name") or "Unknown node"))
      + "</strong><span>"
      + escape(str(node.get("presence_state") or "unknown"))
      + "</span></li>"
    )
    for node in observed_nodes
    if isinstance(node, dict)
  ) or "<li><strong>No observed nodes</strong><span>Waiting</span></li>"

  return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(identity.get("display_name") or "MeshCore Node"))}</title>
  <style>
  :root {{
    --ink: #0e1a24;
    --paper: #f4efe5;
    --panel: #fffaf2;
    --accent: #0f766e;
    --accent-soft: #d7f2eb;
    --warn: #8a5a00;
    --line: #d8cdb9;
    --muted: #5f6b73;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: Georgia, 'Times New Roman', serif; color: var(--ink); background:
    radial-gradient(circle at top left, #fff6d8 0, transparent 32%),
    linear-gradient(135deg, #efe4ce 0%, #f8f4ea 55%, #e8efe9 100%); }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 56px; }}
  .hero {{ display: grid; gap: 18px; padding: 24px; background: rgba(255,250,242,0.9); border: 1px solid var(--line); border-radius: 24px; box-shadow: 0 18px 40px rgba(14,26,36,0.08); }}
  h1, h2 {{ margin: 0; font-weight: 600; }}
  h1 {{ font-size: clamp(2rem, 5vw, 3.5rem); }}
  .status {{ display: inline-flex; align-items: center; gap: 10px; width: fit-content; padding: 8px 14px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-size: 0.95rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 18px; }}
  .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 18px; }}
  .eyebrow {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.75rem; margin-bottom: 10px; }}
  dl {{ margin: 0; display: grid; grid-template-columns: 1fr auto; gap: 8px 12px; }}
  dt {{ color: var(--muted); }}
  dd {{ margin: 0; font-weight: 600; text-align: right; }}
  ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
  li {{ display: flex; justify-content: space-between; gap: 12px; padding: 12px 14px; border-radius: 14px; background: #fff; border: 1px solid #efe4d1; }}
  li span {{ color: var(--muted); text-align: right; }}
  </style>
</head>
<body>
  <main>
  <section class="hero">
    <div class="status">{hero_state} · {escape(str(identity.get("status") or "unknown"))}</div>
    <div>
    <h1>{escape(str(identity.get("display_name") or "MeshCore Node"))}</h1>
    <p>{escape(str(identity.get("model") or "Unknown model"))} · {escape(str(identity.get("firmware_version") or "Unknown version"))} · build {escape(str(identity.get("firmware_build") or "Unknown build"))}</p>
    </div>
  </section>
  <section class="grid">
    <article class="card"><div class="eyebrow">Identity</div><dl>
    <dt>Local ID</dt><dd>{escape(_fmt(identity.get("local_id")))}</dd>
    <dt>Observed Nodes</dt><dd>{escape(_fmt(identity.get("observed_nodes_count")))}</dd>
    <dt>Public Key</dt><dd>{escape(_fmt(identity.get("public_key")))}</dd>
    </dl></article>
    <article class="card"><div class="eyebrow">Radio</div><dl>
    <dt>TX Power</dt><dd>{escape(_fmt(radio.get("tx_power_dbm"), " dBm"))}</dd>
    <dt>Frequency</dt><dd>{escape(_fmt(radio.get("freq_mhz"), " MHz"))}</dd>
    <dt>Bandwidth</dt><dd>{escape(_fmt(radio.get("bw_khz"), " kHz"))}</dd>
    <dt>SF / CR</dt><dd>{escape(_fmt(radio.get("sf")))} / {escape(_fmt(radio.get("cr")))}</dd>
    </dl></article>
    <article class="card"><div class="eyebrow">Runtime</div><dl>
    <dt>Mode</dt><dd>{escape(_fmt(runtime.get("interface_mode")))}</dd>
    <dt>Transport</dt><dd>{escape(_fmt(runtime.get("transport")))}</dd>
    <dt>Endpoint</dt><dd>{escape(_fmt(runtime.get("runtime_endpoint")))}</dd>
    <dt>Link</dt><dd>{escape(_fmt(runtime.get("link_endpoint")))}</dd>
    <dt>Service</dt><dd>{escape(_fmt(runtime.get("service_state")))}</dd>
    </dl></article>
    <article class="card"><div class="eyebrow">Access</div><dl>
    <dt>Overall</dt><dd>{escape(_fmt(access.get("overall_state")))}</dd>
    <dt>Runtime</dt><dd>{escape(_fmt(access.get("runtime_state")))}</dd>
    <dt>Gateway TX</dt><dd>{escape(_fmt(access.get("gateway_tx_state")))}</dd>
    <dt>Browser Send</dt><dd>{escape(_fmt(access.get("browser_send_state")))}</dd>
    <dt>Helper Send</dt><dd>{escape(_fmt(access.get("helper_send_state")))}</dd>
    </dl></article>
    <article class="card"><div class="eyebrow">Capabilities</div><dl>
    <dt>BLE PIN</dt><dd>{escape(_fmt(capabilities.get("ble_pin")))}</dd>
    <dt>GPS Enabled</dt><dd>{escape(_fmt(capabilities.get("gps_enabled")))}</dd>
    <dt>GPS Interval</dt><dd>{escape(_fmt(capabilities.get("gps_interval_s"), " s"))}</dd>
    <dt>Max Contacts / Channels</dt><dd>{escape(_fmt(capabilities.get("max_contacts")))} / {escape(_fmt(capabilities.get("max_channels")))}</dd>
    </dl></article>
    <article class="card"><div class="eyebrow">Battery</div><dl>
    <dt>Battery</dt><dd>{escape(_fmt(battery.get("battery_mv"), " mV"))}</dd>
    <dt>Storage Used</dt><dd>{escape(_fmt(battery.get("used_kb"), " KB"))}</dd>
    <dt>Storage Total</dt><dd>{escape(_fmt(battery.get("total_kb"), " KB"))}</dd>
    </dl></article>
    <article class="card"><div class="eyebrow">Compose</div><dl>
    <dt>Status</dt><dd>{escape(_fmt(compose.get("status_text")))}</dd>
    <dt>Send Allowed</dt><dd>{escape('Yes' if compose.get("send_allowed") else 'No')}</dd>
    <dt>Targets</dt><dd>{escape(_fmt(compose.get("target_count")))}</dd>
    <dt>Default Target</dt><dd>{escape(_fmt(compose.get("default_target_name")))}</dd>
    </dl></article>
    <article class="card"><div class="eyebrow">Channels</div><ul>{channel_cards}</ul></article>
    <article class="card"><div class="eyebrow">Observed Nodes</div><ul>{observed_cards}</ul></article>
  </section>
  </main>
</body>
</html>
'''


def build_directed_private_message_request(model: dict[str, Any], text: str, *, public_key: str | None = None) -> dict[str, str]:
  compose = _as_dict(model.get("compose"))
  if not compose.get("send_allowed"):
    raise ValueError("directed private send is not currently available")
  target_public_key = str(public_key or compose.get("default_target_public_key") or "").strip()
  if not target_public_key:
    raise ValueError("no target public key is available for directed private send")
  message_text = str(text).strip()
  if not message_text:
    raise ValueError("directed private message text must not be empty")
  return {
    "public_key": target_public_key,
    "text": message_text,
  }
