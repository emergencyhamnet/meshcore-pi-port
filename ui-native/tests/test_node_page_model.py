from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from meshcore_ui_native.node_page_model import build_node_page_model  # noqa: E402


class NodePageModelTests(unittest.TestCase):
    def test_build_node_page_model_uses_native_snapshot_fields(self) -> None:
        snapshot = {
            "self_info": {
                "name": "pi-port-probe",
                "public_key": "00" * 32,
                "adv_lat": 40.774777,
                "adv_lon": -74.17829,
                "tx_power": 15,
                "max_tx_power": 17,
                "radio_freq_mhz": 910.525,
                "radio_bw_khz": 62.5,
                "radio_sf": 7,
                "radio_cr": 5,
                "advert_loc_policy": 1,
                "telemetry_mode_base": 2,
                "telemetry_mode_loc": 2,
                "telemetry_mode_env": 2,
                "manual_add_contacts": False,
            },
            "device_info": {
                "model": "Raspberry Pi",
                "version": "v1.16.0",
                "firmware_build": "6 Jun 2026",
                "ble_pin": 123456,
                "client_repeat": 0,
                "path_hash_mode": 1,
                "max_contacts": 100,
                "max_channels": 15,
            },
            "device_time": 1724515200,
            "battery": {"battery_mv": 4167, "used_kb": 0, "total_kb": 0},
            "contacts": [{"name": "N2dh", "public_key": "11" * 32, "gps_lat": 40.7748, "gps_lon": -74.1782}],
            "channels": [
                {"index": 0, "name": "public", "secret_hex": "00" * 16},
                {"index": 1, "name": "private-test", "secret_hex": "ab" * 16},
            ],
            "custom_vars": {"gps": "0"},
        }

        model = build_node_page_model(snapshot).to_dict()

        self.assertEqual(model["identity"]["name"], "pi-port-probe")
        self.assertEqual(model["identity"]["model"], "Raspberry Pi")
        self.assertEqual(model["identity"]["advert_lat"], 40.774777)
        self.assertEqual(model["identity"]["advert_lon"], -74.17829)
        self.assertEqual(model["radio"]["tx_power_dbm"], 15)
        self.assertEqual(model["radio"]["max_tx_power_dbm"], 17)
        self.assertEqual(model["capabilities"]["max_channels"], 15)
        self.assertEqual(model["battery"]["battery_mv"], 4167)
        self.assertEqual(model["contacts_with_location_count"], 1)
        self.assertEqual(model["provisioned_channel_count"], 1)
        self.assertEqual(model["contacts"][0]["name"], "N2dh")
        self.assertEqual(model["channels"][0]["name"], "public")
        self.assertEqual(model["custom_vars"]["gps"], "0")


if __name__ == "__main__":
    unittest.main()