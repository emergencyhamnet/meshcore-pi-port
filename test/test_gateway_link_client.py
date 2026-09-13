from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from gateway_link_client import (  # noqa: E402
    PROTOCOL_VERSION,
    GatewayLinkEnvelope,
    GatewayLinkProtocolError,
    decode_gateway_link_frame,
    encode_gateway_link_frame,
)


class GatewayLinkClientTests(unittest.TestCase):
    def test_encode_gateway_link_frame_prefixes_big_endian_length(self) -> None:
        frame = encode_gateway_link_frame(
            GatewayLinkEnvelope(
                version=PROTOCOL_VERSION,
                type="request",
                id="abc",
                method="get_snapshot",
                params={},
            )
        )

        self.assertEqual(int.from_bytes(frame[:4], byteorder="big"), len(frame) - 4)

    def test_decode_gateway_link_frame_round_trips_envelope(self) -> None:
        original = GatewayLinkEnvelope(
            version=PROTOCOL_VERSION,
            type="response",
            id="abc",
            ok=True,
            result={"snapshot": {"connected": True}},
        )

        decoded = decode_gateway_link_frame(encode_gateway_link_frame(original))

        self.assertEqual(decoded.version, PROTOCOL_VERSION)
        self.assertEqual(decoded.type, "response")
        self.assertEqual(decoded.id, "abc")
        self.assertTrue(decoded.ok)
        self.assertEqual(decoded.result, {"snapshot": {"connected": True}})

    def test_decode_gateway_link_frame_rejects_truncated_payload(self) -> None:
        with self.assertRaises(GatewayLinkProtocolError):
            decode_gateway_link_frame(b"\x00\x00\x00\x05{}")


if __name__ == "__main__":
    unittest.main()