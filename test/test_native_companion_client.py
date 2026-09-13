from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from native_companion_client import (  # noqa: E402
    PACKET_BATTERY,
    PACKET_CHANNEL_INFO,
    PACKET_CONTACT,
    PACKET_CUSTOM_VARS,
    PACKET_DEVICE_INFO,
    PACKET_SELF_INFO,
    decode_response_frame,
    encode_command_frame,
    parse_battery_info,
    parse_channel_info,
    parse_contact_info,
    parse_custom_vars,
    parse_device_info,
    parse_self_info,
)


class NativeCompanionClientTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()