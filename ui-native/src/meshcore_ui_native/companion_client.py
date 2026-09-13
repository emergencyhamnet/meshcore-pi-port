from __future__ import annotations

from dataclasses import asdict, dataclass
import socket
import time
from typing import Any


CMD_APP_START = 0x01
CMD_SEND_TXT_MSG = 0x02
CMD_SEND_CHANNEL_TXT_MSG = 0x03
CMD_GET_CONTACTS = 0x04
CMD_GET_DEVICE_TIME = 0x05
CMD_SET_DEVICE_TIME = 0x06
CMD_SEND_SELF_ADVERT = 0x07
CMD_SET_ADVERT_NAME = 0x08
CMD_ADD_UPDATE_CONTACT = 0x09
CMD_SET_RADIO_PARAMS = 0x0B
CMD_SYNC_NEXT_MESSAGE = 0x0A
CMD_REMOVE_CONTACT = 0x0F
CMD_SET_ADVERT_LATLON = 0x0E
CMD_EXPORT_CONTACT = 0x11
CMD_IMPORT_CONTACT = 0x12
CMD_REBOOT = 0x13
CMD_SET_RADIO_TX_POWER = 0x0C
CMD_GET_BATT_AND_STORAGE = 0x14
CMD_DEVICE_QUERY = 0x16
CMD_GET_STATS = 0x38
CMD_GET_CUSTOM_VARS = 0x28
CMD_GET_CHANNEL = 0x1F
CMD_SET_CHANNEL = 0x20

PACKET_OK = 0x00
PACKET_ERROR = 0x01
PACKET_CONTACT_START = 0x02
PACKET_CONTACT = 0x03
PACKET_CONTACT_END = 0x04
PACKET_SELF_INFO = 0x05
PACKET_MSG_SENT = 0x06
PACKET_CONTACT_MSG_RECV = 0x07
PACKET_CHANNEL_MSG_RECV = 0x08
PACKET_CURRENT_TIME = 0x09
PACKET_NO_MORE_MSGS = 0x0A
PACKET_EXPORT_CONTACT = 0x0B
PACKET_BATTERY = 0x0C
PACKET_DEVICE_INFO = 0x0D
PACKET_CONTACT_MSG_RECV_V3 = 0x10
PACKET_CHANNEL_MSG_RECV_V3 = 0x11
PACKET_CHANNEL_INFO = 0x12
PACKET_CUSTOM_VARS = 0x15
PACKET_STATS = 0x18
PACKET_CHANNEL_DATA_RECV = 0x1B
PACKET_ADVERTISEMENT = 0x80
PACKET_ACK = 0x82
PACKET_MESSAGES_WAITING = 0x83
PACKET_LOG_DATA = 0x88

PUB_KEY_SIZE = 32
MAX_PATH_SIZE = 64
MAX_TEXT_LEN = 133
TXT_TYPE_PLAIN = 0x00
TXT_TYPE_CLI_DATA = 0x01
ADV_TYPE_CHAT = 0x01
OUT_PATH_UNKNOWN = 0xFF
STATS_TYPE_CORE = 0x00
STATS_TYPE_RADIO = 0x01
STATS_TYPE_PACKETS = 0x02

ASYNC_PACKET_TYPES = {
    PACKET_ADVERTISEMENT,
    PACKET_ACK,
    PACKET_MESSAGES_WAITING,
    PACKET_LOG_DATA,
}


class CompanionProtocolError(RuntimeError):
    pass


class CompanionDeviceError(CompanionProtocolError):
    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SelfInfo:
    adv_type: int
    tx_power: int
    max_tx_power: int
    public_key: str
    adv_lat: float
    adv_lon: float
    multi_acks: int
    advert_loc_policy: int
    telemetry_mode_base: int
    telemetry_mode_loc: int
    telemetry_mode_env: int
    manual_add_contacts: bool
    radio_freq_mhz: float
    radio_bw_khz: float
    radio_sf: int
    radio_cr: int
    name: str


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    firmware_version_code: int
    max_contacts: int | None
    max_channels: int | None
    ble_pin: int | None
    firmware_build: str
    model: str
    version: str
    client_repeat: int | None
    path_hash_mode: int | None


@dataclass(frozen=True, slots=True)
class BatteryInfo:
    battery_mv: int
    used_kb: int | None
    total_kb: int | None


@dataclass(frozen=True, slots=True)
class ChannelInfo:
    index: int
    name: str
    secret_hex: str


@dataclass(frozen=True, slots=True)
class ContactInfo:
    public_key: str
    contact_type: int
    flags: int
    out_path_len: int
    out_path: tuple[int, ...]
    name: str
    last_advert_timestamp: int
    gps_lat: float
    gps_lon: float
    lastmod: int


@dataclass(frozen=True, slots=True)
class MessageEnvelope:
    packet_type: int
    channel_index: int | None
    pubkey_prefix: str | None
    path_len: int
    txt_type: int | None
    timestamp: int | None
    text: str | None
    snr: float | None
    data_type: int | None
    payload_hex: str | None


@dataclass(frozen=True, slots=True)
class SendResult:
    packet_type: int
    was_flood: bool | None
    expected_ack: int | None
    suggested_timeout_ms: int | None


@dataclass(frozen=True, slots=True)
class CoreStats:
    battery_mv: int
    uptime_secs: int
    error_flags: int
    queue_len: int


@dataclass(frozen=True, slots=True)
class RadioStats:
    noise_floor: int
    last_rssi: int
    last_snr: float
    tx_air_secs: int
    rx_air_secs: int


@dataclass(frozen=True, slots=True)
class PacketStats:
    packets_recv: int
    packets_sent: int
    sent_flood: int
    sent_direct: int
    recv_flood: int
    recv_direct: int
    recv_errors: int


@dataclass(frozen=True, slots=True)
class LogFrame:
    snr: float
    rssi: int
    payload_hex: str


def encode_command_frame(payload: bytes) -> bytes:
    if len(payload) > 0xFFFF:
        raise ValueError("payload is too large for a companion frame")
    return b"<" + len(payload).to_bytes(2, byteorder="little", signed=False) + payload


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = int(size)
    while remaining > 0:
        chunk = connection.recv(remaining)
        if not chunk:
            raise CompanionProtocolError("connection closed before a full companion frame was received")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def decode_response_frame(frame: bytes) -> bytes:
    if len(frame) < 4:
        raise CompanionProtocolError("companion frame is too short")
    if frame[0] != ord(">"):
        raise CompanionProtocolError("companion response frame is missing the '>' prefix")
    payload_len = int.from_bytes(frame[1:3], byteorder="little", signed=False)
    payload = frame[3:]
    if len(payload) != payload_len:
        raise CompanionProtocolError("companion response frame length does not match payload size")
    return payload


def recv_response_frame(connection: socket.socket) -> bytes:
    header = _recv_exact(connection, 3)
    payload_len = int.from_bytes(header[1:3], byteorder="little", signed=False)
    payload = _recv_exact(connection, payload_len)
    return decode_response_frame(header + payload)


def _decode_utf8_text(payload: bytes) -> str:
    return payload.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()


def _decode_signed_int8(value: int) -> int:
    return value if value < 0x80 else value - 0x100


def parse_self_info(payload: bytes) -> SelfInfo:
    if len(payload) < 58 or payload[0] != PACKET_SELF_INFO:
        raise CompanionProtocolError("invalid PACKET_SELF_INFO payload")
    telemetry_mode = payload[46]
    return SelfInfo(
        adv_type=payload[1],
        tx_power=_decode_signed_int8(payload[2]),
        max_tx_power=payload[3],
        public_key=payload[4:36].hex(),
        adv_lat=int.from_bytes(payload[36:40], byteorder="little", signed=True) / 1_000_000.0,
        adv_lon=int.from_bytes(payload[40:44], byteorder="little", signed=True) / 1_000_000.0,
        multi_acks=payload[44],
        advert_loc_policy=payload[45],
        telemetry_mode_base=telemetry_mode & 0b11,
        telemetry_mode_loc=(telemetry_mode >> 2) & 0b11,
        telemetry_mode_env=(telemetry_mode >> 4) & 0b11,
        manual_add_contacts=payload[47] > 0,
        radio_freq_mhz=int.from_bytes(payload[48:52], byteorder="little", signed=False) / 1000.0,
        radio_bw_khz=int.from_bytes(payload[52:56], byteorder="little", signed=False) / 1000.0,
        radio_sf=payload[56],
        radio_cr=payload[57],
        name=_decode_utf8_text(payload[58:]),
    )


def parse_device_info(payload: bytes) -> DeviceInfo:
    if len(payload) < 2 or payload[0] != PACKET_DEVICE_INFO:
        raise CompanionProtocolError("invalid PACKET_DEVICE_INFO payload")
    firmware_version_code = payload[1]
    max_contacts = payload[2] * 2 if firmware_version_code >= 3 and len(payload) >= 4 else None
    max_channels = payload[3] if firmware_version_code >= 3 and len(payload) >= 4 else None
    ble_pin = int.from_bytes(payload[4:8], byteorder="little", signed=False) if len(payload) >= 8 else None
    firmware_build = _decode_utf8_text(payload[8:20]) if len(payload) >= 20 else ""
    model = _decode_utf8_text(payload[20:60]) if len(payload) >= 60 else ""
    version = _decode_utf8_text(payload[60:80]) if len(payload) >= 80 else ""
    client_repeat = payload[80] if len(payload) >= 81 else None
    path_hash_mode = payload[81] if len(payload) >= 82 else None
    return DeviceInfo(
        firmware_version_code=firmware_version_code,
        max_contacts=max_contacts,
        max_channels=max_channels,
        ble_pin=ble_pin,
        firmware_build=firmware_build,
        model=model,
        version=version,
        client_repeat=client_repeat,
        path_hash_mode=path_hash_mode,
    )


def parse_battery_info(payload: bytes) -> BatteryInfo:
    if len(payload) < 3 or payload[0] != PACKET_BATTERY:
        raise CompanionProtocolError("invalid PACKET_BATTERY payload")
    used_kb = int.from_bytes(payload[3:7], byteorder="little", signed=False) if len(payload) >= 7 else None
    total_kb = int.from_bytes(payload[7:11], byteorder="little", signed=False) if len(payload) >= 11 else None
    return BatteryInfo(
        battery_mv=int.from_bytes(payload[1:3], byteorder="little", signed=False),
        used_kb=used_kb,
        total_kb=total_kb,
    )


def parse_channel_info(payload: bytes) -> ChannelInfo:
    if len(payload) < 50 or payload[0] != PACKET_CHANNEL_INFO:
        raise CompanionProtocolError("invalid PACKET_CHANNEL_INFO payload")
    return ChannelInfo(
        index=payload[1],
        name=_decode_utf8_text(payload[2:34]),
        secret_hex=payload[34:50].hex(),
    )


def parse_contact_info(payload: bytes) -> ContactInfo:
    minimum_size = 1 + PUB_KEY_SIZE + 1 + 1 + 1 + MAX_PATH_SIZE + 32 + 4 + 4 + 4 + 4
    if len(payload) < minimum_size or payload[0] != PACKET_CONTACT:
        raise CompanionProtocolError("invalid PACKET_CONTACT payload")
    offset = 1
    public_key = payload[offset:offset + PUB_KEY_SIZE].hex()
    offset += PUB_KEY_SIZE
    contact_type = payload[offset]
    flags = payload[offset + 1]
    out_path_len = payload[offset + 2]
    offset += 3
    out_path = tuple(payload[offset:offset + MAX_PATH_SIZE])
    offset += MAX_PATH_SIZE
    name = _decode_utf8_text(payload[offset:offset + 32])
    offset += 32
    last_advert_timestamp = int.from_bytes(payload[offset:offset + 4], byteorder="little", signed=False)
    offset += 4
    gps_lat = int.from_bytes(payload[offset:offset + 4], byteorder="little", signed=True) / 1_000_000.0
    offset += 4
    gps_lon = int.from_bytes(payload[offset:offset + 4], byteorder="little", signed=True) / 1_000_000.0
    offset += 4
    lastmod = int.from_bytes(payload[offset:offset + 4], byteorder="little", signed=False)
    return ContactInfo(
        public_key=public_key,
        contact_type=contact_type,
        flags=flags,
        out_path_len=out_path_len,
        out_path=out_path,
        name=name,
        last_advert_timestamp=last_advert_timestamp,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        lastmod=lastmod,
    )


def parse_custom_vars(payload: bytes) -> dict[str, str]:
    if len(payload) < 1 or payload[0] != PACKET_CUSTOM_VARS:
        raise CompanionProtocolError("invalid PACKET_CUSTOM_VARS payload")
    text = _decode_utf8_text(payload[1:])
    if not text:
        return {}
    result: dict[str, str] = {}
    for pair in text.split(","):
        name, separator, value = pair.partition(":")
        if separator:
            result[name.strip()] = value.strip()
    return result


def parse_message_envelope(payload: bytes) -> MessageEnvelope | None:
    if not payload:
        raise CompanionProtocolError("empty message payload")
    packet_type = payload[0]
    if packet_type == PACKET_NO_MORE_MSGS:
        return None
    if packet_type in {PACKET_CONTACT_MSG_RECV, PACKET_CONTACT_MSG_RECV_V3}:
        offset = 1
        snr = None
        if packet_type == PACKET_CONTACT_MSG_RECV_V3:
            snr = _decode_signed_int8(payload[offset]) / 4.0
            offset += 3
        pubkey_prefix = payload[offset:offset + 6].hex()
        offset += 6
        path_len = payload[offset]
        txt_type = payload[offset + 1]
        offset += 2
        timestamp = int.from_bytes(payload[offset:offset + 4], byteorder="little", signed=False)
        offset += 4
        if txt_type == 2:
            offset += 4
        return MessageEnvelope(
            packet_type=packet_type,
            channel_index=None,
            pubkey_prefix=pubkey_prefix,
            path_len=path_len,
            txt_type=txt_type,
            timestamp=timestamp,
            text=_decode_utf8_text(payload[offset:]),
            snr=snr,
            data_type=None,
            payload_hex=None,
        )
    if packet_type in {PACKET_CHANNEL_MSG_RECV, PACKET_CHANNEL_MSG_RECV_V3}:
        offset = 1
        snr = None
        if packet_type == PACKET_CHANNEL_MSG_RECV_V3:
            snr = _decode_signed_int8(payload[offset]) / 4.0
            offset += 3
        channel_index = payload[offset]
        path_len = payload[offset + 1]
        txt_type = payload[offset + 2]
        timestamp = int.from_bytes(payload[offset + 3:offset + 7], byteorder="little", signed=False)
        return MessageEnvelope(
            packet_type=packet_type,
            channel_index=channel_index,
            pubkey_prefix=None,
            path_len=path_len,
            txt_type=txt_type,
            timestamp=timestamp,
            text=_decode_utf8_text(payload[offset + 7:]),
            snr=snr,
            data_type=None,
            payload_hex=None,
        )
    if packet_type == PACKET_CHANNEL_DATA_RECV:
        if len(payload) < 9:
            raise CompanionProtocolError("invalid PACKET_CHANNEL_DATA_RECV payload")
        data_len = payload[8]
        data_end = 9 + data_len
        if data_end > len(payload):
            raise CompanionProtocolError("PACKET_CHANNEL_DATA_RECV payload is truncated")
        return MessageEnvelope(
            packet_type=packet_type,
            channel_index=payload[4],
            pubkey_prefix=None,
            path_len=payload[5],
            txt_type=None,
            timestamp=None,
            text=None,
            snr=_decode_signed_int8(payload[1]) / 4.0,
            data_type=int.from_bytes(payload[6:8], byteorder="little", signed=False),
            payload_hex=payload[9:data_end].hex(),
        )
    raise CompanionProtocolError(f"unsupported message packet type 0x{packet_type:02x}")


def parse_send_result(payload: bytes) -> SendResult:
    if not payload:
        raise CompanionProtocolError("empty send-result payload")
    if payload[0] == PACKET_OK:
        return SendResult(
            packet_type=PACKET_OK,
            was_flood=None,
            expected_ack=None,
            suggested_timeout_ms=None,
        )
    if payload[0] != PACKET_MSG_SENT:
        raise CompanionProtocolError("invalid send-result payload")
    if len(payload) < 10:
        raise CompanionProtocolError("PACKET_MSG_SENT payload is truncated")
    return SendResult(
        packet_type=PACKET_MSG_SENT,
        was_flood=payload[1] == 1,
        expected_ack=int.from_bytes(payload[2:6], byteorder="little", signed=False),
        suggested_timeout_ms=int.from_bytes(payload[6:10], byteorder="little", signed=False),
    )


def parse_log_frame(payload: bytes) -> LogFrame:
    if len(payload) < 3 or payload[0] != PACKET_LOG_DATA:
        raise CompanionProtocolError("invalid PACKET_LOG_DATA payload")
    return LogFrame(
        snr=_decode_signed_int8(payload[1]) / 4.0,
        rssi=_decode_signed_int8(payload[2]),
        payload_hex=payload[3:].hex(),
    )


def parse_stats(payload: bytes) -> CoreStats | RadioStats | PacketStats:
    if len(payload) < 2 or payload[0] != PACKET_STATS:
        raise CompanionProtocolError("invalid PACKET_STATS payload")
    stats_type = payload[1]
    if stats_type == STATS_TYPE_CORE:
        if len(payload) < 11:
            raise CompanionProtocolError("PACKET_STATS core payload is truncated")
        return CoreStats(
            battery_mv=int.from_bytes(payload[2:4], byteorder="little", signed=False),
            uptime_secs=int.from_bytes(payload[4:8], byteorder="little", signed=False),
            error_flags=int.from_bytes(payload[8:10], byteorder="little", signed=False),
            queue_len=payload[10],
        )
    if stats_type == STATS_TYPE_RADIO:
        if len(payload) < 14:
            raise CompanionProtocolError("PACKET_STATS radio payload is truncated")
        return RadioStats(
            noise_floor=int.from_bytes(payload[2:4], byteorder="little", signed=True),
            last_rssi=_decode_signed_int8(payload[4]),
            last_snr=_decode_signed_int8(payload[5]) / 4.0,
            tx_air_secs=int.from_bytes(payload[6:10], byteorder="little", signed=False),
            rx_air_secs=int.from_bytes(payload[10:14], byteorder="little", signed=False),
        )
    if stats_type == STATS_TYPE_PACKETS:
        if len(payload) < 30:
            raise CompanionProtocolError("PACKET_STATS packet payload is truncated")
        return PacketStats(
            packets_recv=int.from_bytes(payload[2:6], byteorder="little", signed=False),
            packets_sent=int.from_bytes(payload[6:10], byteorder="little", signed=False),
            sent_flood=int.from_bytes(payload[10:14], byteorder="little", signed=False),
            sent_direct=int.from_bytes(payload[14:18], byteorder="little", signed=False),
            recv_flood=int.from_bytes(payload[18:22], byteorder="little", signed=False),
            recv_direct=int.from_bytes(payload[22:26], byteorder="little", signed=False),
            recv_errors=int.from_bytes(payload[26:30], byteorder="little", signed=False),
        )
    raise CompanionProtocolError(f"unsupported stats subtype 0x{stats_type:02x}")


class MeshCoreNativeTcpClient:
    def __init__(self, host: str, port: int, *, timeout_seconds: float = 5.0) -> None:
        self._host = str(host).strip() or "127.0.0.1"
        self._port = int(port)
        self._timeout_seconds = float(timeout_seconds)
        self._connection: socket.socket | None = None
        self.notifications: list[bytes] = []

    def __enter__(self) -> MeshCoreNativeTcpClient:
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        if self._connection is not None:
            return
        self._connection = socket.create_connection((self._host, self._port), timeout=self._timeout_seconds)
        self._connection.settimeout(self._timeout_seconds)

    def close(self) -> None:
        if self._connection is None:
            return
        try:
            self._connection.close()
        finally:
            self._connection = None

    def app_start(self, app_name: str = "windows-native-ui") -> SelfInfo:
        reserved = bytes(7)
        payload = bytes([CMD_APP_START]) + reserved + app_name.encode("utf-8")
        return parse_self_info(self._command(payload, expected={PACKET_SELF_INFO}))

    def device_query(self, protocol_version: int = 3) -> DeviceInfo:
        payload = bytes([CMD_DEVICE_QUERY, protocol_version & 0xFF])
        return parse_device_info(self._command(payload, expected={PACKET_DEVICE_INFO}))

    def get_device_time(self) -> int:
        payload = self._command(bytes([CMD_GET_DEVICE_TIME]), expected={PACKET_CURRENT_TIME})
        if len(payload) < 5:
            raise CompanionProtocolError("PACKET_CURRENT_TIME payload is truncated")
        return int.from_bytes(payload[1:5], byteorder="little", signed=False)

    def set_device_time(self, timestamp: int) -> bool:
        payload = bytes([CMD_SET_DEVICE_TIME]) + int(timestamp).to_bytes(4, byteorder="little", signed=False)
        self._command(payload, expected={PACKET_OK})
        return True

    def set_advert_name(self, name: str) -> bool:
        payload = bytes([CMD_SET_ADVERT_NAME]) + self._encode_node_name(name)
        self._command(payload, expected={PACKET_OK})
        return True

    def set_advert_location(self, lat: float, lon: float) -> bool:
        payload = bytes([CMD_SET_ADVERT_LATLON]) + self._encode_advert_location(lat, lon)
        self._command(payload, expected={PACKET_OK})
        return True

    def send_self_advert(self, *, flood: bool = True) -> bool:
        payload = bytes([CMD_SEND_SELF_ADVERT, 1 if flood else 0])
        self._command(payload, expected={PACKET_OK})
        return True

    def get_contacts(self, since: int | None = None) -> list[ContactInfo]:
        payload = bytes([CMD_GET_CONTACTS])
        if since is not None:
            payload += int(since).to_bytes(4, byteorder="little", signed=False)
        self._send_command(payload)
        start_payload = self._read_expected({PACKET_CONTACT_START, PACKET_ERROR})
        if start_payload[0] == PACKET_ERROR:
            self._raise_device_error(start_payload, "GET_CONTACTS failed")
        contacts: list[ContactInfo] = []
        while True:
            frame = self._read_expected({PACKET_CONTACT, PACKET_CONTACT_END, PACKET_ERROR})
            packet_type = frame[0]
            if packet_type == PACKET_CONTACT:
                contacts.append(parse_contact_info(frame))
                continue
            if packet_type == PACKET_CONTACT_END:
                return contacts
            self._raise_device_error(frame, "GET_CONTACTS failed during iteration")

    def add_or_update_contact(
        self,
        *,
        public_key_hex: str,
        name: str,
        contact_type: int = ADV_TYPE_CHAT,
        flags: int = 0,
        last_advert_timestamp: int = 0,
    ) -> bool:
        payload = (
            bytes([CMD_ADD_UPDATE_CONTACT])
            + self._decode_public_key(public_key_hex)
            + bytes([int(contact_type) & 0xFF, int(flags) & 0xFF, OUT_PATH_UNKNOWN])
            + bytes(MAX_PATH_SIZE)
            + self._encode_channel_name(name)
            + int(last_advert_timestamp).to_bytes(4, byteorder="little", signed=False)
        )
        self._command(payload, expected={PACKET_OK})
        return True

    def remove_contact(self, public_key_hex: str) -> bool:
        payload = bytes([CMD_REMOVE_CONTACT]) + self._decode_public_key(public_key_hex)
        self._command(payload, expected={PACKET_OK})
        return True

    def get_channel(self, index: int) -> ChannelInfo | None:
        payload = bytes([CMD_GET_CHANNEL, int(index) & 0xFF])
        frame = self._command(payload, expected={PACKET_CHANNEL_INFO, PACKET_ERROR})
        if frame[0] == PACKET_ERROR:
            error_code = frame[1] if len(frame) >= 2 else None
            if error_code == 2:
                return None
            self._raise_device_error(frame, f"GET_CHANNEL {index} failed")
        return parse_channel_info(frame)

    def get_channels(self, max_channels: int) -> list[ChannelInfo | None]:
        return [self.get_channel(index) for index in range(max(0, int(max_channels)))]

    def get_battery_and_storage(self) -> BatteryInfo:
        return parse_battery_info(self._command(bytes([CMD_GET_BATT_AND_STORAGE]), expected={PACKET_BATTERY}))

    def export_self_contact_code(self) -> str:
        payload = self._command(bytes([CMD_EXPORT_CONTACT]), expected={PACKET_EXPORT_CONTACT})
        return payload[1:].hex()

    def import_contact_code(self, contact_code_hex: str) -> bool:
        payload = bytes([CMD_IMPORT_CONTACT]) + self._decode_contact_code(contact_code_hex)
        self._command(payload, expected={PACKET_OK})
        return True

    def get_custom_vars(self) -> dict[str, str]:
        return parse_custom_vars(self._command(bytes([CMD_GET_CUSTOM_VARS]), expected={PACKET_CUSTOM_VARS}))

    def get_core_stats(self) -> CoreStats:
        payload = self._command(bytes([CMD_GET_STATS, STATS_TYPE_CORE]), expected={PACKET_STATS})
        stats = parse_stats(payload)
        if not isinstance(stats, CoreStats):
            raise CompanionProtocolError("device returned unexpected stats subtype for core stats")
        return stats

    def get_radio_stats(self) -> RadioStats:
        payload = self._command(bytes([CMD_GET_STATS, STATS_TYPE_RADIO]), expected={PACKET_STATS})
        stats = parse_stats(payload)
        if not isinstance(stats, RadioStats):
            raise CompanionProtocolError("device returned unexpected stats subtype for radio stats")
        return stats

    def get_packet_stats(self) -> PacketStats:
        payload = self._command(bytes([CMD_GET_STATS, STATS_TYPE_PACKETS]), expected={PACKET_STATS})
        stats = parse_stats(payload)
        if not isinstance(stats, PacketStats):
            raise CompanionProtocolError("device returned unexpected stats subtype for packet stats")
        return stats

    def reboot(self) -> bool:
        self._send_command(bytes([CMD_REBOOT]) + b"reboot")
        return True

    def set_radio_tx_power(self, tx_power_dbm: int) -> bool:
        encoded = int(tx_power_dbm).to_bytes(1, byteorder="little", signed=True)
        self._command(bytes([CMD_SET_RADIO_TX_POWER]) + encoded, expected={PACKET_OK})
        return True

    def set_radio_params(
        self,
        *,
        freq_mhz: float,
        bw_khz: float,
        sf: int,
        cr: int,
        repeat: bool,
    ) -> bool:
        payload = bytes([CMD_SET_RADIO_PARAMS]) + self._encode_radio_params(
            freq_mhz=freq_mhz,
            bw_khz=bw_khz,
            sf=sf,
            cr=cr,
            repeat=repeat,
        )
        self._command(payload, expected={PACKET_OK})
        return True

    def set_channel(self, *, index: int, name: str, secret_hex: str) -> bool:
        encoded_name = self._encode_channel_name(name, allow_empty=True)
        encoded_secret = self._decode_channel_secret(secret_hex)
        payload = bytes([CMD_SET_CHANNEL, int(index) & 0xFF]) + encoded_name + encoded_secret
        self._command(payload, expected={PACKET_OK})
        return True

    def remove_channel(self, index: int) -> bool:
        return self.set_channel(index=index, name="", secret_hex="00" * 16)

    def send_channel_text_message(
        self,
        *,
        channel_index: int,
        text: str,
        timestamp: int | None = None,
    ) -> SendResult:
        encoded_text = self._encode_text_message(text)
        message_timestamp = int(timestamp if timestamp is not None else time.time())
        payload = (
            bytes([CMD_SEND_CHANNEL_TXT_MSG, TXT_TYPE_PLAIN, int(channel_index) & 0xFF])
            + message_timestamp.to_bytes(4, byteorder="little", signed=False)
            + encoded_text
        )
        frame = self._command(payload, expected={PACKET_OK})
        return parse_send_result(frame)

    def send_direct_text_message(
        self,
        *,
        public_key_prefix_hex: str,
        text: str,
        attempt: int = 0,
        timestamp: int | None = None,
        text_type: int = TXT_TYPE_PLAIN,
    ) -> SendResult:
        prefix = self._decode_contact_prefix(public_key_prefix_hex)
        encoded_text = self._encode_text_message(text)
        message_timestamp = int(timestamp if timestamp is not None else time.time())
        payload = (
            bytes([CMD_SEND_TXT_MSG, text_type & 0xFF, int(attempt) & 0xFF])
            + message_timestamp.to_bytes(4, byteorder="little", signed=False)
            + prefix
            + encoded_text
        )
        frame = self._command(payload, expected={PACKET_MSG_SENT})
        return parse_send_result(frame)

    def sync_next_message(self) -> MessageEnvelope | None:
        frame = self._command(
            bytes([CMD_SYNC_NEXT_MESSAGE]),
            expected={
                PACKET_CONTACT_MSG_RECV,
                PACKET_CHANNEL_MSG_RECV,
                PACKET_CONTACT_MSG_RECV_V3,
                PACKET_CHANNEL_MSG_RECV_V3,
                PACKET_CHANNEL_DATA_RECV,
                PACKET_NO_MORE_MSGS,
            },
        )
        return parse_message_envelope(frame)

    def drain_messages(self, *, limit: int = 50) -> list[MessageEnvelope]:
        messages: list[MessageEnvelope] = []
        for _ in range(max(0, int(limit))):
            message = self.sync_next_message()
            if message is None:
                break
            messages.append(message)
        return messages

    def collect_session_snapshot(self, *, app_name: str = "windows-native-ui", protocol_version: int = 3) -> dict[str, Any]:
        self_info = self.app_start(app_name=app_name)
        device_info = self.device_query(protocol_version=protocol_version)
        device_time = self.get_device_time()
        contacts = [asdict(contact) for contact in self.get_contacts()]
        max_channels = device_info.max_channels or 0
        channels = [asdict(channel) if channel is not None else None for channel in self.get_channels(max_channels)]
        battery = asdict(self.get_battery_and_storage())
        custom_vars: dict[str, str] = {}
        try:
            custom_vars = self.get_custom_vars()
        except CompanionDeviceError:
            custom_vars = {}
        return {
            "self_info": asdict(self_info),
            "device_info": asdict(device_info),
            "device_time": device_time,
            "contacts": contacts,
            "channels": channels,
            "battery": battery,
            "custom_vars": custom_vars,
        }

    def read_next_frame(self, *, timeout_seconds: float | None = None) -> bytes | None:
        if self._connection is None:
            raise CompanionProtocolError("client is not connected")
        previous_timeout = self._connection.gettimeout()
        if timeout_seconds is not None:
            self._connection.settimeout(timeout_seconds)
        try:
            return recv_response_frame(self._connection)
        except socket.timeout:
            return None
        finally:
            self._connection.settimeout(previous_timeout)

    def pop_notifications(self) -> list[bytes]:
        notifications = list(self.notifications)
        self.notifications.clear()
        return notifications

    def _command(self, payload: bytes, *, expected: set[int]) -> bytes:
        self._send_command(payload)
        return self._read_expected(expected)

    @staticmethod
    def _encode_text_message(text: str) -> bytes:
        encoded = str(text).encode("utf-8")
        if not encoded:
            raise ValueError("text message must not be empty")
        if len(encoded) > MAX_TEXT_LEN:
            raise ValueError(f"text message exceeds MeshCore limit of {MAX_TEXT_LEN} UTF-8 bytes")
        return encoded

    @staticmethod
    def _encode_node_name(name: str) -> bytes:
        cleaned = str(name).strip()
        if not cleaned:
            raise ValueError("node name must not be empty")
        encoded = cleaned.encode("utf-8")
        if len(encoded) > 31:
            raise ValueError("node name exceeds MeshCore limit of 31 UTF-8 bytes")
        return encoded

    @staticmethod
    def _encode_advert_location(lat: float, lon: float) -> bytes:
        latitude = float(lat)
        longitude = float(lon)
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError("longitude must be between -180 and 180 degrees")
        return (
            int(round(latitude * 1_000_000)).to_bytes(4, byteorder="little", signed=True)
            + int(round(longitude * 1_000_000)).to_bytes(4, byteorder="little", signed=True)
        )

    @staticmethod
    def _encode_radio_params(
        *,
        freq_mhz: float,
        bw_khz: float,
        sf: int,
        cr: int,
        repeat: bool,
    ) -> bytes:
        freq_value = int(round(float(freq_mhz) * 1000))
        bw_value = int(round(float(bw_khz) * 1000))
        spreading_factor = int(sf)
        coding_rate = int(cr)
        if freq_value < 150_000 or freq_value > 2_500_000:
            raise ValueError("radio frequency must be between 150.000 and 2500.000 MHz")
        if bw_value < 7_000 or bw_value > 500_000:
            raise ValueError("radio bandwidth must be between 7.0 and 500.0 kHz")
        if spreading_factor < 5 or spreading_factor > 12:
            raise ValueError("spreading factor must be between 5 and 12")
        if coding_rate < 5 or coding_rate > 8:
            raise ValueError("coding rate must be between 5 and 8")
        return (
            freq_value.to_bytes(4, byteorder="little", signed=False)
            + bw_value.to_bytes(4, byteorder="little", signed=False)
            + bytes([spreading_factor, coding_rate, 1 if repeat else 0])
        )

    @staticmethod
    def _decode_contact_prefix(public_key_prefix_hex: str) -> bytes:
        cleaned = "".join(str(public_key_prefix_hex).split()).lower()
        if len(cleaned) != 12:
            raise ValueError("public key prefix must be exactly 12 hex characters")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError("public key prefix must be valid hexadecimal") from exc

    @staticmethod
    def _decode_public_key(public_key_hex: str) -> bytes:
        cleaned = "".join(str(public_key_hex).split()).lower()
        if len(cleaned) != 64:
            raise ValueError("public key must be exactly 64 hex characters")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError("public key must be valid hexadecimal") from exc

    @staticmethod
    def _encode_channel_name(name: str, *, allow_empty: bool = False) -> bytes:
        cleaned = str(name).strip()
        if not cleaned and not allow_empty:
            raise ValueError("channel name must not be empty")
        encoded = cleaned.encode("utf-8")
        if len(encoded) > 32:
            raise ValueError("channel name exceeds MeshCore limit of 32 UTF-8 bytes")
        return encoded.ljust(32, b"\x00")

    @staticmethod
    def _decode_channel_secret(secret_hex: str) -> bytes:
        cleaned = "".join(str(secret_hex).split()).lower()
        if len(cleaned) != 32:
            raise ValueError("channel secret must be exactly 32 hex characters")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError("channel secret must be valid hexadecimal") from exc

    @staticmethod
    def _decode_contact_code(contact_code_hex: str) -> bytes:
        cleaned = "".join(str(contact_code_hex).split()).lower()
        if len(cleaned) < 2:
            raise ValueError("contact code must not be empty")
        if len(cleaned) % 2 != 0:
            raise ValueError("contact code must contain an even number of hex characters")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError("contact code must be valid hexadecimal") from exc

    def _send_command(self, payload: bytes) -> None:
        if self._connection is None:
            self.connect()
        assert self._connection is not None
        self._connection.sendall(encode_command_frame(payload))

    def _read_expected(self, expected: set[int]) -> bytes:
        if self._connection is None:
            raise CompanionProtocolError("client is not connected")
        while True:
            payload = recv_response_frame(self._connection)
            packet_type = payload[0] if payload else None
            if packet_type in ASYNC_PACKET_TYPES:
                self.notifications.append(payload)
                continue
            if packet_type == PACKET_ERROR and PACKET_ERROR not in expected:
                self._raise_device_error(payload, "device rejected command")
            if packet_type not in expected:
                raise CompanionProtocolError(
                    f"unexpected packet type 0x{packet_type:02x}; expected one of {sorted(expected)}"
                )
            return payload

    @staticmethod
    def _raise_device_error(payload: bytes, prefix: str) -> None:
        error_code = payload[1] if len(payload) >= 2 else None
        raise CompanionDeviceError(error_code, f"{prefix}: device returned error code {error_code}")