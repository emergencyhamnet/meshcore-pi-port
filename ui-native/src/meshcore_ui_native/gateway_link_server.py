from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import json
import os
import socket
import subprocess
import threading
from typing import Any, Protocol
from uuid import uuid4

from .native_session_broker import NativeSessionBroker


PROTOCOL_VERSION = "ehn-gateway-link/1"
DEFAULT_APP_NAME = "meshcore-gateway-link"
DEFAULT_PROTOCOL_VERSION = 3


@dataclass(frozen=True, slots=True)
class GatewayLinkEnvelope:
    version: str
    type: str
    id: str | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    ok: bool | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "version": self.version,
            "type": self.type,
        }
        optional_fields = {
            "id": self.id,
            "method": self.method,
            "params": self.params,
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value
        return payload

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GatewayLinkEnvelope:
        return cls(
            version=str(payload.get("version") or "").strip(),
            type=str(payload.get("type") or "").strip(),
            id=str(payload.get("id") or "").strip() or None,
            method=str(payload.get("method") or "").strip() or None,
            params=payload.get("params") if isinstance(payload.get("params"), dict) else None,
            ok=payload.get("ok") if isinstance(payload.get("ok"), bool) else None,
            result=payload.get("result") if isinstance(payload.get("result"), dict) else None,
            error=payload.get("error") if isinstance(payload.get("error"), dict) else None,
        )


def encode_gateway_link_frame(envelope: GatewayLinkEnvelope) -> bytes:
    payload = envelope.to_json_bytes()
    return len(payload).to_bytes(4, byteorder="big", signed=False) + payload


def decode_gateway_link_frame(frame: bytes) -> GatewayLinkEnvelope:
    if len(frame) < 4:
        raise ValueError("Gateway-link frame is too short.")
    payload_length = int.from_bytes(frame[:4], byteorder="big", signed=False)
    payload = frame[4:]
    if len(payload) != payload_length:
        raise ValueError("Gateway-link frame length does not match payload size.")
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Gateway-link payload must decode to a JSON object.")
    return GatewayLinkEnvelope.from_dict(data)


def iso_utc(timestamp: int | float | None = None) -> str:
    if timestamp:
        return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def read_service_properties(service_name: str) -> dict[str, Any]:
    command = [
        "systemctl",
        "show",
        service_name,
        "--no-pager",
        "--property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp,FragmentPath,UnitFileState",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "error": str(exc),
            "active": False,
        }

    info: dict[str, Any] = {
        "available": result.returncode == 0,
        "command": " ".join(command),
        "stderr": result.stderr.strip(),
    }
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        info[key] = value
    info["active"] = info.get("ActiveState") == "active"
    return info


def mask_secret(secret_hex: str) -> str:
    clean = str(secret_hex or "").strip()
    if len(clean) < 16:
        return clean
    return f"{clean[:8]}...{clean[-8:]}"


def _is_empty_channel_slot(name: str, secret_hex: str) -> bool:
    clean_name = str(name or "").strip()
    clean_secret = str(secret_hex or "").strip().lower()
    return not clean_name and (not clean_secret or all(char == "0" for char in clean_secret))


class GatewayLinkBroker(Protocol):
    def collect_session_snapshot(self) -> dict[str, Any]: ...

    def list_activity(self, *, limit: int = 50, direction: str | None = None) -> list[dict[str, Any]]: ...

    def tools_summary(self) -> dict[str, Any]: ...

    def send_contact_message(self, public_key: str, body: dict[str, Any]) -> dict[str, Any]: ...

    def send_channel_message(self, channel_index: int, body: dict[str, Any]) -> dict[str, Any]: ...

    def set_tx_power(self, tx_power_dbm: int) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class GatewayLinkConfig:
    host: str
    port: int
    native_host: str
    native_port: int
    app_name: str
    protocol_version: int
    timeout_seconds: float
    allow_basestation_tx: bool
    service_name: str

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> GatewayLinkConfig:
        return cls(
            host=str(args.host).strip() or "0.0.0.0",
            port=int(args.port),
            native_host=str(args.native_host).strip() or "127.0.0.1",
            native_port=int(args.native_port),
            app_name=str(args.app_name).strip() or DEFAULT_APP_NAME,
            protocol_version=int(args.protocol_version),
            timeout_seconds=float(args.timeout),
            allow_basestation_tx=_env_flag(args.allow_basestation_tx),
            service_name=str(args.service_name).strip() or "meshcore-pi-live-runtime.service",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the MeshCore Pi basestation gateway-link over a persistent native session broker.")
    parser.add_argument("--host", default=os.environ.get("MESHCORE_PI_GATEWAY_LINK_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MESHCORE_PI_GATEWAY_LINK_PORT", "7463")))
    parser.add_argument("--native-host", default=os.environ.get("MESHCORE_PI_GATEWAY_LINK_NATIVE_HOST", "127.0.0.1"))
    parser.add_argument("--native-port", type=int, default=int(os.environ.get("MESHCORE_PI_GATEWAY_LINK_NATIVE_PORT", "5040")))
    parser.add_argument("--app-name", default=os.environ.get("MESHCORE_PI_GATEWAY_LINK_APP_NAME", DEFAULT_APP_NAME))
    parser.add_argument("--protocol-version", type=int, default=int(os.environ.get("MESHCORE_PI_GATEWAY_LINK_PROTOCOL_VERSION", str(DEFAULT_PROTOCOL_VERSION))))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("MESHCORE_PI_GATEWAY_LINK_TIMEOUT_SECONDS", "5.0")))
    parser.add_argument("--service-name", default=os.environ.get("MESHCORE_PI_LIVE_RUNTIME_SERVICE", "meshcore-pi-live-runtime.service"))
    parser.add_argument("--allow-basestation-tx", default=os.environ.get("MESHCORE_PI_GATEWAY_LINK_ALLOW_TX", "1"))
    return parser.parse_args()


def _env_flag(value: object) -> bool:
    return str(value or "").strip().lower() not in {"", "0", "false", "no", "off"}


def build_native_session_broker(config: GatewayLinkConfig) -> NativeSessionBroker:
    native_config = {
        "host": config.native_host,
        "port": config.native_port,
        "app_name": config.app_name,
        "protocol_version": config.protocol_version,
        "timeout_seconds": config.timeout_seconds,
    }
    return NativeSessionBroker(native_config, {}, {})


class GatewayLinkService:
    def __init__(self, config: GatewayLinkConfig, broker: GatewayLinkBroker) -> None:
        self._config = config
        self._broker = broker
        self._outbound_requests: list[dict[str, Any]] = []
        self._outbound_lock = threading.RLock()
        self._policy_lock = threading.RLock()
        self._allow_basestation_tx = bool(config.allow_basestation_tx)

    def current_allow_basestation_tx(self) -> bool:
        with self._policy_lock:
            return self._allow_basestation_tx

    def get_access_state(self) -> dict[str, Any]:
        allow_basestation_tx = self.current_allow_basestation_tx()
        return {
            "enabled": True,
            "gateway_tx_allowed": allow_basestation_tx,
            "gateway_access_mode": "transmit-enabled" if allow_basestation_tx else "read-only",
            "default_gateway_tx_allowed": bool(self._config.allow_basestation_tx),
            "runtime_endpoint": f"tcp://{self._config.native_host}:{self._config.native_port}",
            "link_endpoint": f"tcp://{self._config.host}:{self._config.port}",
            "service_name": self._config.service_name,
            "persistence_note": "Applies to the running browser UI process. Restart returns to the service default.",
        }

    def set_allow_basestation_tx(self, allow_basestation_tx: bool) -> dict[str, Any]:
        with self._policy_lock:
            self._allow_basestation_tx = bool(allow_basestation_tx)
        return self.get_access_state()

    def dispatch(self, envelope: GatewayLinkEnvelope) -> GatewayLinkEnvelope:
        if envelope.type != "request":
            return self._error_response(envelope, "Gateway link only accepts request envelopes.")
        if envelope.version != PROTOCOL_VERSION:
            return self._error_response(envelope, f"Unsupported gateway-link version {envelope.version!r}.")

        try:
            result = self._dispatch_method(envelope.method or "", dict(envelope.params or {}))
        except Exception as exc:
            return GatewayLinkEnvelope(
                version=PROTOCOL_VERSION,
                type="response",
                id=envelope.id,
                ok=False,
                error={"message": str(exc)},
            )

        return GatewayLinkEnvelope(
            version=PROTOCOL_VERSION,
            type="response",
            id=envelope.id,
            ok=True,
            result=result,
        )

    def _dispatch_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "get_snapshot":
            return {"snapshot": self.get_snapshot()}
        if method == "get_access_state":
            return {"access": self.get_access_state()}
        if method == "list_channels":
            return {"channels": self.list_channels()}
        if method == "list_observed_nodes":
            return {"observed_nodes": self.list_observed_nodes()}
        if method == "list_gateway_inbound_events":
            return {"events": self.list_gateway_inbound_events(limit=int(params.get("limit", 50) or 50))}
        if method == "list_gateway_outbound_status":
            return {
                "requests": self.list_gateway_outbound_status(
                    limit=int(params.get("limit", 50) or 50),
                    state=str(params.get("state") or "").strip() or None,
                )
            }
        if method == "get_device_details":
            return {"device": self.get_device_details()}
        if method == "send_directed_private_message":
            return self.send_directed_private_message(params)
        if method == "send_channel_message":
            return self.send_channel_message(params)
        if method == "set_tx_power":
            return self.set_tx_power(params)
        raise ValueError(f"Unsupported gateway-link method {method!r}.")

    def get_snapshot(self) -> dict[str, Any]:
        try:
            snapshot = self._broker.collect_session_snapshot()
        except Exception as exc:
            return self._unreachable_snapshot(str(exc))

        allow_basestation_tx = self.current_allow_basestation_tx()

        self_info = snapshot.get("self_info") if isinstance(snapshot.get("self_info"), dict) else {}
        device_info = snapshot.get("device_info") if isinstance(snapshot.get("device_info"), dict) else {}
        custom_vars = snapshot.get("custom_vars") if isinstance(snapshot.get("custom_vars"), dict) else {}
        service = read_service_properties(self._config.service_name)
        identity_name = str(self_info.get("name") or "meshcore-pi-node").strip() or "meshcore-pi-node"
        return {
            "connected": True,
            "status": "connected",
            "gateway_id": "meshcore-gateway-1",
            "display_name": identity_name,
            "runtime_name": "meshcore-native-gateway-link",
            "runtime_version": str(device_info.get("version") or "").strip() or None,
            "contract_version": "1.0",
            "identity": {
                "local_id": identity_name,
                "display_name": identity_name,
                "short_name": identity_name,
                "public_key": str(self_info.get("public_key") or "").strip() or None,
                "identity_loaded": True,
                "lat": self_info.get("adv_lat"),
                "lon": self_info.get("adv_lon"),
                "telemetry_mode_base": self_info.get("telemetry_mode_base"),
                "telemetry_mode_loc": self_info.get("telemetry_mode_loc"),
                "telemetry_mode_env": self_info.get("telemetry_mode_env"),
                "advert_loc_policy": self_info.get("advert_loc_policy"),
                "ble_pin": device_info.get("ble_pin"),
                "gps_enabled": custom_vars.get("gps"),
                "gps_interval_s": custom_vars.get("gps_interval"),
                "client_repeat": device_info.get("client_repeat"),
                "tx_power_dbm": self_info.get("tx_power"),
                "tx_power_max_dbm": self_info.get("max_tx_power"),
                "path_hash_mode": device_info.get("path_hash_mode"),
            },
            "runtime_status": {
                "transport": "meshcore-gateway-link",
                "source_kind": "native-session-broker",
                "interface_mode": "gateway-link",
                "gateway_tx_allowed": allow_basestation_tx,
                "transport_ready": True,
                "runtime_endpoint": f"tcp://{self._config.native_host}:{self._config.native_port}",
                "link_carrier": "tcp",
                "link_endpoint": f"{self._config.host}:{self._config.port}",
                "link_version": PROTOCOL_VERSION,
                "service": service,
                "freq_mhz": self_info.get("radio_freq_mhz"),
                "sf": self_info.get("radio_sf"),
                "cr": self_info.get("radio_cr"),
                "bw_khz": self_info.get("radio_bw_khz"),
                "tx_power_dbm": self_info.get("tx_power"),
                "tx_power_max_dbm": self_info.get("max_tx_power"),
                "path_hash_mode": device_info.get("path_hash_mode"),
                "client_repeat": device_info.get("client_repeat"),
                "max_contacts": device_info.get("max_contacts"),
                "max_channels": device_info.get("max_channels"),
            },
            "device_query": {
                "model": device_info.get("model"),
                "firmware_build": device_info.get("firmware_build"),
                "version": device_info.get("version"),
                "client_repeat": device_info.get("client_repeat"),
                "path_hash_mode": device_info.get("path_hash_mode"),
                "max_contacts": device_info.get("max_contacts"),
                "max_channels": device_info.get("max_channels"),
            },
            "battery": snapshot.get("battery") if isinstance(snapshot.get("battery"), dict) else {},
            "custom_vars": custom_vars,
            "last_error": None,
        }

    def list_channels(self) -> list[dict[str, Any]]:
        snapshot = self._broker.collect_session_snapshot()
        raw_channels = snapshot.get("channels") if isinstance(snapshot.get("channels"), list) else []
        channels: list[dict[str, Any]] = []
        for index, channel in enumerate(raw_channels):
            if isinstance(channel, dict):
                secret_hex = str(channel.get("secret_hex") or "").strip()
                name = str(channel.get("name") or "").strip()
                is_empty = _is_empty_channel_slot(name, secret_hex)
            else:
                secret_hex = ""
                name = ""
                is_empty = True
            channels.append(
                {
                    "index": index,
                    "name": name or ("public" if index == 0 else ""),
                    "secret_hex": secret_hex,
                    "secret_preview": mask_secret(secret_hex),
                    "is_empty": is_empty,
                    "browser_send_allowed": False,
                    "gateway_send_allowed": self.current_allow_basestation_tx(),
                }
            )
        return channels

    def list_observed_nodes(self) -> list[dict[str, Any]]:
        snapshot = self._broker.collect_session_snapshot()
        contacts = snapshot.get("contacts") if isinstance(snapshot.get("contacts"), list) else []
        observed_nodes: list[dict[str, Any]] = []
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            public_key = str(contact.get("public_key") or "").strip() or None
            if not public_key:
                continue
            last_seen_at = iso_utc(contact.get("lastmod") or contact.get("last_advert_timestamp"))
            observed_nodes.append(
                {
                    "node_id": f"meshcore:{public_key[:12]}",
                    "public_key": public_key,
                    "native_address": public_key,
                    "contact_name": str(contact.get("name") or public_key[:12]),
                    "display_name": str(contact.get("name") or public_key[:12]),
                    "short_name": str(contact.get("name") or public_key[:12]),
                    "last_seen_at": last_seen_at,
                    "last_advert_utc": iso_utc(contact.get("last_advert_timestamp")),
                    "observed_at": last_seen_at,
                    "presence_state": "MESH_ACTIVE",
                    "last_channel_name": "Primary Public",
                    "gps_lat": contact.get("gps_lat"),
                    "gps_lon": contact.get("gps_lon"),
                    "path_len": contact.get("out_path_len"),
                }
            )
        return observed_nodes

    def list_gateway_inbound_events(self, *, limit: int) -> list[dict[str, Any]]:
        return self._broker.list_activity(limit=limit, direction="incoming")

    def list_gateway_outbound_status(self, *, limit: int, state: str | None) -> list[dict[str, Any]]:
        with self._outbound_lock:
            rows = list(self._outbound_requests)
        if state:
            rows = [row for row in rows if str(row.get("state") or "").strip().lower() == state.lower()]
        rows.sort(key=lambda row: str(row.get("updated_at") or row.get("requested_at") or ""), reverse=True)
        return rows[: max(1, int(limit))]

    def get_device_details(self) -> dict[str, Any]:
        snapshot = self._broker.collect_session_snapshot()
        self_info = snapshot.get("self_info") if isinstance(snapshot.get("self_info"), dict) else {}
        device_info = snapshot.get("device_info") if isinstance(snapshot.get("device_info"), dict) else {}
        battery = snapshot.get("battery") if isinstance(snapshot.get("battery"), dict) else {}
        custom_vars = snapshot.get("custom_vars") if isinstance(snapshot.get("custom_vars"), dict) else {}
        tools = self._broker.tools_summary()
        return {
            "device_query": {
                "model": device_info.get("model"),
                "firmware_build": device_info.get("firmware_build"),
                "version": device_info.get("version"),
                "client_repeat": device_info.get("client_repeat"),
                "path_hash_mode": device_info.get("path_hash_mode"),
                "max_contacts": device_info.get("max_contacts"),
                "max_channels": device_info.get("max_channels"),
            },
            "self_info": self_info,
            "battery": battery,
            "stats": {
                "core": tools.get("core") if isinstance(tools.get("core"), dict) else {},
                "radio": tools.get("radio") if isinstance(tools.get("radio"), dict) else {},
                "packets": tools.get("packets") if isinstance(tools.get("packets"), dict) else {},
            },
            "custom_vars": custom_vars,
            "gps_mode": custom_vars.get("gps_mode") or None,
            "gps_supported": custom_vars.get("gps") is not None,
        }

    def send_directed_private_message(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.current_allow_basestation_tx():
            raise ValueError("Basestation-directed transmit is disabled for this gateway-link server.")
        recipient_public_key = str(params.get("recipient_public_key") or "").strip().lower()
        text = str(params.get("text") or "").strip()
        delivery_id = str(params.get("delivery_id") or "").strip() or None
        sender_identity = dict(params.get("sender_identity") if isinstance(params.get("sender_identity"), dict) else {})
        destination_identity = dict(params.get("destination_identity") if isinstance(params.get("destination_identity"), dict) else {})
        reply_context = dict(params.get("reply_context") if isinstance(params.get("reply_context"), dict) else {})
        if len(recipient_public_key) != 64:
            raise ValueError("recipient_public_key must be 64 hex characters")
        if not text:
            raise ValueError("text is required")
        requested_at = iso_utc()
        broker_result = self._broker.send_contact_message(recipient_public_key, {"text": text})
        accepted = bool(broker_result.get("ok"))
        record = {
            "request_id": delivery_id or f"gwreq-{uuid4()}",
            "gateway_id": "meshcore-gateway-1",
            "network": "meshcore",
            "message_class": "directed_private",
            "requested_at": requested_at,
            "updated_at": iso_utc(),
            "state": "sent" if accepted else "failed",
            "accepted": accepted,
            "destination": {
                "public_key": recipient_public_key,
                "native_address": recipient_public_key,
            },
            "source_identity": sender_identity,
            "destination_identity": destination_identity,
            "reply_context": reply_context,
            "target_user_id": str(reply_context.get("target_user_id") or destination_identity.get("user_id") or "").strip() or None,
            "payload": {"text": text},
            "response": broker_result,
        }
        self._remember_outbound(record)
        return {
            "accepted": accepted,
            "message": "Directed private message accepted by MeshCore gateway link." if accepted else "Directed private message rejected by MeshCore gateway link.",
            "payload": record,
        }

    def send_channel_message(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.current_allow_basestation_tx():
            raise ValueError("Basestation-directed transmit is disabled for this gateway-link server.")
        channel_index = int(params.get("channel_index") or 0)
        text = str(params.get("text") or "").strip()
        delivery_id = str(params.get("delivery_id") or "").strip() or None
        if channel_index < 0:
            raise ValueError("channel_index must be non-negative")
        if not text:
            raise ValueError("text is required")
        requested_at = iso_utc()
        broker_result = self._broker.send_channel_message(channel_index, {"text": text})
        accepted = bool(broker_result.get("ok"))
        record = {
            "request_id": delivery_id or f"gwreq-{uuid4()}",
            "gateway_id": "meshcore-gateway-1",
            "network": "meshcore",
            "message_class": "channel",
            "requested_at": requested_at,
            "updated_at": iso_utc(),
            "state": "accepted" if accepted else "failed",
            "accepted": accepted,
            "destination": {
                "channel_index": channel_index,
                "channel_name": str(params.get("channel_name") or "").strip() or None,
            },
            "payload": {"text": text},
            "response": broker_result,
        }
        self._remember_outbound(record)
        return {
            "accepted": accepted,
            "message": "Channel message accepted by MeshCore gateway link; on-air delivery is not independently confirmed." if accepted else "Channel message rejected by MeshCore gateway link.",
            "payload": record,
        }

    def set_tx_power(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.current_allow_basestation_tx():
            raise ValueError("Basestation-directed transmit is disabled for this gateway-link server.")
        tx_power_dbm = int(params.get("tx_power_dbm"))
        result = self._broker.set_tx_power(tx_power_dbm)
        return {
            "accepted": bool(result.get("ok")),
            "message": f"TX power set to {tx_power_dbm} dBm.",
            "tx_power_dbm": tx_power_dbm,
        }

    def _remember_outbound(self, record: dict[str, Any]) -> None:
        with self._outbound_lock:
            self._outbound_requests.append(dict(record))
            if len(self._outbound_requests) > 200:
                del self._outbound_requests[:-200]

    def _unreachable_snapshot(self, message: str) -> dict[str, Any]:
        service = read_service_properties(self._config.service_name)
        allow_basestation_tx = self.current_allow_basestation_tx()
        return {
            "connected": False,
            "status": "unreachable",
            "gateway_id": "meshcore-gateway-1",
            "display_name": "MeshCore Gateway",
            "contract_version": "1.0",
            "identity": {},
            "runtime_status": {
                "transport": "meshcore-gateway-link",
                "source_kind": "native-session-broker",
                "interface_mode": "gateway-link",
                "gateway_tx_allowed": allow_basestation_tx,
                "runtime_endpoint": f"tcp://{self._config.native_host}:{self._config.native_port}",
                "link_carrier": "tcp",
                "link_endpoint": f"{self._config.host}:{self._config.port}",
                "link_version": PROTOCOL_VERSION,
                "service": service,
            },
            "last_error": message,
        }

    def _error_response(self, envelope: GatewayLinkEnvelope, message: str) -> GatewayLinkEnvelope:
        return GatewayLinkEnvelope(
            version=PROTOCOL_VERSION,
            type="response",
            id=envelope.id,
            ok=False,
            error={"message": message},
        )


class GatewayLinkServer:
    def __init__(self, config: GatewayLinkConfig, broker: NativeSessionBroker | None = None) -> None:
        self._config = config
        self._owns_broker = broker is None
        self._broker = broker or build_native_session_broker(config)
        self._service = GatewayLinkService(config, self._broker)
        self._server: socket.socket | None = None
        self._stop_event = threading.Event()
        self._accept_thread: threading.Thread | None = None

    def serve_forever(self) -> None:
        started = self.start(raise_on_bind_error=True)
        if not started:
            return
        try:
            assert self._accept_thread is not None
            self._accept_thread.join()
        finally:
            self.stop()

    def start(self, *, raise_on_bind_error: bool) -> bool:
        if self._accept_thread is not None:
            return True
        if self._owns_broker:
            self._broker.start()
        try:
            self._server = socket.create_server((self._config.host, self._config.port), reuse_port=False)
        except OSError as exc:
            if self._owns_broker:
                self._broker.stop()
            if raise_on_bind_error:
                raise
            print(
                f"MeshCore Pi gateway link sidecar disabled: could not bind tcp://{self._config.host}:{self._config.port} ({exc})"
            )
            return False
        self._stop_event.clear()
        self._accept_thread = threading.Thread(target=self._accept_loop, name="meshcore-gateway-link", daemon=True)
        self._accept_thread.start()
        print(f"MeshCore Pi gateway link listening on tcp://{self._config.host}:{self._config.port}")
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._server is not None:
            try:
                self._server.close()
            finally:
                self._server = None
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=1.0)
            self._accept_thread = None
        if self._owns_broker:
            self._broker.stop()

    def get_access_state(self) -> dict[str, Any]:
        return self._service.get_access_state()

    def set_allow_basestation_tx(self, allow_basestation_tx: bool) -> dict[str, Any]:
        return self._service.set_allow_basestation_tx(allow_basestation_tx)

    def _accept_loop(self) -> None:
        assert self._server is not None
        while not self._stop_event.is_set():
            try:
                connection, _ = self._server.accept()
            except OSError:
                if self._stop_event.is_set():
                    return
                raise
            thread = threading.Thread(target=self._handle_client, args=(connection,), daemon=True)
            thread.start()

    def _handle_client(self, connection: socket.socket) -> None:
        with connection:
            try:
                request_envelope = _recv_envelope(connection)
                response = self._service.dispatch(request_envelope)
                connection.sendall(encode_gateway_link_frame(response))
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                return
            except OSError as exc:
                if exc.errno in {errno.EPIPE, errno.ECONNRESET, errno.ECONNABORTED}:
                    return
                raise


def _recv_envelope(connection: socket.socket) -> GatewayLinkEnvelope:
    header = _recv_exact(connection, 4)
    payload_length = int.from_bytes(header, byteorder="big", signed=False)
    payload = _recv_exact(connection, payload_length)
    return decode_gateway_link_frame(header + payload)


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = int(size)
    while remaining > 0:
        chunk = connection.recv(remaining)
        if not chunk:
            raise RuntimeError("Gateway link connection closed before frame completed.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def main() -> int:
    args = parse_args()
    config = GatewayLinkConfig.from_args(args)
    server = GatewayLinkServer(config)
    print(f"Native companion target: tcp://{config.native_host}:{config.native_port}")
    print(f"App name: {config.app_name}")
    print(f"Basestation TX allowed: {config.allow_basestation_tx}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())