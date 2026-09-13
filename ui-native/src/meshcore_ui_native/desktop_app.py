from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import html
import json
from queue import Empty, Queue
import secrets
import threading
import time
from typing import Any

from .companion_client import (
    PACKET_ACK,
    PACKET_ADVERTISEMENT,
    PACKET_CHANNEL_DATA_RECV,
    PACKET_CHANNEL_MSG_RECV,
    PACKET_CHANNEL_MSG_RECV_V3,
    PACKET_CONTACT_MSG_RECV,
    PACKET_CONTACT_MSG_RECV_V3,
    PACKET_LOG_DATA,
    PACKET_MESSAGES_WAITING,
    CompanionDeviceError,
    CompanionProtocolError,
    MessageEnvelope,
    MeshCoreNativeTcpClient,
    parse_log_frame,
    parse_message_envelope,
)
from .node_page_model import NodePageModel, build_node_page_model


def launch_desktop_app(
    *,
    host: str,
    port: int,
    app_name: str,
    protocol_version: int,
    timeout_seconds: float,
) -> int:
    try:
        from PySide6.QtCore import QObject, QThread, Qt, Signal
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QMenu,
            QPushButton,
            QPlainTextEdit,
            QScrollArea,
            QSizePolicy,
            QStackedWidget,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print(
            "PySide6 is required for --ui. Install it with: "
            ".\\.venv\\Scripts\\python.exe -m pip install PySide6>=6.8"
        )
        return 2

    @dataclass(slots=True)
    class SessionConfig:
        host: str
        port: int
        app_name: str
        protocol_version: int
        timeout_seconds: float

    @dataclass(frozen=True, slots=True)
    class RadioPresetDefinition:
        key: str
        label: str
        bw_khz: float
        sf: int
        cr: int

    RADIO_PRESETS = (
        RadioPresetDefinition("default", "MeshCore default", 250.0, 11, 5),
        RadioPresetDefinition("balanced", "Balanced", 250.0, 10, 5),
        RadioPresetDefinition("long_range", "Long range", 125.0, 12, 5),
        RadioPresetDefinition("fast", "Fast", 250.0, 9, 5),
    )

    def _format_timestamp(value: int) -> str:
        if value <= 0:
            return "Unavailable"
        return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    def _format_datetime_input(value: int) -> str:
        if value <= 0:
            return ""
        return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d %H:%M:%S")

    def _parse_datetime_input(value: str) -> int:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError("device time must not be empty")
        try:
            parsed = datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError("device time must use YYYY-MM-DD HH:MM:SS in UTC") from exc
        return int(parsed.replace(tzinfo=UTC).timestamp())

    def _format_contact(item: dict[str, Any]) -> str:
        name = str(item.get("name") or "Unnamed contact")
        public_key = str(item.get("public_key") or "")
        return f"{name} ({public_key[:12]})"

    def _format_channel(item: dict[str, Any]) -> str:
        index = int(item.get("index") or 0)
        name = str(item.get("name") or "") or "unused"
        return f"{index}: {name}"

    def _format_custom_vars(values: dict[str, str]) -> str:
        if not values:
            return "No custom vars reported."
        return "\n".join(f"{key}: {value}" for key, value in sorted(values.items()))

    def _format_custom_var_summary(values: dict[str, str]) -> str:
        if not values:
            return "None"
        keys = sorted(values.keys())
        if len(keys) <= 3:
            return ", ".join(keys)
        return ", ".join(keys[:3]) + f" (+{len(keys) - 3} more)"

    def _format_location(lat: float | None, lon: float | None) -> str:
        if lat is None or lon is None:
            return "Unavailable"
        if lat == 0.0 and lon == 0.0:
            return "Unavailable"
        return f"{lat:.6f}, {lon:.6f}"

    def _format_radio_tuple(freq_mhz: float, bw_khz: float, sf: int, cr: int) -> str:
        return f"{freq_mhz:.3f} MHz, {bw_khz:.1f} kHz, SF{sf}, CR{cr}"

    def _radio_preset_for_values(bw_khz: float, sf: int, cr: int) -> RadioPresetDefinition | None:
        for preset in RADIO_PRESETS:
            if abs(preset.bw_khz - bw_khz) < 0.05 and preset.sf == sf and preset.cr == cr:
                return preset
        return None

    def _format_contact_location_list(contacts: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for contact in contacts:
            lat = contact.get("gps_lat")
            lon = contact.get("gps_lon")
            if lat in (None, 0, 0.0) and lon in (None, 0, 0.0):
                continue
            lines.append(
                f"{contact.get('name') or 'Unnamed contact'}: {float(lat):.6f}, {float(lon):.6f}"
            )
        return "\n".join(lines) if lines else "No contact coordinates reported."

    def _format_message_timestamp(value: int | None) -> str:
        if value is None or value <= 0:
            return "unknown time"
        return datetime.fromtimestamp(value, UTC).strftime("%H:%M:%S")

    def _format_uptime(total_seconds: int) -> str:
        minutes, seconds = divmod(max(0, int(total_seconds)), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        if days:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        if hours:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def _format_route(path_len: int | None) -> str:
        if path_len == 0xFF:
            return "flood"
        if path_len is None:
            return "route unknown"
        return f"path {path_len}"

    def _format_channel_message_line(message: dict[str, Any]) -> str:
        timestamp = _format_message_timestamp(message.get("timestamp"))
        route = _format_route(message.get("path_len"))
        snr = message.get("snr")
        snr_text = "" if snr is None else f" | SNR {snr}"
        direction = str(message.get("direction") or "message")
        return f"[{timestamp}] {direction} | {route}{snr_text}\n{message.get('text') or '(no text)'}"

    def _format_contact_message_line(message: dict[str, Any]) -> str:
        timestamp = _format_message_timestamp(message.get("timestamp"))
        route = _format_route(message.get("path_len"))
        snr = message.get("snr")
        snr_text = "" if snr is None else f" | SNR {snr}"
        direction = str(message.get("direction") or "message")
        return f"[{timestamp}] {direction} | {route}{snr_text}\n{message.get('text') or '(no text)'}"

    def _message_preview(message: dict[str, Any] | None) -> str:
        if not message:
            return "No messages yet"
        text = " ".join(str(message.get("text") or "").split())
        if not text:
            text = "(no text)"
        if len(text) > 36:
            text = text[:33] + "..."
        direction = str(message.get("direction") or "message")
        timestamp = _format_message_timestamp(message.get("timestamp"))
        return f"{direction} {timestamp}: {text}"

    def _message_preview_text(history: list[dict[str, Any]]) -> str:
        if not history:
            return "No messages yet"
        return _message_preview(history[-1])

    def _format_tool_stats_text(stats_sections: dict[str, dict[str, Any]]) -> str:
        sections: list[str] = []
        core = stats_sections.get("core")
        if core is not None:
            sections.append(
                "Core\n"
                f"Battery: {core.get('battery_mv', 0)} mV\n"
                f"Uptime: {_format_uptime(int(core.get('uptime_secs') or 0))}\n"
                f"Error flags: 0x{int(core.get('error_flags') or 0):04x}\n"
                f"Outbound queue: {int(core.get('queue_len') or 0)}"
            )
        radio = stats_sections.get("radio")
        if radio is not None:
            sections.append(
                "Radio\n"
                f"Noise floor: {int(radio.get('noise_floor') or 0)} dBm\n"
                f"Last RSSI: {int(radio.get('last_rssi') or 0)} dBm\n"
                f"Last SNR: {float(radio.get('last_snr') or 0.0):.2f} dB\n"
                f"TX airtime: {int(radio.get('tx_air_secs') or 0)} s\n"
                f"RX airtime: {int(radio.get('rx_air_secs') or 0)} s"
            )
        packets = stats_sections.get("packets")
        if packets is not None:
            sections.append(
                "Packets\n"
                f"Received: {int(packets.get('packets_recv') or 0)}\n"
                f"Sent: {int(packets.get('packets_sent') or 0)}\n"
                f"Sent flood/direct: {int(packets.get('sent_flood') or 0)} / {int(packets.get('sent_direct') or 0)}\n"
                f"Received flood/direct: {int(packets.get('recv_flood') or 0)} / {int(packets.get('recv_direct') or 0)}\n"
                f"Receive errors: {int(packets.get('recv_errors') or 0)}"
            )
        return "\n\n".join(sections) if sections else "No tool stats loaded yet."

    def _format_log_entry(log_frame: dict[str, Any]) -> str:
        timestamp = datetime.now(UTC).strftime("%H:%M:%S")
        snr = float(log_frame.get("snr") or 0.0)
        rssi = int(log_frame.get("rssi") or 0)
        payload_hex = str(log_frame.get("payload_hex") or "")
        return f"[{timestamp}] SNR {snr:.2f} dB | RSSI {rssi} dBm | {payload_hex}"

    def _is_active_channel(channel: dict[str, Any]) -> bool:
        name = str(channel.get("name") or "").strip()
        secret_hex = str(channel.get("secret_hex") or "")
        has_secret = bool(secret_hex) and any(char != "0" for char in secret_hex)
        has_name = bool(name) and name.lower() != "unused"
        return has_secret or has_name

    def _render_message_html(history: list[dict[str, Any]], empty_text: str) -> str:
        if not history:
            return (
                "<html><body style='font-family:Segoe UI;font-size:10pt;color:#58636f;'>"
                f"<p>{html.escape(empty_text)}</p>"
                "</body></html>"
            )
        blocks: list[str] = []
        for message in history:
            direction = str(message.get("direction") or "message")
            incoming = direction == "received"
            align = "left" if incoming else "right"
            bg = "#e6f4ea" if incoming else "#dceeff"
            border = "#b7d8bf" if incoming else "#b8cee8"
            label = "Incoming" if incoming else "Sent"
            timestamp = _format_message_timestamp(message.get("timestamp"))
            route = _format_route(message.get("path_len"))
            snr = message.get("snr")
            snr_text = "" if snr is None else f" | SNR {snr}"
            text = html.escape(str(message.get("text") or "(no text)"))
            text = text.replace("\n", "<br>")
            blocks.append(
                "<div style='text-align:{align}; margin:10px 0;'>"
                "<div style='display:inline-block; max-width:80%; text-align:left; "
                "background:{bg}; border:1px solid {border}; border-radius:10px; "
                "padding:8px 10px;'>"
                "<div style='font-size:8.5pt; color:#51606d; margin-bottom:4px;'>"
                "{label} {timestamp} | {route}{snr}</div>"
                "<div style='font-size:10pt; color:#16202a; white-space:pre-wrap;'>{text}</div>"
                "</div></div>".format(
                    align=align,
                    bg=bg,
                    border=border,
                    label=label,
                    timestamp=timestamp,
                    route=route,
                    snr=snr_text,
                    text=text,
                )
            )
        return (
            "<html><body style='font-family:Segoe UI;font-size:10pt;background:#f5f7fa;'>"
            + "".join(blocks)
            + "</body></html>"
        )

    def _channel_message_entry(message: MessageEnvelope, *, direction: str) -> dict[str, Any]:
        return {
            "timestamp": message.timestamp,
            "text": message.text,
            "path_len": message.path_len,
            "snr": message.snr,
            "txt_type": message.txt_type,
            "packet_type": message.packet_type,
            "direction": direction,
        }

    def _contact_message_entry(message: MessageEnvelope, *, direction: str) -> dict[str, Any]:
        return {
            "timestamp": message.timestamp,
            "text": message.text,
            "path_len": message.path_len,
            "snr": message.snr,
            "txt_type": message.txt_type,
            "packet_type": message.packet_type,
            "direction": direction,
        }

    class PersistentSessionWorker(QObject):
        snapshot_loaded = Signal(object)
        messages_received = Signal(object)
        log_received = Signal(object)
        status_changed = Signal(str)
        command_finished = Signal(str, object, object)

        def __init__(self, config: SessionConfig) -> None:
            super().__init__()
            self._config = config
            self._stop_event = threading.Event()
            self._commands: Queue[tuple[str, dict[str, Any]]] = Queue()

        def enqueue(self, action: str, payload: dict[str, Any]) -> None:
            self._commands.put((action, payload))

        def stop(self) -> None:
            self._stop_event.set()

        def run(self) -> None:
            client: MeshCoreNativeTcpClient | None = None
            try:
                while not self._stop_event.is_set():
                    try:
                        if client is None:
                            self.status_changed.emit(
                                f"Connecting to {self._config.host}:{self._config.port} as {self._config.app_name}..."
                            )
                            client = MeshCoreNativeTcpClient(
                                self._config.host,
                                self._config.port,
                                timeout_seconds=self._config.timeout_seconds,
                            )
                            client.connect()
                            snapshot = client.collect_session_snapshot(
                                app_name=self._config.app_name,
                                protocol_version=self._config.protocol_version,
                            )
                            self.snapshot_loaded.emit(build_node_page_model(snapshot))
                            self.status_changed.emit(
                                f"Connected to {self._config.host}:{self._config.port}. "
                                "Live native message notices are active."
                            )
                            self._drain_client_notifications(client)

                        self._process_pending_command(client)
                        self._drain_client_notifications(client)
                        payload = client.read_next_frame(timeout_seconds=0.25)
                        if payload is not None:
                            self._handle_incoming_payload(client, payload)
                    except (CompanionDeviceError, CompanionProtocolError, OSError) as exc:
                        self.status_changed.emit(f"Session lost: {exc}")
                        if client is not None:
                            client.close()
                            client = None
                        if self._stop_event.wait(1.0):
                            break
            finally:
                if client is not None:
                    client.close()

        def _process_pending_command(self, client: MeshCoreNativeTcpClient) -> None:
            try:
                action, payload = self._commands.get_nowait()
            except Empty:
                return
            try:
                if action == "refresh_snapshot":
                    snapshot = client.collect_session_snapshot(
                        app_name=self._config.app_name,
                        protocol_version=self._config.protocol_version,
                    )
                    self.snapshot_loaded.emit(build_node_page_model(snapshot))
                    self.command_finished.emit(action, {"ok": True}, None)
                    return
                if action == "send_channel_message":
                    result = client.send_channel_text_message(
                        channel_index=int(payload["channel_index"]),
                        text=str(payload["text"]),
                        timestamp=int(payload.get("timestamp") or time.time()),
                    )
                    self.command_finished.emit(
                        action,
                        {
                            "channel_index": int(payload["channel_index"]),
                            "text": str(payload["text"]),
                            "timestamp": int(payload.get("timestamp") or time.time()),
                            "result": asdict(result),
                        },
                        None,
                    )
                    return
                if action == "send_direct_message":
                    result = client.send_direct_text_message(
                        public_key_prefix_hex=str(payload["public_key_prefix_hex"]),
                        text=str(payload["text"]),
                        timestamp=int(payload.get("timestamp") or time.time()),
                    )
                    self.command_finished.emit(
                        action,
                        {
                            "public_key_prefix_hex": str(payload["public_key_prefix_hex"]),
                            "text": str(payload["text"]),
                            "timestamp": int(payload.get("timestamp") or time.time()),
                            "result": asdict(result),
                        },
                        None,
                    )
                    return
                if action == "add_contact_manual":
                    client.add_or_update_contact(
                        public_key_hex=str(payload["public_key_hex"]),
                        name=str(payload["name"]),
                    )
                    self.command_finished.emit(
                        action,
                        {
                            "name": str(payload["name"]),
                            "public_key_hex": str(payload["public_key_hex"]),
                        },
                        None,
                    )
                    return
                if action == "remove_contact":
                    client.remove_contact(str(payload["public_key_hex"]))
                    self.command_finished.emit(
                        action,
                        {
                            "name": str(payload.get("name") or ""),
                            "public_key_hex": str(payload["public_key_hex"]),
                        },
                        None,
                    )
                    return
                if action == "import_contact_code":
                    client.import_contact_code(str(payload["contact_code_hex"]))
                    self.command_finished.emit(action, {"ok": True}, None)
                    return
                if action == "export_self_contact_code":
                    contact_code = client.export_self_contact_code()
                    self.command_finished.emit(action, {"contact_code_hex": contact_code}, None)
                    return
                if action == "add_channel":
                    client.set_channel(
                        index=int(payload["channel_index"]),
                        name=str(payload["name"]),
                        secret_hex=str(payload["secret_hex"]),
                    )
                    self.command_finished.emit(
                        action,
                        {
                            "channel_index": int(payload["channel_index"]),
                            "name": str(payload["name"]),
                        },
                        None,
                    )
                    return
                if action == "remove_channel":
                    client.remove_channel(int(payload["channel_index"]))
                    self.command_finished.emit(
                        action,
                        {
                            "channel_index": int(payload["channel_index"]),
                            "name": str(payload.get("name") or ""),
                        },
                        None,
                    )
                    return
                if action == "discover_contacts":
                    client.send_self_advert(flood=bool(payload.get("flood", True)))
                    self.command_finished.emit(action, {"ok": True}, None)
                    return
                if action == "get_core_stats":
                    self.command_finished.emit(action, asdict(client.get_core_stats()), None)
                    return
                if action == "get_radio_stats":
                    self.command_finished.emit(action, asdict(client.get_radio_stats()), None)
                    return
                if action == "get_packet_stats":
                    self.command_finished.emit(action, asdict(client.get_packet_stats()), None)
                    return
                if action == "set_advert_name":
                    client.set_advert_name(str(payload["name"]))
                    self.command_finished.emit(action, {"name": str(payload["name"])}, None)
                    return
                if action == "set_device_time":
                    client.set_device_time(int(payload["timestamp"]))
                    self.command_finished.emit(action, {"timestamp": int(payload["timestamp"])}, None)
                    return
                if action == "set_advert_location":
                    client.set_advert_location(float(payload["lat"]), float(payload["lon"]))
                    self.command_finished.emit(
                        action,
                        {"lat": float(payload["lat"]), "lon": float(payload["lon"])},
                        None,
                    )
                    return
                if action == "set_radio_settings":
                    client.set_radio_params(
                        freq_mhz=float(payload["freq_mhz"]),
                        bw_khz=float(payload["bw_khz"]),
                        sf=int(payload["sf"]),
                        cr=int(payload["cr"]),
                        repeat=bool(payload["repeat"]),
                    )
                    client.set_radio_tx_power(int(payload["tx_power_dbm"]))
                    self.command_finished.emit(action, dict(payload), None)
                    return
                if action == "reboot":
                    client.reboot()
                    self.command_finished.emit(action, {"ok": True}, None)
                    return
                if action == "drain_messages":
                    drained = client.drain_messages(limit=int(payload.get("limit") or 50))
                    if drained:
                        self.messages_received.emit(drained)
                    self.command_finished.emit(action, {"count": len(drained)}, None)
                    return
                raise ValueError(f"unsupported session action: {action}")
            except (CompanionDeviceError, CompanionProtocolError, OSError, ValueError) as exc:
                self.command_finished.emit(action, None, str(exc))

        def _drain_client_notifications(self, client: MeshCoreNativeTcpClient) -> None:
            for payload in client.pop_notifications():
                self._handle_incoming_payload(client, payload)

        def _handle_incoming_payload(self, client: MeshCoreNativeTcpClient, payload: bytes) -> None:
            packet_type = payload[0] if payload else None
            if packet_type == PACKET_MESSAGES_WAITING:
                drained = client.drain_messages(limit=50)
                if drained:
                    self.messages_received.emit(drained)
                    self.status_changed.emit(f"Auto-received {len(drained)} queued native messages.")
                return
            if packet_type in {
                PACKET_CONTACT_MSG_RECV,
                PACKET_CONTACT_MSG_RECV_V3,
                PACKET_CHANNEL_MSG_RECV,
                PACKET_CHANNEL_MSG_RECV_V3,
                PACKET_CHANNEL_DATA_RECV,
            }:
                message = parse_message_envelope(payload)
                if message is not None:
                    self.messages_received.emit([message])
                return
            if packet_type == PACKET_ACK:
                self.status_changed.emit("Native send acknowledgment received.")
                return
            if packet_type == PACKET_ADVERTISEMENT:
                self.status_changed.emit("Native advert notification received.")
                return
            if packet_type == PACKET_LOG_DATA:
                self.log_received.emit(asdict(parse_log_frame(payload)))
                self.status_changed.emit("Native log data received.")
                return

    class NodeWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self._config = SessionConfig(
                host=host,
                port=port,
                app_name=app_name,
                protocol_version=protocol_version,
                timeout_seconds=timeout_seconds,
            )
            self._session_thread: QThread | None = None
            self._session_worker: PersistentSessionWorker | None = None
            self._current_model: NodePageModel | None = None
            self._contacts_data: list[dict[str, Any]] = []
            self._channels_data: list[dict[str, Any]] = []
            self._active_channels_data: list[dict[str, Any]] = []
            self._channel_messages: dict[int, list[dict[str, Any]]] = {}
            self._contact_messages: dict[str, list[dict[str, Any]]] = {}
            self._channel_unread_counts: dict[int, int] = {}
            self._contact_unread_counts: dict[str, int] = {}
            self._tool_stats_sections: dict[str, dict[str, Any]] = {}
            self._tool_log_entries: list[str] = []
            self._tools_dialog: QDialog | None = None
            self._tools_stats_view: QPlainTextEdit | None = None
            self._tools_log_view: QPlainTextEdit | None = None
            self.setWindowTitle("MeshCore Native UI")
            self.resize(1180, 860)
            self._build_ui()
            self.refresh()

        def _build_ui(self) -> None:
            root = QWidget()
            outer_layout = QVBoxLayout(root)
            outer_layout.setContentsMargins(16, 16, 16, 16)
            outer_layout.setSpacing(12)

            connection_box = QGroupBox("Connection")
            connection_layout = QHBoxLayout(connection_box)

            self.host_edit = QLineEdit(self._config.host)
            self.host_edit.setPlaceholderText("Native companion host")
            self.port_edit = QLineEdit(str(self._config.port))
            self.port_edit.setPlaceholderText("Port")
            self.app_name_edit = QLineEdit(self._config.app_name)
            self.app_name_edit.setPlaceholderText("APP_START name")
            self.status_label = QLabel("Connecting...")
            self.status_label.setWordWrap(True)
            self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.refresh_button = QPushButton("Reconnect")
            self.refresh_button.clicked.connect(self.refresh)
            self.menu_button = QPushButton("Menu")
            self.menu_button.setVisible(False)
            self.menu_button.setMenu(self._build_tab_menu())

            connection_layout.addWidget(QLabel("Host"))
            connection_layout.addWidget(self.host_edit, 2)
            connection_layout.addWidget(QLabel("Port"))
            connection_layout.addWidget(self.port_edit)
            connection_layout.addWidget(QLabel("App"))
            connection_layout.addWidget(self.app_name_edit, 2)
            connection_layout.addWidget(self.refresh_button)
            connection_layout.addWidget(self.menu_button)

            self.tabs = QTabWidget()
            self._settings_tab_index = self.tabs.addTab(self._build_settings_tab(), "Settings")
            self._contacts_tab_index = self.tabs.addTab(self._build_contacts_tab(), "Contacts")
            self._channels_tab_index = self.tabs.addTab(self._build_channels_tab(), "Channels")
            self._map_tab_index = self.tabs.addTab(self._build_map_tab(), "Map")
            self.tabs.currentChanged.connect(self._handle_tab_changed)

            content = QWidget()
            layout = QVBoxLayout(content)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            layout.addWidget(connection_box)
            layout.addWidget(self.status_label)
            layout.addWidget(self.tabs)

            outer_layout.addWidget(content)
            self.setCentralWidget(root)

        def _build_tab_menu(self) -> QMenu:
            menu = QMenu(self)
            menu.addAction("Disconnect", self._disconnect_session)
            menu.addAction("Add Contact", self._open_add_contact_dialog)
            menu.addAction("Add Channel", self._open_add_channel_dialog)
            menu.addAction("Discover Contacts", self._discover_contacts)
            menu.addAction("My Contact Code", self._show_my_contact_code)
            menu.addAction("Internet Map", self._open_map_tab)
            menu.addAction("Tools", self._show_tools_dialog)
            menu.addAction("About", self._show_about_dialog)
            return menu

        def _build_settings_tab(self) -> QWidget:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)

            self.public_info_fields = self._create_key_value_box(
                "Public Info",
                ["Public key", "Scope location", "Custom vars"],
            )
            self.radio_fields = self._create_key_value_box(
                "Radio Settings",
                ["Max TX", "Frequency", "Current"],
            )
            self.network_fields = self._create_key_value_box(
                "Network Settings",
                ["Max contacts", "Max channels", "Client repeat", "Path hash mode", "Manual add contacts", "Contact count"],
            )
            self.other_settings_fields = self._create_key_value_box(
                "Other Settings",
                ["GPS mode", "GPS interval", "Advert policy", "Telemetry base", "Telemetry location", "Telemetry environment"],
            )
            public_info_layout = self.public_info_fields["layout"]
            self.settings_name_edit = QLineEdit()
            self.settings_name_save_button = QPushButton("Save name")
            self.settings_name_save_button.clicked.connect(self._apply_settings_name)
            name_row = QHBoxLayout()
            name_row.addWidget(self.settings_name_edit)
            name_row.addWidget(self.settings_name_save_button)
            public_info_layout.insertRow(0, "Name", name_row)

            self.settings_time_edit = QLineEdit()
            self.settings_time_edit.setPlaceholderText("YYYY-MM-DD HH:MM:SS")
            self.settings_time_now_button = QPushButton("Use PC UTC now")
            self.settings_time_now_button.clicked.connect(self._use_current_utc_time)
            self.settings_time_save_button = QPushButton("Save time")
            self.settings_time_save_button.clicked.connect(self._apply_settings_time)
            time_row = QHBoxLayout()
            time_row.addWidget(self.settings_time_edit)
            time_row.addWidget(self.settings_time_now_button)
            time_row.addWidget(self.settings_time_save_button)
            public_info_layout.insertRow(4, "Device time", time_row)

            self.settings_lat_edit = QLineEdit()
            self.settings_lat_edit.setPlaceholderText("Latitude")
            self.settings_lon_edit = QLineEdit()
            self.settings_lon_edit.setPlaceholderText("Longitude")
            self.settings_location_save_button = QPushButton("Save location")
            self.settings_location_save_button.clicked.connect(self._apply_settings_location)
            location_row = QHBoxLayout()
            location_row.addWidget(self.settings_lat_edit)
            location_row.addWidget(self.settings_lon_edit)
            location_row.addWidget(self.settings_location_save_button)
            public_info_layout.insertRow(3, "Advert location", location_row)

            radio_info_layout = self.radio_fields["layout"]
            self.settings_preset_combo = QComboBox()
            self.settings_preset_combo.currentIndexChanged.connect(self._update_radio_preset_summary)
            self.settings_repeat_checkbox = QCheckBox("Enable repeat mode")
            self.settings_tx_power_edit = QLineEdit()
            self.settings_tx_power_edit.setPlaceholderText("dBm")
            self.settings_tx_power_save_button = QPushButton("Save TX")
            self.settings_tx_power_save_button.clicked.connect(self._apply_radio_settings)
            tx_row = QHBoxLayout()
            tx_row.addWidget(self.settings_tx_power_edit)
            tx_row.addWidget(self.settings_tx_power_save_button)
            radio_info_layout.insertRow(0, "TX power", tx_row)

            self.settings_radio_save_button = QPushButton("Apply preset")
            self.settings_radio_save_button.clicked.connect(self._apply_radio_settings)
            preset_row = QHBoxLayout()
            preset_row.addWidget(self.settings_preset_combo)
            preset_row.addWidget(self.settings_radio_save_button)
            radio_info_layout.insertRow(3, "Preset", preset_row)
            radio_info_layout.insertRow(4, "Repeat mode", self.settings_repeat_checkbox)
            self.settings_radio_note = QLabel(
                "Presets keep the current device frequency and only change bandwidth, spreading factor, and coding rate."
            )
            self.settings_radio_note.setWordWrap(True)
            radio_info_layout.insertRow(5, "Notes", self.settings_radio_note)

            self.extra_tools_fields = self._create_key_value_box(
                "Extra Tools",
                ["Connection", "Native endpoint", "App name", "Message mode", "Selected contact", "Selected channel"],
            )
            self.device_info_fields = self._create_key_value_box(
                "Device Info",
                ["Model", "Firmware version", "Firmware build", "BLE pin", "Battery", "Storage"],
            )

            for section in (
                self.public_info_fields,
                self.radio_fields,
                self.network_fields,
                self.other_settings_fields,
                self.extra_tools_fields,
                self.device_info_fields,
            ):
                layout.addWidget(section["box"])

            layout.addStretch(1)
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(container)
            return scroll_area

        def _build_contacts_tab(self) -> QWidget:
            contacts_box = QGroupBox("Contacts")
            contacts_layout = QVBoxLayout(contacts_box)
            self.contacts_list = QListWidget()
            self.contacts_list.currentRowChanged.connect(self._show_contact_detail)
            self.contact_detail = QPlainTextEdit()
            self.contact_detail.setReadOnly(True)
            self.contact_conversation_label = QLabel("Select a contact to view the conversation.")
            self.contact_conversation_label.setWordWrap(True)
            self.contact_messages_output = QTextEdit()
            self.contact_messages_output.setReadOnly(True)
            self.contact_message_input = QPlainTextEdit()
            self.contact_message_input.setPlaceholderText("Type a direct message for the selected contact")
            self.contact_send_button = QPushButton("Send direct message")
            self.contact_send_button.clicked.connect(self._send_selected_contact_message)
            self.contact_drain_button = QPushButton("Check queue now")
            self.contact_drain_button.clicked.connect(self._request_manual_drain)
            self.contact_message_status = QLabel("Live notices will place direct messages here when they arrive.")
            self.contact_message_status.setWordWrap(True)
            self.contact_edit_button = QPushButton("Edit contact")
            self.contact_edit_button.clicked.connect(self._open_edit_contact_dialog)
            self.contact_remove_button = QPushButton("Remove contact")
            self.contact_remove_button.clicked.connect(self._confirm_remove_contact)
            action_row = QHBoxLayout()
            action_row.addWidget(self.contact_edit_button)
            action_row.addWidget(self.contact_remove_button)
            action_row.addStretch(1)
            button_row = QHBoxLayout()
            button_row.addWidget(self.contact_send_button)
            button_row.addWidget(self.contact_drain_button)
            contacts_layout.addWidget(self.contacts_list)
            contacts_layout.addWidget(self.contact_detail)
            contacts_layout.addLayout(action_row)
            contacts_layout.addWidget(self.contact_conversation_label)
            contacts_layout.addWidget(QLabel("Direct messages"))
            contacts_layout.addWidget(self.contact_messages_output)
            contacts_layout.addWidget(QLabel("Compose"))
            contacts_layout.addWidget(self.contact_message_input)
            contacts_layout.addLayout(button_row)
            contacts_layout.addWidget(self.contact_message_status)
            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.addWidget(contacts_box)
            return wrapper

        def _build_channels_tab(self) -> QWidget:
            channels_box = QGroupBox("Channels")
            channels_layout = QVBoxLayout(channels_box)
            self.channels_list = QListWidget()
            self.channels_list.currentRowChanged.connect(self._show_channel_detail)
            self.channels_stack = QStackedWidget()
            self.channels_stack.addWidget(self._build_channel_list_page())
            self.channels_stack.addWidget(self._build_channel_detail_page())
            channels_layout.addWidget(self.channels_stack)
            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.addWidget(channels_box)
            return wrapper

        def _build_channel_list_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            self.channels_overview_label = QLabel(
                "Active channels only are shown here. Select one to open its conversation page."
            )
            self.channels_overview_label.setWordWrap(True)
            layout.addWidget(self.channels_overview_label)
            layout.addWidget(self.channels_list)
            return page

        def _build_channel_detail_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)

            self.channel_title_label = QLabel("Channel")
            self.channel_title_label.setWordWrap(True)
            self.channel_title_label.setStyleSheet("font-size: 22px; font-weight: 700; color: #16202a;")

            back_row = QHBoxLayout()
            self.channel_back_button = QPushButton("Back to channel list")
            self.channel_back_button.clicked.connect(self._show_channel_list_page)
            back_row.addWidget(self.channel_back_button)
            self.channel_edit_button = QPushButton("Edit channel")
            self.channel_edit_button.clicked.connect(self._open_edit_channel_dialog)
            self.channel_remove_button = QPushButton("Remove channel")
            self.channel_remove_button.clicked.connect(self._confirm_remove_channel)
            back_row.addWidget(self.channel_edit_button)
            back_row.addWidget(self.channel_remove_button)
            back_row.addStretch(1)

            self.channel_detail = QPlainTextEdit()
            self.channel_detail.setReadOnly(True)
            self.channel_conversation_label = QLabel("Select a channel to view live traffic.")
            self.channel_conversation_label.setWordWrap(True)
            self.channel_activity_label = QLabel("Recent activity: No messages yet")
            self.channel_activity_label.setWordWrap(True)
            self.channel_messages_output = QTextEdit()
            self.channel_messages_output.setReadOnly(True)
            self.channel_message_input = QPlainTextEdit()
            self.channel_message_input.setPlaceholderText("Type a message for the selected channel")
            self.channel_send_button = QPushButton("Send on selected channel")
            self.channel_send_button.clicked.connect(self._send_selected_channel_message)
            self.channel_drain_button = QPushButton("Check queue now")
            self.channel_drain_button.clicked.connect(self._request_manual_drain)
            self.channel_message_status = QLabel("Live notices will place channel messages here when they arrive.")
            self.channel_message_status.setWordWrap(True)
            button_row = QHBoxLayout()
            button_row.addWidget(self.channel_send_button)
            button_row.addWidget(self.channel_drain_button)

            layout.addWidget(self.channel_title_label)
            layout.addLayout(back_row)
            layout.addWidget(self.channel_detail)
            layout.addWidget(self.channel_conversation_label)
            layout.addWidget(self.channel_activity_label)
            layout.addWidget(QLabel("Channel messages"))
            layout.addWidget(self.channel_messages_output)
            layout.addWidget(QLabel("Compose"))
            layout.addWidget(self.channel_message_input)
            layout.addLayout(button_row)
            layout.addWidget(self.channel_message_status)
            return page

        def _build_map_tab(self) -> QWidget:
            wrapper = QWidget()
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            self.map_fields = self._create_key_value_box(
                "Map Overview",
                ["Node location", "Contact locations", "Visible contacts", "Visible channels", "Map mode", "Status"],
            )
            map_notes_box = QGroupBox("Map Notes")
            map_notes_layout = QVBoxLayout(map_notes_box)
            self.map_notes = QPlainTextEdit()
            self.map_notes.setReadOnly(True)
            self.map_notes.setPlainText(
                "Map layout placeholder.\n\n"
                "This tab stays native-first: it will render locations from companion data when a map widget is added.\n"
                "For now it shows the available location facts so layout decisions can be made before adding another dependency."
            )
            map_notes_layout.addWidget(self.map_notes)
            layout.addWidget(self.map_fields["box"])
            layout.addWidget(map_notes_box)
            layout.addStretch(1)
            return wrapper

        def _create_key_value_box(self, title: str, labels: list[str]) -> dict[str, Any]:
            box = QGroupBox(title)
            layout = QFormLayout(box)
            layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            fields: dict[str, QLabel] = {}
            for index, label in enumerate(labels, start=1):
                key = f"line_{index}"
                value = QLabel("-")
                value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                value.setWordWrap(True)
                fields[key] = value
                layout.addRow(label, value)
            return {"box": box, "fields": fields, "layout": layout}

        def refresh(self) -> None:
            try:
                self._config = SessionConfig(
                    host=self.host_edit.text().strip() or self._config.host,
                    port=int(self.port_edit.text().strip() or self._config.port),
                    app_name=self.app_name_edit.text().strip() or self._config.app_name,
                    protocol_version=self._config.protocol_version,
                    timeout_seconds=self._config.timeout_seconds,
                )
            except ValueError:
                QMessageBox.warning(self, "Invalid port", "Port must be a whole number.")
                return
            self._stop_session()
            self._clear_model_view()
            self.status_label.setText(
                f"Connecting to {self._config.host}:{self._config.port} as {self._config.app_name}..."
            )
            self._session_thread = QThread(self)
            self._session_worker = PersistentSessionWorker(self._config)
            self._session_worker.moveToThread(self._session_thread)
            self._session_thread.started.connect(self._session_worker.run)
            self._session_worker.snapshot_loaded.connect(self._handle_snapshot_loaded)
            self._session_worker.messages_received.connect(self._handle_messages_received)
            self._session_worker.log_received.connect(self._handle_log_received)
            self._session_worker.status_changed.connect(self.status_label.setText)
            self._session_worker.command_finished.connect(self._handle_command_finished)
            self._session_thread.finished.connect(self._teardown_session)
            self._session_thread.start()

        def _stop_session(self) -> None:
            if self._session_worker is not None:
                self._session_worker.stop()
            if self._session_thread is not None:
                self._session_thread.wait(2000)

        def _teardown_session(self) -> None:
            if self._session_worker is not None:
                self._session_worker.deleteLater()
                self._session_worker = None
            if self._session_thread is not None:
                self._session_thread.deleteLater()
                self._session_thread = None

        def closeEvent(self, event) -> None:  # type: ignore[override]
            self._stop_session()
            super().closeEvent(event)

        def _handle_snapshot_loaded(self, model: NodePageModel) -> None:
            self._render_model(model)

        def _handle_messages_received(self, payload: object) -> None:
            messages = [message for message in payload if isinstance(message, MessageEnvelope)]
            channel_count = 0
            contact_count = 0
            for message in messages:
                if message.channel_index is not None and message.text is not None:
                    self._append_channel_message(int(message.channel_index), _channel_message_entry(message, direction="received"))
                    channel_count += 1
                    continue
                if message.pubkey_prefix and message.text is not None:
                    self._append_contact_message(message.pubkey_prefix, _contact_message_entry(message, direction="received"))
                    contact_count += 1
            if channel_count:
                selected_channel = self._selected_channel()
                if selected_channel is not None:
                    self._render_channel_messages(int(selected_channel.get("index") or 0))
                self._refresh_channel_list_labels()
            if contact_count:
                selected_contact = self._selected_contact()
                if selected_contact is not None:
                    self._render_contact_messages(self._contact_prefix_for(selected_contact))
                self._refresh_contact_list_labels()
            if channel_count:
                self.channel_message_status.setText(f"Received {channel_count} channel messages automatically.")
            if contact_count:
                self.contact_message_status.setText(f"Received {contact_count} direct messages automatically.")

        def _handle_log_received(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            entry = _format_log_entry(payload)
            self._tool_log_entries.append(entry)
            if len(self._tool_log_entries) > 200:
                del self._tool_log_entries[:-200]
            if self._tools_log_view is not None:
                self._tools_log_view.setPlainText("\n".join(self._tool_log_entries))
                scrollbar = self._tools_log_view.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

        def _handle_command_finished(self, action: str, result: object, error: object) -> None:
            if error is not None:
                if action == "send_direct_message":
                    self.contact_message_status.setText(str(error))
                elif action in {"add_contact_manual", "import_contact_code", "remove_contact"}:
                    QMessageBox.warning(self, "Contact action failed", str(error))
                    self.status_label.setText(f"Contact action failed: {error}")
                elif action == "export_self_contact_code":
                    QMessageBox.warning(self, "My contact code", str(error))
                    self.status_label.setText(f"Contact code export failed: {error}")
                elif action in {"add_channel", "remove_channel"}:
                    QMessageBox.warning(self, "Channel action failed", str(error))
                    self.status_label.setText(f"Channel action failed: {error}")
                elif action in {"get_core_stats", "get_radio_stats", "get_packet_stats"}:
                    QMessageBox.warning(self, "Tools", str(error))
                    self.status_label.setText(f"Tools request failed: {error}")
                elif action == "reboot":
                    QMessageBox.warning(self, "Reboot failed", str(error))
                    self.status_label.setText(f"Reboot failed: {error}")
                elif action in {"set_advert_name", "set_device_time", "set_advert_location", "set_radio_settings"}:
                    QMessageBox.warning(self, "Settings update failed", str(error))
                    self.status_label.setText(f"Settings update failed: {error}")
                else:
                    self.channel_message_status.setText(str(error))
                return
            if action == "refresh_snapshot":
                self.status_label.setText(
                    f"Connected to {self._config.host}:{self._config.port}. Live native message notices are active."
                )
                return
            if action == "send_channel_message" and isinstance(result, dict):
                channel_index = int(result["channel_index"])
                entry = {
                    "timestamp": int(result["timestamp"]),
                    "text": str(result["text"]),
                    "path_len": 0xFF,
                    "snr": None,
                    "direction": "sent",
                }
                self._append_channel_message(channel_index, entry)
                self.channel_message_input.setPlainText("")
                self.channel_message_status.setText(f"Sent message on channel {channel_index}.")
                self._refresh_channel_list_labels()
                self._render_channel_messages(channel_index)
                return
            if action == "send_direct_message" and isinstance(result, dict):
                prefix = str(result["public_key_prefix_hex"])
                entry = {
                    "timestamp": int(result["timestamp"]),
                    "text": str(result["text"]),
                    "path_len": 0xFF,
                    "snr": None,
                    "direction": "sent",
                }
                self._append_contact_message(prefix, entry)
                self.contact_message_input.setPlainText("")
                self.contact_message_status.setText("Direct message sent.")
                self._refresh_contact_list_labels()
                self._render_contact_messages(prefix)
                return
            if action == "add_contact_manual" and isinstance(result, dict):
                contact_name = str(result["name"])
                self.status_label.setText(f"Saved contact {contact_name}. Refreshing contacts...")
                self._enqueue_session_command("refresh_snapshot", {})
                self.tabs.setCurrentIndex(self._contacts_tab_index)
                return
            if action == "remove_contact" and isinstance(result, dict):
                contact_name = str(result.get("name") or "contact")
                self.status_label.setText(f"Removed {contact_name}. Refreshing contacts...")
                self._enqueue_session_command("refresh_snapshot", {})
                self.tabs.setCurrentIndex(self._contacts_tab_index)
                return
            if action == "import_contact_code":
                self.status_label.setText("Imported contact code. Refreshing contacts...")
                self._enqueue_session_command("refresh_snapshot", {})
                self.tabs.setCurrentIndex(self._contacts_tab_index)
                return
            if action == "export_self_contact_code" and isinstance(result, dict):
                self._show_contact_code_dialog(str(result["contact_code_hex"]))
                return
            if action == "add_channel" and isinstance(result, dict):
                channel_index = int(result["channel_index"])
                channel_name = str(result["name"])
                self.status_label.setText(f"Saved channel {channel_index}: {channel_name}. Refreshing active channels...")
                self._enqueue_session_command("refresh_snapshot", {})
                return
            if action == "remove_channel" and isinstance(result, dict):
                channel_index = int(result["channel_index"])
                self.status_label.setText(f"Removed channel {channel_index}. Refreshing active channels...")
                self._enqueue_session_command("refresh_snapshot", {})
                return
            if action == "discover_contacts":
                self.status_label.setText("Sent self advert to help nearby contacts discover this node.")
                return
            if action == "set_advert_name" and isinstance(result, dict):
                self.status_label.setText(f"Saved node name as {result.get('name')}. Refreshing settings...")
                self._enqueue_session_command("refresh_snapshot", {})
                self.tabs.setCurrentIndex(self._settings_tab_index)
                return
            if action == "set_device_time" and isinstance(result, dict):
                self.status_label.setText("Saved device time. Refreshing settings...")
                self._enqueue_session_command("refresh_snapshot", {})
                self.tabs.setCurrentIndex(self._settings_tab_index)
                return
            if action == "set_advert_location" and isinstance(result, dict):
                self.status_label.setText("Saved advert location. Refreshing settings...")
                self._enqueue_session_command("refresh_snapshot", {})
                self.tabs.setCurrentIndex(self._settings_tab_index)
                return
            if action == "set_radio_settings" and isinstance(result, dict):
                self.status_label.setText("Saved radio settings. Refreshing settings...")
                self._enqueue_session_command("refresh_snapshot", {})
                self.tabs.setCurrentIndex(self._settings_tab_index)
                return
            if action == "get_core_stats" and isinstance(result, dict):
                self._tool_stats_sections["core"] = result
                self._refresh_tools_dialog()
                return
            if action == "get_radio_stats" and isinstance(result, dict):
                self._tool_stats_sections["radio"] = result
                self._refresh_tools_dialog()
                return
            if action == "get_packet_stats" and isinstance(result, dict):
                self._tool_stats_sections["packets"] = result
                self._refresh_tools_dialog()
                self.status_label.setText("Tool stats refreshed from the native companion session.")
                return
            if action == "reboot":
                self.status_label.setText("Reboot command sent. The device should drop and re-establish the companion session.")
                return
            if action == "drain_messages" and isinstance(result, dict):
                count = int(result.get("count") or 0)
                self.channel_message_status.setText(f"Manual queue check fetched {count} messages.")
                self.contact_message_status.setText(f"Manual queue check fetched {count} messages.")

        def _render_model(self, model: NodePageModel) -> None:
            self._current_model = model
            node_location = _format_location(model.identity.advert_lat, model.identity.advert_lon)
            gps_mode = model.custom_vars.get("gps", "Unavailable")
            gps_interval = model.custom_vars.get("gps_interval", "Unavailable")
            self._set_settings_edit_enabled(True)
            self.settings_name_edit.setText(model.identity.name)
            self.settings_time_edit.setText(_format_datetime_input(model.identity.device_time))
            self.settings_lat_edit.setText("" if model.identity.advert_lat is None else f"{model.identity.advert_lat:.6f}")
            self.settings_lon_edit.setText("" if model.identity.advert_lon is None else f"{model.identity.advert_lon:.6f}")
            self.settings_tx_power_edit.setText(str(model.radio.tx_power_dbm))
            self._populate_radio_preset_choices(model)

            self._set_fields(
                self.public_info_fields["fields"],
                [
                    model.identity.public_key,
                    node_location,
                    _format_custom_var_summary(model.custom_vars),
                ],
            )
            self._set_fields(
                self.radio_fields["fields"],
                [
                    f"{model.radio.max_tx_power_dbm} dBm",
                    f"{model.radio.freq_mhz:.3f} MHz",
                    _format_radio_tuple(model.radio.freq_mhz, model.radio.bw_khz, model.radio.sf, model.radio.cr),
                ],
            )
            self._set_fields(
                self.network_fields["fields"],
                [
                    str(model.capabilities.max_contacts) if model.capabilities.max_contacts is not None else "Unavailable",
                    str(model.capabilities.max_channels) if model.capabilities.max_channels is not None else "Unavailable",
                    str(model.capabilities.client_repeat) if model.capabilities.client_repeat is not None else "Unavailable",
                    str(model.capabilities.path_hash_mode) if model.capabilities.path_hash_mode is not None else "Unavailable",
                    "Enabled" if model.capabilities.manual_add_contacts else "Disabled",
                    str(len(model.contacts)),
                ],
            )
            self._set_fields(
                self.other_settings_fields["fields"],
                [
                    str(gps_mode),
                    str(gps_interval),
                    str(model.radio.advert_loc_policy),
                    str(model.radio.telemetry_mode_base),
                    str(model.radio.telemetry_mode_loc),
                    str(model.radio.telemetry_mode_env),
                ],
            )
            self._set_fields(
                self.extra_tools_fields["fields"],
                [
                    "Native companion",
                    f"{self._config.host}:{self._config.port}",
                    self._config.app_name,
                    "Persistent session with auto notices",
                    model.contacts[0].get("name", "None") if model.contacts else "None",
                    model.channels[0].get("name", "unused") if model.channels else "unused",
                ],
            )
            self._set_fields(
                self.device_info_fields["fields"],
                [
                    model.identity.model or "Unknown model",
                    model.identity.firmware_version or "Unknown version",
                    model.identity.firmware_build or "Unknown build",
                    str(model.capabilities.ble_pin) if model.capabilities.ble_pin is not None else "Unavailable",
                    f"{model.battery.battery_mv} mV",
                    (
                        f"{model.battery.used_kb or 0} / {model.battery.total_kb or 0} kB"
                        if model.battery.used_kb is not None and model.battery.total_kb is not None
                        else "Unavailable"
                    ),
                ],
            )
            self._set_fields(
                self.map_fields["fields"],
                [
                    node_location,
                    str(model.contacts_with_location_count),
                    str(len(model.contacts)),
                    str(model.provisioned_channel_count),
                    "Placeholder",
                    "Native coordinates only; no tile renderer added yet.",
                ],
            )

            self.contacts_list.clear()
            self._contacts_data = list(model.contacts)
            for contact in self._contacts_data:
                self.contacts_list.addItem(QListWidgetItem(""))
            self._refresh_contact_list_labels()
            if self._contacts_data:
                self.contacts_list.setCurrentRow(0)
            else:
                self.contact_detail.setPlainText("No contacts loaded.")
                self.contact_messages_output.setPlainText("No contact selected.")

            self.channels_list.clear()
            self._channels_data = list(model.channels)
            self._active_channels_data = [channel for channel in self._channels_data if _is_active_channel(channel)]
            for channel in self._active_channels_data:
                self.channels_list.addItem(QListWidgetItem(""))
            self._refresh_channel_list_labels()
            self.channels_stack.setCurrentIndex(0)
            if self._active_channels_data:
                self.channels_list.setCurrentRow(-1)
            else:
                self.channel_detail.setPlainText("No active channels loaded.")
                self.channel_messages_output.setHtml(_render_message_html([], "No channel selected."))
                self.channels_overview_label.setText(
                    "No active channels found. A channel appears here once it has a configured name or key."
                )

            self.map_notes.setPlainText(
                "Map layout placeholder.\n\n"
                f"Node location: {node_location}\n"
                f"Contacts with coordinates: {model.contacts_with_location_count}\n"
                f"Provisioned channels: {model.provisioned_channel_count}\n\n"
                "Contact coordinates\n"
                f"{_format_contact_location_list(model.contacts)}\n\n"
                f"Custom vars\n{_format_custom_vars(model.custom_vars)}"
            )

        def _show_contact_detail(self, index: int) -> None:
            if index < 0 or index >= len(self._contacts_data):
                self.contact_detail.setPlainText("No contact selected.")
                self.contact_messages_output.setPlainText("No contact selected.")
                self.contact_conversation_label.setText("Select a contact to view the conversation.")
                return
            contact = self._contacts_data[index]
            prefix = self._contact_prefix_for(contact)
            self._contact_unread_counts[prefix] = 0
            self._refresh_contact_list_labels()
            self.contact_detail.setPlainText(json.dumps(contact, indent=2, sort_keys=True))
            self.contact_conversation_label.setText(
                f"Conversation with {contact.get('name') or 'Unnamed contact'}"
            )
            self._render_contact_messages(prefix)

        def _show_channel_detail(self, index: int) -> None:
            if index < 0 or index >= len(self._active_channels_data):
                self.channel_detail.setPlainText("No channel selected.")
                self.channel_messages_output.setHtml(_render_message_html([], "No channel selected."))
                self.channel_title_label.setText("Channel")
                self.channel_conversation_label.setText("Select a channel to view live traffic.")
                self.channel_activity_label.setText("Recent activity: No messages yet")
                return
            channel = self._active_channels_data[index]
            channel_index = int(channel.get("index") or 0)
            self._channel_unread_counts[channel_index] = 0
            self._refresh_channel_list_labels()
            self.channel_title_label.setText(
                f"Channel {channel_index}: {channel.get('name') or 'unused'}"
            )
            self.channel_detail.setPlainText(json.dumps(channel, indent=2, sort_keys=True))
            self.channel_conversation_label.setText(
                f"Conversation on channel {channel_index}: {channel.get('name') or 'unused'}"
            )
            self.channel_activity_label.setText(
                f"Recent activity: {_message_preview_text(self._channel_messages.get(channel_index, []))}"
            )
            self._render_channel_messages(channel_index)

            self.channels_stack.setCurrentIndex(1)

        def _show_channel_list_page(self) -> None:
            self.channels_stack.setCurrentIndex(0)
            self.channels_list.blockSignals(True)
            self.channels_list.clearSelection()
            self.channels_list.setCurrentRow(-1)
            self.channels_list.blockSignals(False)

        def _handle_tab_changed(self, index: int) -> None:
            self.menu_button.setVisible(index != self._settings_tab_index)
            if index == self._channels_tab_index:
                self._show_channel_list_page()

        def _disconnect_session(self) -> None:
            self._stop_session()
            self._teardown_session()
            self._clear_model_view()
            self.status_label.setText("Disconnected. Use Reconnect to open the native companion session again.")

        def _open_contact_dialog(self, *, contact: dict[str, Any] | None = None) -> None:
            dialog = QDialog(self)
            editing = contact is not None
            dialog.setWindowTitle("Edit Contact" if editing else "Add Contact")
            layout = QVBoxLayout(dialog)

            intro = QLabel(
                "Update the contact name or public key directly here. Contact-code import stays available for new contacts only."
                if editing
                else "Paste a contact code for the safest add flow, or enter a public key and name manually if you already know them."
            )
            intro.setWordWrap(True)
            layout.addWidget(intro)

            form = QFormLayout()
            contact_code_edit = QPlainTextEdit()
            contact_code_edit.setPlaceholderText("Paste contact code hex here")
            contact_code_edit.setFixedHeight(100)
            name_edit = QLineEdit()
            name_edit.setPlaceholderText("Contact name")
            public_key_edit = QLineEdit()
            public_key_edit.setPlaceholderText("64 hex characters")
            if editing and contact is not None:
                contact_code_edit.setDisabled(True)
                name_edit.setText(str(contact.get("name") or ""))
                public_key_edit.setText(str(contact.get("public_key") or ""))
            form.addRow("Contact code", contact_code_edit)
            form.addRow("Manual name", name_edit)
            form.addRow("Manual public key", public_key_edit)
            layout.addLayout(form)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec() != int(QDialog.DialogCode.Accepted):
                return

            contact_code = contact_code_edit.toPlainText().strip()
            name = name_edit.text().strip()
            public_key = public_key_edit.text().strip()

            if contact_code and not editing:
                try:
                    MeshCoreNativeTcpClient._decode_contact_code(contact_code)
                except ValueError as exc:
                    QMessageBox.warning(self, "Invalid contact code", str(exc))
                    return
                self.status_label.setText("Importing contact code...")
                self._enqueue_session_command("import_contact_code", {"contact_code_hex": contact_code})
                return

            try:
                MeshCoreNativeTcpClient._decode_public_key(public_key)
                MeshCoreNativeTcpClient._encode_channel_name(name)
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid contact", str(exc))
                return

            self.status_label.setText(f"{'Updating' if editing else 'Adding'} contact {name}...")
            self._enqueue_session_command(
                "add_contact_manual",
                {"public_key_hex": public_key, "name": name},
            )

        def _open_add_contact_dialog(self) -> None:
            self._open_contact_dialog(contact=None)

        def _open_edit_contact_dialog(self) -> None:
            contact = self._selected_contact()
            if contact is None:
                QMessageBox.information(self, "Edit contact", "Select a contact first.")
                return
            self._open_contact_dialog(contact=contact)

        def _confirm_remove_contact(self) -> None:
            contact = self._selected_contact()
            if contact is None:
                QMessageBox.information(self, "Remove contact", "Select a contact first.")
                return
            name = str(contact.get("name") or "Unnamed contact")
            answer = QMessageBox.warning(
                self,
                "Remove Contact",
                f"Remove {name} from this node? This leaves any already displayed local message history unchanged until refresh.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.status_label.setText(f"Removing contact {name}...")
            self._enqueue_session_command(
                "remove_contact",
                {"public_key_hex": str(contact.get("public_key") or ""), "name": name},
            )

        def _open_channel_dialog(self, *, channel: dict[str, Any] | None = None) -> None:
            editing = channel is not None
            channel_index = int(channel.get("index") or 0) if channel is not None else 0
            if not editing:
                next_index = self._next_available_channel_index()
                if next_index is None:
                    QMessageBox.warning(self, "Add channel", "No free private channel slots are available.")
                    return
                channel_index = next_index
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Channel" if editing else "Add Channel")
            layout = QVBoxLayout(dialog)
            form = QFormLayout()
            name_edit = QLineEdit()
            name_edit.setPlaceholderText("Private channel name")
            secret_edit = QLineEdit(secrets.token_hex(16))
            secret_edit.setPlaceholderText("32 hex characters")
            secret_edit.setMinimumWidth(420)
            if editing and channel is not None:
                name_edit.setText(str(channel.get("name") or ""))
                secret_edit.setText(str(channel.get("secret_hex") or ""))
            form.addRow("Channel slot", QLabel(str(channel_index)))
            form.addRow("Name", name_edit)
            form.addRow("Secret", secret_edit)
            layout.addLayout(form)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            dialog.resize(560, dialog.sizeHint().height())

            if dialog.exec() != int(QDialog.DialogCode.Accepted):
                return

            name = name_edit.text().strip()
            secret_hex = secret_edit.text().strip()
            try:
                MeshCoreNativeTcpClient._encode_channel_name(name)
                MeshCoreNativeTcpClient._decode_channel_secret(secret_hex)
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid channel", str(exc))
                return

            self.status_label.setText(f"{'Updating' if editing else 'Adding'} channel {channel_index}: {name}...")
            self._enqueue_session_command(
                "add_channel",
                {"channel_index": channel_index, "name": name, "secret_hex": secret_hex},
            )

        def _open_add_channel_dialog(self) -> None:
            self._open_channel_dialog(channel=None)

        def _open_edit_channel_dialog(self) -> None:
            channel = self._selected_channel()
            if channel is None:
                QMessageBox.information(self, "Edit channel", "Select a channel first.")
                return
            self._open_channel_dialog(channel=channel)

        def _confirm_remove_channel(self) -> None:
            channel = self._selected_channel()
            if channel is None:
                QMessageBox.information(self, "Remove channel", "Select a channel first.")
                return
            channel_index = int(channel.get("index") or 0)
            channel_name = str(channel.get("name") or "unused")
            answer = QMessageBox.warning(
                self,
                "Remove Channel",
                f"Remove channel {channel_index}: {channel_name}? This clears that slot on the device.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.status_label.setText(f"Removing channel {channel_index}: {channel_name}...")
            self._enqueue_session_command(
                "remove_channel",
                {"channel_index": channel_index, "name": channel_name},
            )

        def _discover_contacts(self) -> None:
            self.status_label.setText("Broadcasting self advert for contact discovery...")
            self._enqueue_session_command("discover_contacts", {"flood": True})

        def _show_my_contact_code(self) -> None:
            if self._current_model is None or not self._current_model.identity.public_key:
                QMessageBox.information(self, "My contact code", "No identity is loaded yet.")
                return
            self.status_label.setText("Exporting contact code...")
            self._enqueue_session_command("export_self_contact_code", {})

        def _show_contact_code_dialog(self, contact_code_hex: str) -> None:
            dialog = QDialog(self)
            dialog.setWindowTitle("My Contact Code")
            layout = QVBoxLayout(dialog)

            if self._current_model is not None:
                title = QLabel(self._current_model.identity.name or "This node")
                title.setStyleSheet("font-size: 20px; font-weight: 700; color: #16202a;")
                layout.addWidget(title)

            help_label = QLabel(
                "Share this contact code with another MeshCore client so it can import your contact directly."
            )
            help_label.setWordWrap(True)
            layout.addWidget(help_label)

            code_view = QPlainTextEdit()
            code_view.setReadOnly(True)
            code_view.setPlainText(contact_code_hex)
            layout.addWidget(code_view)

            if self._current_model is not None:
                public_key = self._current_model.identity.public_key
                prefix_label = QLabel(f"Public key prefix: {public_key[:12]}")
                prefix_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                layout.addWidget(prefix_label)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dialog.reject)
            buttons.accepted.connect(dialog.accept)
            layout.addWidget(buttons)
            dialog.resize(640, 360)
            dialog.exec()

        def _open_map_tab(self) -> None:
            self.tabs.setCurrentIndex(self._map_tab_index)

        def _show_tools_dialog(self) -> None:
            if self._tools_dialog is None:
                dialog = QDialog(self)
                dialog.setWindowTitle("Tools")
                dialog.setModal(False)
                layout = QVBoxLayout(dialog)

                intro = QLabel(
                    "Use native maintenance actions here. This first pass exposes device stats, live debug log capture, and a guarded reboot."
                )
                intro.setWordWrap(True)
                layout.addWidget(intro)

                stats_label = QLabel("Native stats")
                stats_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #16202a;")
                layout.addWidget(stats_label)

                self._tools_stats_view = QPlainTextEdit()
                self._tools_stats_view.setReadOnly(True)
                self._tools_stats_view.setPlainText(_format_tool_stats_text(self._tool_stats_sections))
                self._tools_stats_view.setMinimumHeight(210)
                layout.addWidget(self._tools_stats_view)

                button_row = QHBoxLayout()
                refresh_stats_button = QPushButton("Refresh Stats")
                refresh_stats_button.clicked.connect(self._request_tool_stats)
                clear_logs_button = QPushButton("Clear Log View")
                clear_logs_button.clicked.connect(self._clear_tool_logs)
                reboot_button = QPushButton("Reboot Node")
                reboot_button.clicked.connect(self._confirm_reboot)
                close_button = QPushButton("Close")
                close_button.clicked.connect(dialog.close)
                button_row.addWidget(refresh_stats_button)
                button_row.addWidget(clear_logs_button)
                button_row.addWidget(reboot_button)
                button_row.addStretch(1)
                button_row.addWidget(close_button)
                layout.addLayout(button_row)

                logs_label = QLabel("Live native debug logs")
                logs_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #16202a;")
                layout.addWidget(logs_label)

                self._tools_log_view = QPlainTextEdit()
                self._tools_log_view.setReadOnly(True)
                self._tools_log_view.setPlainText("\n".join(self._tool_log_entries) or "No native log frames received yet.")
                self._tools_log_view.setMinimumHeight(220)
                layout.addWidget(self._tools_log_view)

                dialog.finished.connect(self._release_tools_dialog)
                dialog.resize(760, 620)
                self._tools_dialog = dialog

            assert self._tools_dialog is not None
            self._refresh_tools_dialog()
            self._tools_dialog.show()
            self._tools_dialog.raise_()
            self._tools_dialog.activateWindow()
            self._request_tool_stats()

        def _request_tool_stats(self) -> None:
            self.status_label.setText("Requesting native tool stats...")
            self._enqueue_session_command("get_core_stats", {})
            self._enqueue_session_command("get_radio_stats", {})
            self._enqueue_session_command("get_packet_stats", {})

        def _clear_tool_logs(self) -> None:
            self._tool_log_entries = []
            if self._tools_log_view is not None:
                self._tools_log_view.setPlainText("No native log frames received yet.")

        def _confirm_reboot(self) -> None:
            answer = QMessageBox.warning(
                self,
                "Reboot Node",
                "Send a native reboot command to the connected device? The current session will drop while the node restarts.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.status_label.setText("Sending reboot command to the device...")
            self._enqueue_session_command("reboot", {})

        def _refresh_tools_dialog(self) -> None:
            if self._tools_stats_view is not None:
                self._tools_stats_view.setPlainText(_format_tool_stats_text(self._tool_stats_sections))
            if self._tools_log_view is not None and self._tool_log_entries:
                self._tools_log_view.setPlainText("\n".join(self._tool_log_entries))

        def _release_tools_dialog(self) -> None:
            self._tools_dialog = None
            self._tools_stats_view = None
            self._tools_log_view = None

        def _show_about_dialog(self) -> None:
            QMessageBox.information(
                self,
                "About",
                "MeshCore Native UI\n\nThis Windows UI stays native-first and uses MeshCore companion commands as its only product contract.",
            )

        def _next_available_channel_index(self) -> int | None:
            if not self._channels_data:
                return None
            channels_by_index = {
                int(channel.get("index") or 0): channel
                for channel in self._channels_data
                if isinstance(channel, dict)
            }
            for index in sorted(channels_by_index):
                if index == 0:
                    continue
                if not _is_active_channel(channels_by_index[index]):
                    return index
            return None

        def _selected_contact(self) -> dict[str, Any] | None:
            index = self.contacts_list.currentRow()
            if index < 0 or index >= len(self._contacts_data):
                return None
            return self._contacts_data[index]

        def _selected_channel(self) -> dict[str, Any] | None:
            index = self.channels_list.currentRow()
            if index < 0 or index >= len(self._active_channels_data):
                return None
            return self._active_channels_data[index]

        def _contact_prefix_for(self, contact: dict[str, Any]) -> str:
            return str(contact.get("public_key") or "")[:12].lower()

        def _send_selected_contact_message(self) -> None:
            contact = self._selected_contact()
            if contact is None:
                self.contact_message_status.setText("Select a contact first.")
                return
            text = self.contact_message_input.toPlainText().strip()
            if not text:
                self.contact_message_status.setText("Enter a direct message first.")
                return
            self.contact_message_status.setText("Sending direct message...")
            self._enqueue_session_command(
                "send_direct_message",
                {
                    "public_key_prefix_hex": self._contact_prefix_for(contact),
                    "text": text,
                    "timestamp": int(time.time()),
                },
            )

        def _send_selected_channel_message(self) -> None:
            channel = self._selected_channel()
            if channel is None:
                self.channel_message_status.setText("Select a channel first.")
                return
            text = self.channel_message_input.toPlainText().strip()
            if not text:
                self.channel_message_status.setText("Enter a message first.")
                return
            self.channel_message_status.setText(f"Sending message on channel {channel.get('index')}...")
            self._enqueue_session_command(
                "send_channel_message",
                {
                    "channel_index": int(channel.get("index") or 0),
                    "text": text,
                    "timestamp": int(time.time()),
                },
            )

        def _request_manual_drain(self) -> None:
            self.channel_message_status.setText("Checking queued native messages now...")
            self.contact_message_status.setText("Checking queued native messages now...")
            self._enqueue_session_command("drain_messages", {"limit": 50})

        def _enqueue_session_command(self, action: str, payload: dict[str, Any]) -> None:
            if self._session_worker is None:
                self.status_label.setText("No active native session. Reconnect first.")
                return
            self._session_worker.enqueue(action, payload)

        def _set_settings_edit_enabled(self, enabled: bool) -> None:
            self.public_info_fields["box"].setEnabled(enabled)
            self.radio_fields["box"].setEnabled(enabled)

        def _populate_radio_preset_choices(self, model: NodePageModel) -> None:
            current_preset = _radio_preset_for_values(model.radio.bw_khz, model.radio.sf, model.radio.cr)
            self.settings_preset_combo.blockSignals(True)
            self.settings_preset_combo.clear()
            selected_index = 0
            if current_preset is None:
                current_payload = {
                    "label": "Current custom",
                    "bw_khz": model.radio.bw_khz,
                    "sf": model.radio.sf,
                    "cr": model.radio.cr,
                }
                self.settings_preset_combo.addItem(
                    f"Current custom ({_format_radio_tuple(model.radio.freq_mhz, model.radio.bw_khz, model.radio.sf, model.radio.cr)})",
                    current_payload,
                )
            for preset in RADIO_PRESETS:
                payload = {"label": preset.label, "bw_khz": preset.bw_khz, "sf": preset.sf, "cr": preset.cr}
                self.settings_preset_combo.addItem(
                    f"{preset.label} ({preset.bw_khz:.1f} kHz / SF{preset.sf} / CR{preset.cr})",
                    payload,
                )
                if current_preset is not None and preset.key == current_preset.key:
                    selected_index = self.settings_preset_combo.count() - 1
            self.settings_preset_combo.setCurrentIndex(selected_index)
            self.settings_preset_combo.blockSignals(False)
            self.settings_repeat_checkbox.setChecked(bool(model.capabilities.client_repeat))
            self._update_radio_preset_summary()

        def _update_radio_preset_summary(self) -> None:
            if self._current_model is None:
                self.settings_radio_note.setText(
                    "Presets keep the current device frequency and only change bandwidth, spreading factor, and coding rate."
                )
                return
            payload = self.settings_preset_combo.currentData()
            if not isinstance(payload, dict):
                self.settings_radio_note.setText(
                    "Presets keep the current device frequency and only change bandwidth, spreading factor, and coding rate."
                )
                return
            self.settings_radio_note.setText(
                "Selected preset will apply "
                f"{_format_radio_tuple(self._current_model.radio.freq_mhz, float(payload['bw_khz']), int(payload['sf']), int(payload['cr']))}. "
                "Repeat mode may be rejected by the device on unsupported frequencies."
            )

        def _use_current_utc_time(self) -> None:
            self.settings_time_edit.setText(_format_datetime_input(int(time.time())))

        def _apply_settings_name(self) -> None:
            try:
                name = self.settings_name_edit.text().strip()
                MeshCoreNativeTcpClient._encode_node_name(name)
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid name", str(exc))
                return
            self.status_label.setText(f"Saving node name {name}...")
            self._enqueue_session_command("set_advert_name", {"name": name})

        def _apply_settings_time(self) -> None:
            try:
                timestamp = _parse_datetime_input(self.settings_time_edit.text())
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid device time", str(exc))
                return
            self.status_label.setText("Saving device time...")
            self._enqueue_session_command("set_device_time", {"timestamp": timestamp})

        def _apply_settings_location(self) -> None:
            try:
                lat = float(self.settings_lat_edit.text().strip())
                lon = float(self.settings_lon_edit.text().strip())
                MeshCoreNativeTcpClient._encode_advert_location(lat, lon)
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid location", str(exc))
                return
            self.status_label.setText("Saving advert location...")
            self._enqueue_session_command("set_advert_location", {"lat": lat, "lon": lon})

        def _apply_radio_settings(self) -> None:
            if self._current_model is None:
                QMessageBox.information(self, "Radio settings", "Reconnect first so current radio values are loaded.")
                return
            payload = self.settings_preset_combo.currentData()
            if not isinstance(payload, dict):
                QMessageBox.warning(self, "Radio settings", "Select a radio preset first.")
                return
            try:
                tx_power_dbm = int(self.settings_tx_power_edit.text().strip())
                MeshCoreNativeTcpClient._encode_radio_params(
                    freq_mhz=self._current_model.radio.freq_mhz,
                    bw_khz=float(payload["bw_khz"]),
                    sf=int(payload["sf"]),
                    cr=int(payload["cr"]),
                    repeat=self.settings_repeat_checkbox.isChecked(),
                )
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid radio settings", str(exc))
                return
            self.status_label.setText("Saving radio settings...")
            self._enqueue_session_command(
                "set_radio_settings",
                {
                    "freq_mhz": self._current_model.radio.freq_mhz,
                    "bw_khz": float(payload["bw_khz"]),
                    "sf": int(payload["sf"]),
                    "cr": int(payload["cr"]),
                    "repeat": self.settings_repeat_checkbox.isChecked(),
                    "tx_power_dbm": tx_power_dbm,
                },
            )

        def _append_channel_message(self, channel_index: int, entry: dict[str, Any]) -> None:
            history = self._channel_messages.setdefault(channel_index, [])
            history.append(entry)
            if len(history) > 100:
                del history[:-100]
            selected_channel = self._selected_channel()
            selected_channel_index = int(selected_channel.get("index") or 0) if selected_channel is not None else None
            if entry.get("direction") == "received" and selected_channel_index != channel_index:
                self._channel_unread_counts[channel_index] = self._channel_unread_counts.get(channel_index, 0) + 1

        def _append_contact_message(self, prefix: str, entry: dict[str, Any]) -> None:
            history = self._contact_messages.setdefault(prefix.lower(), [])
            history.append(entry)
            if len(history) > 100:
                del history[:-100]
            selected_contact = self._selected_contact()
            selected_prefix = self._contact_prefix_for(selected_contact) if selected_contact is not None else None
            if entry.get("direction") == "received" and selected_prefix != prefix.lower():
                self._contact_unread_counts[prefix.lower()] = self._contact_unread_counts.get(prefix.lower(), 0) + 1

        def _refresh_contact_list_labels(self) -> None:
            for index, contact in enumerate(self._contacts_data):
                item = self.contacts_list.item(index)
                if item is None:
                    continue
                prefix = self._contact_prefix_for(contact)
                unread = self._contact_unread_counts.get(prefix, 0)
                preview = _message_preview(self._contact_messages.get(prefix, [None])[-1])
                suffix = f" | {unread} new" if unread else ""
                item.setText(f"{_format_contact(contact)}{suffix}\n{preview}")

        def _refresh_channel_list_labels(self) -> None:
            for index, channel in enumerate(self._active_channels_data):
                item = self.channels_list.item(index)
                if item is None:
                    continue
                channel_index = int(channel.get("index") or 0)
                unread = self._channel_unread_counts.get(channel_index, 0)
                preview = _message_preview(self._channel_messages.get(channel_index, [None])[-1])
                suffix = f" | {unread} new" if unread else ""
                item.setText(f"{_format_channel(channel)}{suffix}\n{preview}")
            self.channels_overview_label.setText(
                f"{len(self._active_channels_data)} active channels. Select one to open its conversation page."
            )
            selected_channel = self._selected_channel()
            if selected_channel is not None:
                channel_index = int(selected_channel.get("index") or 0)
                self.channel_activity_label.setText(
                    f"Recent activity: {_message_preview_text(self._channel_messages.get(channel_index, []))}"
                )

        def _render_contact_messages(self, prefix: str) -> None:
            history = self._contact_messages.get(prefix.lower(), [])
            self.contact_messages_output.setHtml(
                _render_message_html(
                    list(reversed(history)),
                    "No direct messages recorded for this contact yet. Live notices will populate this area automatically.",
                )
            )
            scrollbar = self.contact_messages_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        def _render_channel_messages(self, channel_index: int) -> None:
            history = self._channel_messages.get(channel_index, [])
            self.channel_messages_output.setHtml(
                _render_message_html(
                    list(reversed(history)),
                    "No channel messages recorded for this channel yet. Live notices will populate this area automatically.",
                )
            )
            scrollbar = self.channel_messages_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        def _clear_model_view(self) -> None:
            self._current_model = None
            self._set_settings_edit_enabled(False)
            self._set_fields(self.public_info_fields["fields"], ["-"] * 3)
            self._set_fields(self.radio_fields["fields"], ["-"] * 3)
            self._set_fields(self.network_fields["fields"], ["-"] * 6)
            self._set_fields(self.other_settings_fields["fields"], ["-"] * 6)
            self._set_fields(self.extra_tools_fields["fields"], ["-"] * 6)
            self._set_fields(self.device_info_fields["fields"], ["-"] * 6)
            self._set_fields(self.map_fields["fields"], ["-"] * 6)
            self.settings_name_edit.setText("")
            self.settings_time_edit.setText("")
            self.settings_lat_edit.setText("")
            self.settings_lon_edit.setText("")
            self.settings_tx_power_edit.setText("")
            self.settings_preset_combo.clear()
            self.settings_repeat_checkbox.setChecked(False)
            self.settings_radio_note.setText(
                "Presets keep the current device frequency and only change bandwidth, spreading factor, and coding rate."
            )
            self._contacts_data = []
            self._channels_data = []
            self._active_channels_data = []
            self._channel_messages = {}
            self._contact_messages = {}
            self._channel_unread_counts = {}
            self._contact_unread_counts = {}
            self._tool_stats_sections = {}
            self.contacts_list.clear()
            self.channels_list.clear()
            self.contact_detail.setPlainText("No contact selected.")
            self.channel_detail.setPlainText("No channel selected.")
            self.channel_title_label.setText("Channel")
            self.contact_conversation_label.setText("Select a contact to view the conversation.")
            self.channel_conversation_label.setText("Select a channel to view live traffic.")
            self.channel_activity_label.setText("Recent activity: No messages yet")
            self.channels_overview_label.setText(
                "Active channels only are shown here. Select one to open its conversation page."
            )
            self.channels_stack.setCurrentIndex(0)
            self.contact_messages_output.setHtml(_render_message_html([], "No contact selected."))
            self.channel_messages_output.setHtml(_render_message_html([], "No channel selected."))
            self.contact_message_input.setPlainText("")
            self.channel_message_input.setPlainText("")
            self.contact_message_status.setText("Live notices will place direct messages here when they arrive.")
            self.channel_message_status.setText("Live notices will place channel messages here when they arrive.")
            self.map_notes.setPlainText("Map layout placeholder.")
            self._refresh_tools_dialog()

        @staticmethod
        def _set_fields(fields: dict[str, QLabel], values: list[str]) -> None:
            for key, value in zip(fields.keys(), values):
                fields[key].setText(value)

    app = QApplication.instance() or QApplication([])
    window = NodeWindow()
    window.show()
    return app.exec()