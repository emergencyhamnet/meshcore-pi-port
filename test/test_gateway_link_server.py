from __future__ import annotations

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ui-native" / "src"))

from meshcore_ui_native.gateway_link_server import GatewayLinkConfig, GatewayLinkEnvelope, GatewayLinkService, GatewayLinkServer  # noqa: E402
from meshcore_ui_native.native_session_broker import NativeSessionBroker  # noqa: E402
from meshcore_ui_native.companion_client import PACKET_ADVERTISEMENT, ChannelInfo, MeshCoreNativeTcpClient, SendResult  # noqa: E402


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

    def discover_contacts(self, body: dict) -> dict:
        return {"ok": True, "flood": body["flood"], "sent_at": 1725400000}


class NativeBrokerSendTests(unittest.TestCase):
    def test_advert_refreshes_cached_contacts_on_next_snapshot(self) -> None:
        key = "9b4994708df9" + "ab" * 26
        reads = []

        def collect_session_snapshot(**kwargs):
            reads.append(kwargs["include_contacts"])
            return {
                "self_info": {}, "device_info": {"max_channels": 1},
                "channels": [None], "battery": {}, "custom_vars": {},
                "contacts": [] if len(reads) == 1 else [{"public_key": key, "name": "TBEAM"}],
            }

        client = SimpleNamespace(
            collect_session_snapshot=collect_session_snapshot,
            pop_notifications=lambda: [],
        )
        broker = NativeSessionBroker({"app_name": "test", "protocol_version": 3}, {}, {})
        broker._client = client
        broker._collect_snapshot_locked(client)
        broker._handle_async_frame_locked(bytes([PACKET_ADVERTISEMENT]))
        snapshot = broker._collect_snapshot_locked(client)

        self.assertEqual(reads, [True, True])
        self.assertEqual(snapshot["contacts"][0]["public_key"], key)
        self.assertEqual(broker._contact_keys_by_prefix[key[:12]], key)
        self.assertEqual(broker._contact_history, {})

    def test_direct_send_checks_contacts_without_collecting_full_node_snapshot(self) -> None:
        key = "22" * 32
        client = SimpleNamespace(
            get_contacts=lambda: [SimpleNamespace(public_key=key)],
            send_direct_text_message=lambda **kwargs: SendResult(packet_type=6, was_flood=False, expected_ack=None, suggested_timeout_ms=None),
            drain_messages=Mock(return_value=[]),
            pop_notifications=lambda: [],
        )
        broker = NativeSessionBroker({}, {}, {})
        broker._client = client
        with patch.object(broker, "_collect_node_page_locked", side_effect=AssertionError("full snapshot before send")):
            result = broker.send_contact_message(key, {"text": "test"})
        self.assertTrue(result["ok"])
        client.drain_messages.assert_not_called()
        with self.assertRaisesRegex(ValueError, "contact is not configured"):
            broker.send_contact_message("33" * 32, {"text": "test"})

    def test_routine_snapshot_reads_cached_active_channel_slots_only(self) -> None:
        requested_indices: list[list[int] | None] = []
        contact_reads: list[bool] = []
        snapshot = {
            "self_info": {},
            "device_info": {"max_channels": 8},
            "contacts": [],
            "channels": [None] * 8,
            "battery": {},
            "custom_vars": {},
        }

        def collect_session_snapshot(**kwargs):
            requested_indices.append(kwargs.get("channel_indices"))
            contact_reads.append(kwargs.get("include_contacts", True))
            if kwargs.get("channel_indices") is None:
                snapshot["channels"][0] = {"index": 0, "name": "public", "secret_hex": "00" * 16}
                snapshot["channels"][3] = {"index": 3, "name": "private", "secret_hex": "ab" * 16}
            else:
                snapshot["channels"] = [None] * 8
                snapshot["channels"][0] = {"index": 0, "name": "public", "secret_hex": "00" * 16}
                snapshot["channels"][3] = {"index": 3, "name": "private", "secret_hex": "ab" * 16}
            return snapshot

        client = SimpleNamespace(
            collect_session_snapshot=collect_session_snapshot,
            pop_notifications=lambda: [],
        )
        broker = NativeSessionBroker({"app_name": "test", "protocol_version": 3}, {}, {})
        broker._client = client

        broker._collect_snapshot_locked(client)
        routine_snapshot = broker._collect_snapshot_locked(client)

        self.assertEqual(requested_indices, [None, [0, 3]])
        self.assertEqual(contact_reads, [True, False])
        self.assertEqual(routine_snapshot["channels"][0]["name"], "public")
        self.assertEqual(routine_snapshot["channels"][3]["name"], "private")
        self.assertIsNone(routine_snapshot["channels"][2])

        broker._collect_snapshot_locked(client, refresh_channels=True)
        self.assertEqual(requested_indices, [None, [0, 3], None])
        self.assertEqual(contact_reads, [True, False, True])


class NativeCompanionChannelReadTests(unittest.TestCase):
    def test_selected_channel_reads_preserve_slot_positions(self) -> None:
        client = MeshCoreNativeTcpClient("127.0.0.1", 5040)
        read_indices: list[int] = []

        def get_channel(index: int) -> ChannelInfo:
            read_indices.append(index)
            return ChannelInfo(index=index, name=f"channel-{index}", secret_hex="ab" * 16)

        client.get_channel = get_channel
        channels = client.get_channels(8, indices=[0, 3])

        self.assertEqual(read_indices, [0, 3])
        self.assertEqual(len(channels), 8)
        self.assertEqual(channels[0].name, "channel-0")
        self.assertEqual(channels[3].name, "channel-3")
        self.assertIsNone(channels[2])


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
        self.assertTrue(snapshot["runtime_status"]["zero_hop_advert_supported"])
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

    def test_dispatch_zero_hop_advert_never_requests_flood(self) -> None:
        with patch.object(self.broker, "discover_contacts", wraps=self.broker.discover_contacts) as send:
            response = self.service.dispatch(GatewayLinkEnvelope(
                version="ehn-gateway-link/1", type="request", id="advert-1",
                method="send_zero_hop_advert", params={"flood": True},
            ))
        self.assertTrue(response.ok)
        self.assertTrue(response.result["accepted"])
        self.assertFalse(response.result["payload"]["flood"])
        self.assertIn("reception is not confirmed", response.result["message"])
        send.assert_called_once_with({"flood": False})

    def test_zero_hop_advert_respects_transmit_gate(self) -> None:
        self.service.set_allow_basestation_tx(False)
        with patch.object(self.broker, "discover_contacts") as send:
            response = self.service.dispatch(GatewayLinkEnvelope(
                version="ehn-gateway-link/1", type="request", method="send_zero_hop_advert",
            ))
        self.assertFalse(response.ok)
        send.assert_not_called()

    def test_zero_hop_advert_rejection_is_not_reported_as_accepted(self) -> None:
        with patch.object(self.broker, "discover_contacts", return_value={"ok": False}) as send:
            result = self.service.send_zero_hop_advert()
        self.assertFalse(result["accepted"])
        send.assert_called_once_with({"flood": False})

    def test_zero_hop_advert_timeout_is_not_retried(self) -> None:
        with patch.object(self.broker, "discover_contacts", side_effect=TimeoutError("uncertain")) as send:
            response = self.service.dispatch(GatewayLinkEnvelope(
                version="ehn-gateway-link/1", type="request", method="send_zero_hop_advert",
            ))
        self.assertFalse(response.ok)
        self.assertEqual(response.error["message"], "uncertain")
        send.assert_called_once_with({"flood": False})

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