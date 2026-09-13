from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from meshcore_ui_native.companion_client import (  # noqa: E402
    PACKET_LOG_DATA,
    PACKET_STATS,
    MAX_TEXT_LEN,
    PACKET_BATTERY,
    PACKET_CHANNEL_INFO,
    PACKET_CONTACT,
    PACKET_CUSTOM_VARS,
    PACKET_DEVICE_INFO,
    PACKET_MSG_SENT,
    PACKET_OK,
    PACKET_SELF_INFO,
    CoreStats,
    LogFrame,
    PacketStats,
    RadioStats,
    SendResult,
    decode_response_frame,
    encode_command_frame,
    parse_log_frame,
    parse_battery_info,
    parse_channel_info,
    parse_contact_info,
    parse_custom_vars,
    parse_device_info,
    parse_send_result,
    parse_self_info,
    parse_stats,
    MeshCoreNativeTcpClient,
)


class CompanionClientTests(unittest.TestCase):
    def test_encode_command_frame_uses_stream_prefix_and_little_endian_length(self) -> None:
        frame = encode_command_frame(bytes([0x01, 0x02, 0x03]))
        self.assertEqual(frame, b"<\x03\x00\x01\x02\x03")

    def test_decode_response_frame_validates_prefix_and_length(self) -> None:
        payload = decode_response_frame(b">\x02\x00\x05\x09")
        self.assertEqual(payload, bytes([0x05, 0x09]))

    def test_parse_self_info_extracts_radio_and_identity_fields(self) -> None:
        payload = bytearray(58 + len("pi-port-probe"))
        payload[0] = PACKET_SELF_INFO
        payload[1] = 1
        payload[2] = 17
        payload[3] = 20
        payload[4:36] = bytes(range(32))
        payload[36:40] = int(51_507_400).to_bytes(4, byteorder="little", signed=True)
        payload[40:44] = int(-127_800).to_bytes(4, byteorder="little", signed=True)
        payload[44] = 1
        payload[45] = 1
        payload[46] = 0b00_01_10
        payload[47] = 1
        payload[48:52] = int(915_500).to_bytes(4, byteorder="little", signed=False)
        payload[52:56] = int(250_000).to_bytes(4, byteorder="little", signed=False)
        payload[56] = 9
        payload[57] = 5
        payload[58:] = b"pi-port-probe"

        info = parse_self_info(bytes(payload))

        self.assertEqual(info.tx_power, 17)
        self.assertEqual(info.max_tx_power, 20)
        self.assertEqual(info.public_key, bytes(range(32)).hex())
        self.assertAlmostEqual(info.adv_lat, 51.5074)
        self.assertAlmostEqual(info.adv_lon, -0.1278)
        self.assertEqual(info.telemetry_mode_base, 2)
        self.assertEqual(info.telemetry_mode_loc, 1)
        self.assertEqual(info.telemetry_mode_env, 0)
        self.assertEqual(info.radio_freq_mhz, 915.5)
        self.assertEqual(info.radio_bw_khz, 250.0)
        self.assertEqual(info.name, "pi-port-probe")

    def test_parse_device_info_extracts_capacity_and_build_fields(self) -> None:
        payload = bytearray(82)
        payload[0] = PACKET_DEVICE_INFO
        payload[1] = 13
        payload[2] = 50
        payload[3] = 40
        payload[4:8] = int(123456).to_bytes(4, byteorder="little", signed=False)
        payload[8:20] = b"6 Jun 2026\x00\x00"
        payload[20:60] = b"PiProbe".ljust(40, b"\x00")
        payload[60:80] = b"v1.16.0".ljust(20, b"\x00")
        payload[80] = 2
        payload[81] = 1

        info = parse_device_info(bytes(payload))

        self.assertEqual(info.firmware_version_code, 13)
        self.assertEqual(info.max_contacts, 100)
        self.assertEqual(info.max_channels, 40)
        self.assertEqual(info.ble_pin, 123456)
        self.assertEqual(info.firmware_build, "6 Jun 2026")
        self.assertEqual(info.model, "PiProbe")
        self.assertEqual(info.version, "v1.16.0")
        self.assertEqual(info.client_repeat, 2)
        self.assertEqual(info.path_hash_mode, 1)

    def test_parse_contact_info_matches_firmware_layout(self) -> None:
        payload = bytearray(1 + 32 + 1 + 1 + 1 + 64 + 32 + 4 + 4 + 4 + 4)
        payload[0] = PACKET_CONTACT
        payload[1:33] = bytes(range(16, 48))
        payload[33] = 1
        payload[34] = 3
        payload[35] = 4
        payload[36:40] = bytes([1, 2, 3, 4])
        payload[100:112] = b"probe-contact"
        payload[132:136] = int(123456).to_bytes(4, byteorder="little", signed=False)
        payload[136:140] = int(51_507_400).to_bytes(4, byteorder="little", signed=True)
        payload[140:144] = int(-127_800).to_bytes(4, byteorder="little", signed=True)
        payload[144:148] = int(654321).to_bytes(4, byteorder="little", signed=False)

        info = parse_contact_info(bytes(payload))

        self.assertEqual(info.public_key, bytes(range(16, 48)).hex())
        self.assertEqual(info.contact_type, 1)
        self.assertEqual(info.flags, 3)
        self.assertEqual(info.out_path_len, 4)
        self.assertEqual(info.out_path[:4], (1, 2, 3, 4))
        self.assertEqual(info.name, "probe-contact")
        self.assertEqual(info.last_advert_timestamp, 123456)
        self.assertAlmostEqual(info.gps_lat, 51.5074)
        self.assertAlmostEqual(info.gps_lon, -0.1278)
        self.assertEqual(info.lastmod, 654321)

    def test_parse_battery_info_handles_storage_fields(self) -> None:
        payload = bytes([PACKET_BATTERY]) + int(4100).to_bytes(2, byteorder="little") + int(128).to_bytes(4, byteorder="little") + int(1024).to_bytes(4, byteorder="little")

        info = parse_battery_info(payload)

        self.assertEqual(info.battery_mv, 4100)
        self.assertEqual(info.used_kb, 128)
        self.assertEqual(info.total_kb, 1024)

    def test_parse_custom_vars_maps_name_value_pairs(self) -> None:
        payload = bytes([PACKET_CUSTOM_VARS]) + b"gps:1,gps_interval:300,foo:bar"

        info = parse_custom_vars(payload)

        self.assertEqual(info["gps"], "1")
        self.assertEqual(info["gps_interval"], "300")
        self.assertEqual(info["foo"], "bar")

    def test_parse_channel_info_stops_at_first_null_in_name_field(self) -> None:
        payload = bytearray(50)
        payload[0] = PACKET_CHANNEL_INFO
        payload[1] = 1
        payload[2:34] = b"private-test\x00garbage-after-null!!!!"
        payload[34:50] = bytes.fromhex("8f2d88a54827f026c5fb574d0f591dda")

        info = parse_channel_info(bytes(payload))

        self.assertEqual(info.name, "private-test")

    def test_parse_send_result_handles_channel_ok_frame(self) -> None:
        result = parse_send_result(bytes([PACKET_OK]))

        self.assertEqual(result, SendResult(packet_type=PACKET_OK, was_flood=None, expected_ack=None, suggested_timeout_ms=None))

    def test_parse_send_result_handles_direct_send_metadata(self) -> None:
        payload = bytes([PACKET_MSG_SENT, 1]) + int(0x12345678).to_bytes(4, byteorder="little") + int(2500).to_bytes(4, byteorder="little")

        result = parse_send_result(payload)

        self.assertEqual(result.packet_type, PACKET_MSG_SENT)
        self.assertTrue(result.was_flood)
        self.assertEqual(result.expected_ack, 0x12345678)
        self.assertEqual(result.suggested_timeout_ms, 2500)

    def test_parse_log_frame_extracts_signal_and_raw_payload(self) -> None:
        payload = bytes([PACKET_LOG_DATA, 0xF8, 0xC9, 0x01, 0x02, 0xAB])

        log_frame = parse_log_frame(payload)

        self.assertEqual(log_frame, LogFrame(snr=-2.0, rssi=-55, payload_hex="0102ab"))

    def test_parse_stats_handles_core_subtype(self) -> None:
        payload = (
            bytes([PACKET_STATS, 0x00])
            + int(4123).to_bytes(2, byteorder="little")
            + int(3600).to_bytes(4, byteorder="little")
            + int(5).to_bytes(2, byteorder="little")
            + bytes([7])
        )

        stats = parse_stats(payload)

        self.assertEqual(stats, CoreStats(battery_mv=4123, uptime_secs=3600, error_flags=5, queue_len=7))

    def test_parse_stats_handles_radio_subtype(self) -> None:
        payload = (
            bytes([PACKET_STATS, 0x01])
            + int(-110).to_bytes(2, byteorder="little", signed=True)
            + bytes([0xC4, 0x0E])
            + int(12).to_bytes(4, byteorder="little")
            + int(34).to_bytes(4, byteorder="little")
        )

        stats = parse_stats(payload)

        self.assertEqual(stats, RadioStats(noise_floor=-110, last_rssi=-60, last_snr=3.5, tx_air_secs=12, rx_air_secs=34))

    def test_parse_stats_handles_packet_subtype(self) -> None:
        payload = bytes([PACKET_STATS, 0x02])
        for value in (101, 77, 41, 36, 55, 46, 3):
            payload += int(value).to_bytes(4, byteorder="little")

        stats = parse_stats(payload)

        self.assertEqual(
            stats,
            PacketStats(
                packets_recv=101,
                packets_sent=77,
                sent_flood=41,
                sent_direct=36,
                recv_flood=55,
                recv_direct=46,
                recv_errors=3,
            ),
        )

    def test_encode_text_message_rejects_oversized_payloads(self) -> None:
        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._encode_text_message("x" * (MAX_TEXT_LEN + 1))

    def test_encode_node_name_limits_to_31_utf8_bytes(self) -> None:
        encoded = MeshCoreNativeTcpClient._encode_node_name("pi-port-probe")

        self.assertEqual(encoded, b"pi-port-probe")

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._encode_node_name("")

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._encode_node_name("x" * 32)

    def test_encode_advert_location_uses_signed_microdegrees(self) -> None:
        encoded = MeshCoreNativeTcpClient._encode_advert_location(51.5074, -0.1278)

        self.assertEqual(encoded[:4], int(51_507_400).to_bytes(4, byteorder="little", signed=True))
        self.assertEqual(encoded[4:], int(-127_800).to_bytes(4, byteorder="little", signed=True))

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._encode_advert_location(91.0, 0.0)

    def test_encode_radio_params_matches_companion_payload_layout(self) -> None:
        encoded = MeshCoreNativeTcpClient._encode_radio_params(
            freq_mhz=869.525,
            bw_khz=250.0,
            sf=11,
            cr=5,
            repeat=True,
        )

        self.assertEqual(encoded[:4], int(869_525).to_bytes(4, byteorder="little", signed=False))
        self.assertEqual(encoded[4:8], int(250_000).to_bytes(4, byteorder="little", signed=False))
        self.assertEqual(encoded[8:], bytes([11, 5, 1]))

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._encode_radio_params(freq_mhz=149.0, bw_khz=250.0, sf=11, cr=5, repeat=False)

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._encode_radio_params(freq_mhz=869.525, bw_khz=600.0, sf=11, cr=5, repeat=False)

    def test_decode_contact_prefix_requires_6_byte_hex_prefix(self) -> None:
        prefix = MeshCoreNativeTcpClient._decode_contact_prefix("aabbccddeeff")

        self.assertEqual(prefix, bytes.fromhex("aabbccddeeff"))

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._decode_contact_prefix("abcd")

    def test_encode_channel_name_pads_to_32_bytes(self) -> None:
        encoded = MeshCoreNativeTcpClient._encode_channel_name("private-test")

        self.assertEqual(len(encoded), 32)
        self.assertEqual(encoded[:12], b"private-test")
        self.assertEqual(encoded[12:], b"\x00" * 20)

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._encode_channel_name("")

    def test_encode_channel_name_allows_empty_name_for_channel_delete(self) -> None:
        encoded = MeshCoreNativeTcpClient._encode_channel_name("", allow_empty=True)

        self.assertEqual(len(encoded), 32)
        self.assertEqual(encoded, b"\x00" * 32)

    def test_decode_channel_secret_requires_16_byte_hex_secret(self) -> None:
        secret = MeshCoreNativeTcpClient._decode_channel_secret("ab" * 16)

        self.assertEqual(secret, bytes.fromhex("ab" * 16))

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._decode_channel_secret("ab" * 15)

    def test_decode_public_key_requires_full_32_byte_hex_key(self) -> None:
        public_key = MeshCoreNativeTcpClient._decode_public_key("ab" * 32)

        self.assertEqual(public_key, bytes.fromhex("ab" * 32))

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._decode_public_key("ab" * 31)

    def test_decode_contact_code_accepts_hex_blob(self) -> None:
        contact_code = MeshCoreNativeTcpClient._decode_contact_code("0102aabbcc")

        self.assertEqual(contact_code, bytes.fromhex("0102aabbcc"))

        with self.assertRaises(ValueError):
            MeshCoreNativeTcpClient._decode_contact_code("abc")


if __name__ == "__main__":
    unittest.main()