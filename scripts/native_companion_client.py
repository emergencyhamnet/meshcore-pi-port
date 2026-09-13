from __future__ import annotations

from dataclasses import asdict, dataclass
import socket
from typing import Any


CMD_APP_START = 0x01
CMD_GET_CONTACTS = 0x04
CMD_GET_DEVICE_TIME = 0x05
CMD_SET_DEVICE_TIME = 0x06
CMD_SYNC_NEXT_MESSAGE = 0x0A
CMD_SET_RADIO_TX_POWER = 0x0C
CMD_GET_BATT_AND_STORAGE = 0x14
CMD_DEVICE_QUERY = 0x16
CMD_GET_CUSTOM_VARS = 0x28
CMD_GET_CHANNEL = 0x1F

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
PACKET_BATTERY = 0x0C
PACKET_DEVICE_INFO = 0x0D
PACKET_CONTACT_MSG_RECV_V3 = 0x10
PACKET_CHANNEL_MSG_RECV_V3 = 0x11
PACKET_CHANNEL_INFO = 0x12
PACKET_CUSTOM_VARS = 0x15
PACKET_CHANNEL_DATA_RECV = 0x1B
PACKET_ADVERTISEMENT = 0x80
PACKET_ACK = 0x82
PACKET_MESSAGES_WAITING = 0x83
PACKET_LOG_DATA = 0x88

ERR_CODE_BAD_STATE = 4

PUB_KEY_SIZE = 32
MAX_PATH_SIZE = 64

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

    def get_custom_vars(self) -> dict[str, str]:
        return parse_custom_vars(self._command(bytes([CMD_GET_CUSTOM_VARS]), expected={PACKET_CUSTOM_VARS}))

    def set_radio_tx_power(self, tx_power_dbm: int) -> bool:
        encoded = int(tx_power_dbm).to_bytes(1, byteorder="little", signed=True)
        self._command(bytes([CMD_SET_RADIO_TX_POWER]) + encoded, expected={PACKET_OK})
        return True

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

    def _command(self, payload: bytes, *, expected: set[int]) -> bytes:
        self._send_command(payload)
        return self._read_expected(expected)

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
