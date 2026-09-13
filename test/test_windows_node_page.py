from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from windows_node_page import (  # noqa: E402
    build_directed_private_message_request,
    build_node_page_model,
    render_node_page_html,
)


class WindowsNodePageTests(unittest.TestCase):
    def test_build_node_page_model_maps_runtime_identity_and_channels(self) -> None:
        snapshot = {
            "snapshot": {
                "display_name": "pi-port-probe",
                "status": "connected",
                "connected": True,
                "observed_nodes_count": 2,
                "identity": {
                    "local_id": "meshcorebasestation",
                    "display_name": "pi-port-probe",
                    "public_key": None,
                    "advert_loc_policy": 1,
                    "telemetry_mode_base": 2,
                    "telemetry_mode_loc": 2,
                    "telemetry_mode_env": 2,
                    "ble_pin": 123456,
                    "gps_enabled": 0,
                    "gps_interval_s": 0,
                    "client_repeat": 0,
                },
                "device_query": {
                    "model": "Raspberry Pi",
                    "version": "v1.16.0",
                    "firmware_build": "6 Jun 2026",
                    "max_contacts": 100,
                    "max_channels": 15,
                    "path_hash_mode": 1,
                },
                "runtime_status": {
                    "tx_power_dbm": 15,
                    "freq_mhz": 910.525,
                    "bw_khz": 62.5,
                    "sf": 7,
                    "cr": 5,
                    "interface_mode": "app",
                    "transport": "meshcore-runtime",
                    "runtime_endpoint": "tcp://127.0.0.1:5041",
                    "transport_ready": True,
                    "gateway_tx_allowed": True,
                    "browser_send_allowed": False,
                    "helper_tx_allowed": False,
                },
                "battery": {"battery_mv": 4167, "used_kb": 0, "total_kb": 0},
            }
        }
        device = {"device": {"battery": {"battery_mv": 4167, "used_kb": 0, "total_kb": 0}}}
        channels = {"channels": [{"index": 0, "name": "public", "visibility": "public", "is_empty": False}]}
        observed_nodes = {
            "observed_nodes": [
                {
                    "display_name": "N2dh",
                    "presence_state": "MESH_ACTIVE",
                    "public_key": "2b44ae59b2497b183176fd056e0c13c0d8c4b3131b0718c1bd0e9127a0845076",
                }
            ]
        }

        model = build_node_page_model(snapshot, device, channels, observed_nodes)

        self.assertEqual(model["identity"]["display_name"], "pi-port-probe")
        self.assertEqual(model["identity"]["model"], "Raspberry Pi")
        self.assertEqual(model["radio"]["tx_power_dbm"], 15)
        self.assertEqual(model["runtime"]["runtime_endpoint"], "tcp://127.0.0.1:5041")
        self.assertEqual(model["capabilities"]["ble_pin"], 123456)
        self.assertTrue(model["compose"]["send_allowed"])
        self.assertEqual(model["compose"]["target_count"], 1)
        self.assertEqual(model["channels"][0]["name"], "public")
        self.assertEqual(model["observed_nodes"][0]["display_name"], "N2dh")

    def test_render_node_page_html_surfaces_core_fields(self) -> None:
        model = {
            "identity": {
                "display_name": "pi-port-probe",
                "local_id": "meshcorebasestation",
                "status": "connected",
                "connected": True,
                "model": "Raspberry Pi",
                "firmware_version": "v1.16.0",
                "firmware_build": "6 Jun 2026",
                "public_key": None,
                "observed_nodes_count": 2,
            },
            "radio": {"tx_power_dbm": 15, "freq_mhz": 910.525, "bw_khz": 62.5, "sf": 7, "cr": 5},
            "runtime": {"interface_mode": "app", "transport": "meshcore-runtime", "runtime_endpoint": "tcp://127.0.0.1:5041", "transport_ready": True, "gateway_tx_allowed": False},
            "access": {"overall_state": "Connected, writes disabled", "runtime_state": "Ready", "gateway_tx_state": "Writes disabled", "browser_send_state": "Hidden", "helper_send_state": "Blocked"},
            "battery": {"battery_mv": 4167, "used_kb": 0, "total_kb": 0},
            "capabilities": {"ble_pin": 123456, "gps_enabled": False, "gps_interval_s": 0, "max_contacts": 100, "max_channels": 15},
            "compose": {"send_allowed": False, "target_count": 1, "default_target_name": "N2dh", "status_text": "Waiting for a reachable target or TX permission"},
            "channels": [{"index": 0, "name": "public", "visibility": "public", "is_empty": False}],
            "observed_nodes": [{"display_name": "N2dh", "presence_state": "MESH_ACTIVE"}],
        }

        html = render_node_page_html(model)

        self.assertIn("pi-port-probe", html)
        self.assertIn("Raspberry Pi", html)
        self.assertIn("15 dBm", html)
        self.assertIn("meshcore-runtime", html)
        self.assertIn("Connected, writes disabled", html)
        self.assertIn("Writes disabled", html)
        self.assertIn("Waiting for a reachable target or TX permission", html)
        self.assertIn("public", html)
        self.assertIn("N2dh", html)

    def test_build_directed_private_message_request_uses_default_target(self) -> None:
        model = {
            "compose": {
                "send_allowed": True,
                "default_target_public_key": "abc123",
            }
        }

        payload = build_directed_private_message_request(model, "hello")

        self.assertEqual(payload, {"public_key": "abc123", "text": "hello"})

    def test_build_directed_private_message_request_rejects_unavailable_send(self) -> None:
        model = {
            "compose": {
                "send_allowed": False,
            }
        }

        with self.assertRaises(ValueError):
            build_directed_private_message_request(model, "hello")


if __name__ == "__main__":
    unittest.main()