from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import secrets
import threading
import time
from typing import Any

from .companion_client import (
    PACKET_ACK,
    PACKET_ADVERTISEMENT,
    PACKET_LOG_DATA,
    PACKET_MESSAGES_WAITING,
    CompanionDeviceError,
    CompanionProtocolError,
    MeshCoreNativeTcpClient,
    parse_log_frame,
)
from .node_page_model import build_node_page_model


HISTORY_LIMIT = 200
EVENT_HISTORY_LIMIT = 200
TOOL_LOG_LIMIT = 200
AUTO_TIME_SYNC_THRESHOLD_SECONDS = 24 * 60 * 60


def _is_active_channel(channel: dict[str, Any]) -> bool:
    name = str(channel.get("name") or "").strip()
    secret_hex = str(channel.get("secret_hex") or "")
    return bool(name) or any(char != "0" for char in secret_hex)


def _channel_message_entry(*, direction: str, channel_index: int, text: str, timestamp: int | None, snr: float | None) -> dict[str, Any]:
    return {
        "direction": direction,
        "channel_index": channel_index,
        "text": text,
        "timestamp": int(timestamp or 0),
        "snr": snr,
    }


def _append_channel_history(channel_history: dict[int, list[dict[str, Any]]], message: dict[str, Any]) -> None:
    channel_index = int(message["channel_index"])
    history = channel_history.setdefault(channel_index, [])
    history.append(message)
    if len(history) > HISTORY_LIMIT:
        del history[:-HISTORY_LIMIT]


def _contact_message_entry(
    *,
    direction: str,
    public_key_ref: str,
    text: str,
    timestamp: int | None,
    snr: float | None,
    route_type: str,
) -> dict[str, Any]:
    return {
        "direction": direction,
        "public_key_ref": public_key_ref,
        "text": text,
        "timestamp": int(timestamp or 0),
        "snr": snr,
        "route_type": route_type,
    }


def _append_contact_history(contact_history: dict[str, list[dict[str, Any]]], message: dict[str, Any]) -> None:
    public_key_ref = str(message["public_key_ref"])
    history = contact_history.setdefault(public_key_ref, [])
    history.append(message)
    if len(history) > HISTORY_LIMIT:
        del history[:-HISTORY_LIMIT]


def _message_route_type(*, path_len: int | None = None, was_flood: bool | None = None) -> str:
    if was_flood is not None:
        return "flood" if was_flood else "direct"
    if path_len is None:
        return "unknown"
    if path_len == 0xFF:
        return "direct"
    return "flood"


def _augment_model_with_activity(
    model: dict[str, Any],
    *,
    contact_history: dict[str, list[dict[str, Any]]],
    channel_history: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    contacts = model.get("contacts", [])
    if isinstance(contacts, list):
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            history = contact_history.get(str(contact.get("public_key") or ""), [])
            if history:
                latest = history[-1]
                contact["last_message_timestamp"] = int(latest.get("timestamp") or 0)
                contact["last_message_route"] = str(latest.get("route_type") or "unknown")
                contact["last_message_direction"] = str(latest.get("direction") or "incoming")
            else:
                contact["last_message_timestamp"] = 0
                contact["last_message_route"] = ""
                contact["last_message_direction"] = ""
    channels = model.get("channels", [])
    if isinstance(channels, list):
        for channel in channels:
            if not isinstance(channel, dict):
                continue
            history = channel_history.get(int(channel.get("index") or 0), [])
            if history:
                latest = history[-1]
                channel["last_message_timestamp"] = int(latest.get("timestamp") or 0)
            else:
                channel["last_message_timestamp"] = 0
    return model


def _should_auto_sync_time(device_time: int | None, *, now: int | None = None) -> bool:
    if not device_time:
        return True
    current_time = int(time.time() if now is None else now)
    return abs(current_time - int(device_time)) > AUTO_TIME_SYNC_THRESHOLD_SECONDS


def _timestamp_to_iso_utc(timestamp: int | float | None) -> str:
    if timestamp:
        return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


class NativeSessionBroker:
    def __init__(
        self,
        native_config: dict[str, Any],
        channel_history: dict[int, list[dict[str, Any]]],
        contact_history: dict[str, list[dict[str, Any]]],
    ) -> None:
        self._native_config = dict(native_config)
        self._channel_history = channel_history
        self._contact_history = contact_history
        self._lock = threading.RLock()
        self._events_condition = threading.Condition()
        self._events: list[dict[str, Any]] = []
        self._next_event_id = 0
        self._tool_logs: list[dict[str, Any]] = []
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._run, name="meshcore-web-session", daemon=True)
        self._client: MeshCoreNativeTcpClient | None = None
        self._contact_keys_by_prefix: dict[str, str] = {}

    def start(self) -> None:
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            self._close_client_locked()
        self._worker.join(timeout=1.0)

    def wait_for_events(self, last_event_id: int, *, timeout_seconds: float = 15.0) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout_seconds
        with self._events_condition:
            while self._next_event_id <= last_event_id and not self._stop_event.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return []
                self._events_condition.wait(timeout=remaining)
            return [event for event in self._events if int(event["id"]) > last_event_id]

    def collect_node_page(self) -> dict[str, Any]:
        model = self._execute(self._collect_node_page_locked)
        return {"ok": True, "node_page": model}

    def collect_session_snapshot(self) -> dict[str, Any]:
        return self._execute(self._collect_snapshot_locked)

    def list_activity(self, *, limit: int = 50, direction: str | None = None) -> list[dict[str, Any]]:
        def operation(client: MeshCoreNativeTcpClient) -> list[dict[str, Any]]:
            self._drain_messages_locked(client)
            rows = self._collect_activity_locked()
            if direction:
                normalized = str(direction).strip().lower()
                rows = [row for row in rows if str(row.get("direction") or "").lower() == normalized]
            return rows[: max(1, int(limit))]

        return self._execute(operation)

    def apply_settings(self, body: dict[str, Any]) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            client.set_advert_name(str(body.get("name") or ""))
            client.set_device_time(int(body["timestamp"]))
            client.set_advert_location(float(body["lat"]), float(body["lon"]))
            client.set_radio_params(
                freq_mhz=float(body["freq_mhz"]),
                bw_khz=float(body["bw_khz"]),
                sf=int(body["sf"]),
                cr=int(body["cr"]),
                repeat=bool(body["repeat"]),
            )
            client.set_radio_tx_power(int(body["tx_power_dbm"]))
            return {"ok": True, "reboot_recommended": True}

        return self._execute(operation)

    def set_name(self, name: str) -> dict[str, Any]:
        return self._execute(lambda client: {"ok": True} if client.set_advert_name(name) else {"ok": False})

    def set_time(self, timestamp: int) -> dict[str, Any]:
        return self._execute(lambda client: {"ok": True} if client.set_device_time(timestamp) else {"ok": False})

    def set_location(self, lat: float, lon: float) -> dict[str, Any]:
        return self._execute(lambda client: {"ok": True} if client.set_advert_location(lat, lon) else {"ok": False})

    def set_radio(self, body: dict[str, Any]) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            client.set_radio_params(
                freq_mhz=float(body["freq_mhz"]),
                bw_khz=float(body["bw_khz"]),
                sf=int(body["sf"]),
                cr=int(body["cr"]),
                repeat=bool(body["repeat"]),
            )
            client.set_radio_tx_power(int(body["tx_power_dbm"]))
            return {"ok": True}

        return self._execute(operation)

    def set_tx_power(self, tx_power_dbm: int) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            client.set_radio_tx_power(int(tx_power_dbm))
            return {"ok": True, "tx_power_dbm": int(tx_power_dbm)}

        return self._execute(operation)

    def export_contact_code(self) -> dict[str, Any]:
        return self._execute(lambda client: {"ok": True, "contact_code": client.export_self_contact_code()})

    def tools_summary(self) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            return {
                "ok": True,
                "core": asdict(client.get_core_stats()),
                "radio": asdict(client.get_radio_stats()),
                "packets": asdict(client.get_packet_stats()),
                "logs": list(self._tool_logs),
            }

        return self._execute(operation)

    def discover_contacts(self, body: dict[str, Any]) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            flood = bool(body.get("flood", True))
            sent_at = int(time.time())
            client.send_self_advert(flood=flood)
            self._publish_locked("advert-sent", {"flood": flood, "sent_at": sent_at})
            return {"ok": True, "flood": flood, "sent_at": sent_at}

        return self._execute(operation)

    def add_contact(self, body: dict[str, Any]) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            contact_code = str(body.get("contact_code") or "").strip()
            if contact_code:
                client.import_contact_code(contact_code)
                return {"ok": True, "mode": "import"}
            client.add_or_update_contact(
                public_key_hex=str(body["public_key_hex"]),
                name=str(body["name"]),
            )
            return {"ok": True, "mode": "manual"}

        return self._execute(operation)

    def get_contact_messages(self, public_key: str) -> dict[str, Any]:
        normalized_public_key = str(public_key).strip().lower()

        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            self._drain_messages_locked(client)
            model = self._collect_node_page_locked(client)
            contacts = [contact for contact in model.get("contacts", []) if isinstance(contact, dict)]
            if not any(str(contact.get("public_key") or "").lower() == normalized_public_key for contact in contacts):
                raise ValueError("contact is not configured")
            return {"ok": True, "messages": self._contact_history.get(normalized_public_key, [])}

        return self._execute(operation)

    def send_contact_message(self, public_key: str, body: dict[str, Any]) -> dict[str, Any]:
        normalized_public_key = str(public_key).strip().lower()
        text = str(body.get("text") or "").strip()
        if not text:
            raise ValueError("message text must not be empty")

        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            model = self._collect_node_page_locked(client)
            contacts = [contact for contact in model.get("contacts", []) if isinstance(contact, dict)]
            if not any(str(contact.get("public_key") or "").lower() == normalized_public_key for contact in contacts):
                raise ValueError("contact is not configured")
            send_result = client.send_direct_text_message(public_key_prefix_hex=normalized_public_key[:12], text=text)
            sent_at = int(time.time())
            entry = _contact_message_entry(
                direction="outgoing",
                public_key_ref=normalized_public_key,
                text=text,
                timestamp=sent_at,
                snr=None,
                route_type=_message_route_type(was_flood=send_result.was_flood),
            )
            _append_contact_history(self._contact_history, entry)
            self._publish_locked("contact-message", entry)
            self._drain_messages_locked(client)
            return {
                "ok": True,
                "messages": self._contact_history.get(normalized_public_key, []),
                "send_result": asdict(send_result),
            }

        return self._execute(operation)

    def clear_contact_messages(self, public_key: str) -> dict[str, Any]:
        normalized_public_key = str(public_key).strip().lower()

        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            model = self._collect_node_page_locked(client)
            contacts = [contact for contact in model.get("contacts", []) if isinstance(contact, dict)]
            if not any(str(contact.get("public_key") or "").lower() == normalized_public_key for contact in contacts):
                raise ValueError("contact is not configured")
            self._contact_history.pop(normalized_public_key, None)
            return {"ok": True, "public_key": normalized_public_key}

        return self._execute(operation)

    def add_channel(self, body: dict[str, Any]) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            invite = str(body.get("invite") or "").strip()
            if invite:
                name, secret_hex = _parse_channel_invite(invite)
            else:
                name = str(body["name"]).strip()
                secret_hex = str(body.get("secret_hex") or secrets.token_hex(16)).strip()
            model = self._collect_node_page_locked(client)
            active_indices = {
                int(channel.get("index", -1))
                for channel in model.get("channels", [])
                if isinstance(channel, dict) and _is_active_channel(channel)
            }
            max_channels = int(model.get("capabilities", {}).get("max_channels") or len(model.get("channels", [])))
            free_index = next((index for index in range(max_channels) if index not in active_indices), None)
            if free_index is None:
                raise ValueError("no free channel slots are available")
            client.set_channel(index=free_index, name=name, secret_hex=secret_hex)
            return {
                "ok": True,
                "channel": {
                    "index": free_index,
                    "name": name,
                    "secret_hex": secret_hex,
                    "invite_url": f"meshcore://channel/add?name={name.replace(' ', '+')}&secret={secret_hex}",
                },
            }

        return self._execute(operation)

    def update_channel(self, channel_index: int, body: dict[str, Any]) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            name = str(body["name"]).strip()
            secret_hex = str(body["secret_hex"]).strip()
            if not name:
                raise ValueError("channel name must not be empty")
            client.set_channel(index=channel_index, name=name, secret_hex=secret_hex)
            return {
                "ok": True,
                "channel": {
                    "index": channel_index,
                    "name": name,
                    "secret_hex": secret_hex,
                    "invite_url": f"meshcore://channel/add?name={name.replace(' ', '+')}&secret={secret_hex}",
                },
            }

        return self._execute(operation)

    def delete_channel(self, channel_index: int) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            if channel_index == 0:
                raise ValueError("public channel cannot be removed")
            client.remove_channel(channel_index)
            self._channel_history.pop(channel_index, None)
            return {"ok": True, "channel_index": channel_index}

        return self._execute(operation)

    def get_channel_messages(self, channel_index: int) -> dict[str, Any]:
        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            self._drain_messages_locked(client)
            model = self._collect_node_page_locked(client)
            active_channels = [
                channel for channel in model.get("channels", []) if isinstance(channel, dict) and _is_active_channel(channel)
            ]
            if not any(int(channel.get("index", -1)) == channel_index for channel in active_channels):
                raise ValueError(f"channel {channel_index} is not active")
            return {"ok": True, "messages": self._channel_history.get(channel_index, [])}

        return self._execute(operation)

    def send_channel_message(self, channel_index: int, body: dict[str, Any]) -> dict[str, Any]:
        text = str(body.get("text") or "")

        def operation(client: MeshCoreNativeTcpClient) -> dict[str, Any]:
            send_result = client.send_channel_text_message(channel_index=channel_index, text=text)
            sent_at = int(time.time())
            _append_channel_history(
                self._channel_history,
                _channel_message_entry(
                    direction="outgoing",
                    channel_index=channel_index,
                    text=text,
                    timestamp=sent_at,
                    snr=None,
                ),
            )
            self._channel_history[channel_index][-1]["route_type"] = _message_route_type(was_flood=send_result.was_flood)
            self._publish_locked(
                "channel-message",
                {
                    "direction": "outgoing",
                    "channel_index": channel_index,
                    "text": text,
                },
            )
            self._drain_messages_locked(client)
            return {
                "ok": True,
                "messages": self._channel_history.get(channel_index, []),
                "send_result": asdict(send_result),
            }

        return self._execute(operation)

    def reboot(self) -> dict[str, Any]:
        return self._execute(lambda client: {"ok": True} if client.reboot() else {"ok": False})

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self._lock.acquire(timeout=0.1):
                continue
            try:
                client = self._ensure_client_locked()
                payload = client.read_next_frame(timeout_seconds=0.2)
                if payload is None:
                    continue
                self._handle_async_frame_locked(payload)
            except (OSError, CompanionProtocolError) as exc:
                self._publish_locked("session-status", {"status": f"Live companion session reconnecting: {exc}"})
                self._close_client_locked()
            finally:
                self._lock.release()

    def _execute(self, operation):
        with self._lock:
            client = self._ensure_client_locked()
            try:
                result = operation(client)
                self._process_notifications_locked(client)
                return result
            except CompanionDeviceError:
                raise
            except (OSError, CompanionProtocolError):
                self._close_client_locked()
                raise

    def _collect_snapshot_locked(self, client: MeshCoreNativeTcpClient | None = None) -> dict[str, Any]:
        active_client = client if client is not None else self._ensure_client_locked()
        snapshot = active_client.collect_session_snapshot(
            app_name=str(self._native_config["app_name"]),
            protocol_version=int(self._native_config["protocol_version"]),
        )
        self._process_notifications_locked(active_client)
        self._contact_keys_by_prefix = {
            str(contact.get("public_key") or "")[:12]: str(contact.get("public_key") or "")
            for contact in snapshot.get("contacts", [])
            if isinstance(contact, dict) and contact.get("public_key")
        }
        return snapshot

    def _collect_node_page_locked(self, client: MeshCoreNativeTcpClient | None = None) -> dict[str, Any]:
        snapshot = self._collect_snapshot_locked(client)
        model = build_node_page_model(snapshot).to_dict()
        return _augment_model_with_activity(
            model,
            contact_history=self._contact_history,
            channel_history=self._channel_history,
        )

    def _collect_activity_locked(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for public_key, history in self._contact_history.items():
            for message in history:
                if not isinstance(message, dict):
                    continue
                timestamp = int(message.get("timestamp") or 0)
                direction = str(message.get("direction") or "incoming")
                rows.append(
                    {
                        "direction": direction,
                        "transport": "meshcore",
                        "network": "meshcore",
                        "event_type": "contact_message_rx" if direction == "incoming" else "contact_message_tx",
                        "event_ts_utc": _timestamp_to_iso_utc(timestamp),
                        "summary": str(message.get("text") or ""),
                        "payload": {
                            "text": str(message.get("text") or ""),
                            "message_scope": "direct",
                            "event_utc": _timestamp_to_iso_utc(timestamp),
                            "sender": {
                                "public_key": public_key,
                                "short_name": public_key[:12],
                            },
                            "raw": {
                                "channel_index": -1,
                                "message_scope": "direct",
                                "sender_public_key": public_key,
                                "source_endpoint": public_key,
                            },
                        },
                    }
                )
        for channel_index, history in self._channel_history.items():
            for message in history:
                if not isinstance(message, dict):
                    continue
                timestamp = int(message.get("timestamp") or 0)
                direction = str(message.get("direction") or "incoming")
                rows.append(
                    {
                        "direction": direction,
                        "transport": "meshcore",
                        "network": "meshcore",
                        "event_type": "channel_message_rx" if direction == "incoming" else "channel_message_tx",
                        "event_ts_utc": _timestamp_to_iso_utc(timestamp),
                        "summary": str(message.get("text") or ""),
                        "payload": {
                            "text": str(message.get("text") or ""),
                            "channel_index": int(channel_index),
                            "message_scope": "channel",
                            "event_utc": _timestamp_to_iso_utc(timestamp),
                            "raw": {
                                "channel_index": int(channel_index),
                                "message_scope": "channel",
                            },
                        },
                    }
                )
        rows.sort(key=lambda row: str(row.get("event_ts_utc") or ""), reverse=True)
        return rows

    def _ensure_client_locked(self) -> MeshCoreNativeTcpClient:
        if self._client is None:
            client = MeshCoreNativeTcpClient(
                self._native_config["host"],
                self._native_config["port"],
                timeout_seconds=self._native_config["timeout_seconds"],
            )
            client.connect()
            snapshot = client.collect_session_snapshot(
                app_name=str(self._native_config["app_name"]),
                protocol_version=int(self._native_config["protocol_version"]),
            )
            auto_synced_time = False
            if _should_auto_sync_time(int(snapshot.get("device_time") or 0)):
                client.set_device_time(int(time.time()))
                auto_synced_time = True
            self._process_notifications_locked(client)
            self._client = client
            self._publish_locked(
                "session-status",
                {
                    "status": (
                        f"Connected to {self._native_config['host']}:{self._native_config['port']}. "
                        f"Live message notices are active{' Node clock auto-synced from the browser host.' if auto_synced_time else ''}"
                    )
                },
            )
        return self._client

    def _close_client_locked(self) -> None:
        if self._client is None:
            return
        try:
            self._client.close()
        finally:
            self._client = None

    def _process_notifications_locked(self, client: MeshCoreNativeTcpClient) -> None:
        for payload in client.pop_notifications():
            self._handle_async_frame_locked(payload)

    def _handle_async_frame_locked(self, payload: bytes) -> None:
        packet_type = payload[0] if payload else None
        if packet_type == PACKET_MESSAGES_WAITING:
            messages = self._drain_messages_locked(self._ensure_client_locked())
            self._publish_locked(
                "messages-waiting",
                {
                    "count": len(messages),
                    "channel_index": next(
                        (message.get("channel_index") for message in reversed(messages) if message.get("channel_index") is not None),
                        None,
                    ),
                },
            )
            return
        if packet_type == PACKET_LOG_DATA:
            log_entry = asdict(parse_log_frame(payload))
            log_entry["received_at"] = int(time.time())
            self._tool_logs.append(log_entry)
            if len(self._tool_logs) > TOOL_LOG_LIMIT:
                del self._tool_logs[:-TOOL_LOG_LIMIT]
            self._publish_locked("log-frame", log_entry)
            return
        if packet_type == PACKET_ADVERTISEMENT:
            self._publish_locked("advertisement", {"received_at": int(time.time())})
            return
        if packet_type == PACKET_ACK:
            return

    def _drain_messages_locked(self, client: MeshCoreNativeTcpClient) -> list[dict[str, Any]]:
        received: list[dict[str, Any]] = []
        for message in client.drain_messages(limit=100):
            if not message.text:
                continue
            route_type = _message_route_type(path_len=message.path_len)
            if message.channel_index is not None:
                entry = _channel_message_entry(
                    direction="incoming",
                    channel_index=int(message.channel_index),
                    text=message.text,
                    timestamp=message.timestamp,
                    snr=message.snr,
                )
                entry["route_type"] = route_type
                _append_channel_history(self._channel_history, entry)
                self._publish_locked("channel-message", entry)
                received.append(entry)
                continue
            public_key_ref = self._contact_keys_by_prefix.get(str(message.pubkey_prefix or ""), str(message.pubkey_prefix or ""))
            entry = _contact_message_entry(
                direction="incoming",
                public_key_ref=public_key_ref,
                text=message.text,
                timestamp=message.timestamp,
                snr=message.snr,
                route_type=route_type,
            )
            _append_contact_history(self._contact_history, entry)
            self._publish_locked("contact-message", entry)
            received.append(entry)
        return received

    def _publish_locked(self, event_type: str, data: dict[str, Any]) -> None:
        with self._events_condition:
            self._next_event_id += 1
            self._events.append({"id": self._next_event_id, "type": event_type, "data": data})
            if len(self._events) > EVENT_HISTORY_LIMIT:
                del self._events[:-EVENT_HISTORY_LIMIT]
            self._events_condition.notify_all()


def _parse_channel_invite(invite: str) -> tuple[str, str]:
    from urllib.parse import parse_qs, unquote_plus, urlparse

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