from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ui-native" / "src"))

from meshcore_ui_native.gateway_link_server import GatewayLinkConfig, GatewayLinkEnvelope, GatewayLinkService, GatewayLinkServer  # noqa: E402


class FakeBroker:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.snapshot = {
            "self_info": {
                "name": "pi-port-probe",
                "public_key": "11" * 32,
                "adv_lat": 40.774777,
                "adv_lon": -74.17829,
                "tx_power": 17,
                "max_tx_power": 20,
                "telemetry_mode_base": 2,
                "telemetry_mode_loc": 2,
                "telemetry_mode_env": 0,
                "advert_loc_policy": 1,
                "radio_freq_mhz": 915.5,
                "radio_bw_khz": 250.0,
                "radio_sf": 9,
                "radio_cr": 5,
            },
            "device_info": {
                "model": "Raspberry Pi",
                "firmware_build": "6 Jun 2026",
                "version": "v1.16.0",
                "ble_pin": 123456,
                "client_repeat": 2,
                "path_hash_mode": 1,
                "max_contacts": 100,
                "max_channels": 4,
            },
            "battery": {"battery_mv": 4167, "used_kb": 0, "total_kb": 0},
            "custom_vars": {"gps": "1", "gps_interval": "300"},
            "contacts": [
                {
                    "public_key": "22" * 32,
                    "name": "N2dh",
                    "gps_lat": 40.7748,
                    "gps_lon": -74.1782,
                    "out_path_len": 1,
                    "lastmod": 1725400000,
                    "last_advert_timestamp": 1725399900,
                }
            ],
            "channels": [
                {"index": 0, "name": "public", "secret_hex": "00" * 16},
                {"index": 1, "name": "private-test", "secret_hex": "ab" * 16},
                None,
                None,
            ],
        }
        self.activity = [
            {
                "direction": "incoming",
                "transport": "meshcore",
                "network": "meshcore",
                "event_type": "channel_message_rx",
                "event_ts_utc": "2026-09-03T00:00:00+00:00",
                "summary": "hello",
                "payload": {
                    "text": "hello",
                    "channel_index": 1,
                    "message_scope": "channel",
                    "event_utc": "2026-09-03T00:00:00+00:00",
                    "raw": {"channel_index": 1, "message_scope": "channel"},
                },
            }
        ]

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1

    def collect_session_snapshot(self) -> dict:
        return dict(self.snapshot)

    def list_activity(self, *, limit: int = 50, direction: str | None = None) -> list[dict]:
        rows = list(self.activity)
        if direction:
            rows = [row for row in rows if row["direction"] == direction]
        return rows[:limit]

    def tools_summary(self) -> dict:
        return {
            "ok": True,
            "core": {"battery_mv": 4167},
            "radio": {"last_rssi": -60},
            "packets": {"packets_recv": 10},
        }

    def send_contact_message(self, public_key: str, body: dict[str, str]) -> dict:
        return {"ok": True, "public_key": public_key, "text": body["text"]}

    def send_channel_message(self, channel_index: int, body: dict[str, str]) -> dict:
        return {"ok": True, "channel_index": channel_index, "text": body["text"]}

    def set_tx_power(self, tx_power_dbm: int) -> dict:
        return {"ok": True, "tx_power_dbm": tx_power_dbm}


class GatewayLinkServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GatewayLinkConfig(
            host="0.0.0.0",
            port=7463,
            native_host="127.0.0.1",
            native_port=5040,
            app_name="meshcore-gateway-link",
            protocol_version=3,
            timeout_seconds=5.0,
            allow_basestation_tx=True,
            service_name="meshcore-pi-live-runtime.service",
        )
        self.broker = FakeBroker()
        self.service = GatewayLinkService(self.config, self.broker)

    def test_get_snapshot_uses_native_broker_data(self) -> None:
        snapshot = self.service.get_snapshot()

        self.assertTrue(snapshot["connected"])
        self.assertEqual(snapshot["identity"]["public_key"], "11" * 32)
        self.assertEqual(snapshot["runtime_status"]["runtime_endpoint"], "tcp://127.0.0.1:5040")
        self.assertEqual(snapshot["device_query"]["max_channels"], 4)

    def test_list_channels_includes_empty_slots(self) -> None:
        channels = self.service.list_channels()

        self.assertEqual(len(channels), 4)
        self.assertEqual(channels[1]["name"], "private-test")
        self.assertTrue(channels[2]["is_empty"])

    def test_dispatch_get_snapshot_returns_response_envelope(self) -> None:
        response = self.service.dispatch(
            GatewayLinkEnvelope(
                version="ehn-gateway-link/1",
                type="request",
                id="abc",
                method="get_snapshot",
                params={},
            )
        )

        self.assertEqual(response.type, "response")
        self.assertTrue(response.ok)
        assert response.result is not None
        self.assertTrue(response.result["snapshot"]["connected"])

    def test_send_channel_message_records_outbound_request(self) -> None:
        result = self.service.send_channel_message({"channel_index": 1, "text": "ping", "delivery_id": "req-1"})
        requests = self.service.list_gateway_outbound_status(limit=10, state=None)

        self.assertTrue(result["accepted"])
        self.assertEqual(requests[0]["request_id"], "req-1")
        self.assertEqual(requests[0]["destination"]["channel_index"], 1)
        self.assertEqual(requests[0]["state"], "accepted")

    def test_server_with_injected_broker_does_not_own_broker_lifecycle(self) -> None:
        config = GatewayLinkConfig(
            host="127.0.0.1",
            port=0,
            native_host="127.0.0.1",
            native_port=5040,
            app_name="meshcore-gateway-link",
            protocol_version=3,
            timeout_seconds=5.0,
            allow_basestation_tx=False,
            service_name="meshcore-pi-live-runtime.service",
        )
        server = GatewayLinkServer(config, broker=self.broker)

        started = server.start(raise_on_bind_error=True)
        server.stop()

        self.assertTrue(started)
        self.assertEqual(self.broker.started, 0)
        self.assertEqual(self.broker.stopped, 0)


if __name__ == "__main__":
    unittest.main()