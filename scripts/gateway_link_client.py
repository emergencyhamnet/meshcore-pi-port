from __future__ import annotations

from dataclasses import dataclass
import json
import socket
from typing import Any
from uuid import uuid4


PROTOCOL_VERSION = "ehn-gateway-link/1"


class GatewayLinkProtocolError(RuntimeError):
    pass


class GatewayLinkRequestError(GatewayLinkProtocolError):
    def __init__(self, message: str, *, response: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.response = response or {}


@dataclass(frozen=True, slots=True)
class GatewayLinkEnvelope:
    version: str
    type: str
    id: str | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    ok: bool | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "version": self.version,
            "type": self.type,
        }
        if self.id is not None:
            payload["id"] = self.id
        if self.method is not None:
            payload["method"] = self.method
        if self.params is not None:
            payload["params"] = self.params
        if self.ok is not None:
            payload["ok"] = self.ok
        if self.result is not None:
            payload["result"] = self.result
        if self.error is not None:
            payload["error"] = self.error
        return payload

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GatewayLinkEnvelope:
        if not isinstance(payload, dict):
            raise GatewayLinkProtocolError("gateway-link payload must be a JSON object")
        params = payload.get("params")
        result = payload.get("result")
        error = payload.get("error")
        return cls(
            version=str(payload.get("version") or "").strip(),
            type=str(payload.get("type") or "").strip(),
            id=str(payload.get("id") or "").strip() or None,
            method=str(payload.get("method") or "").strip() or None,
            params=params if isinstance(params, dict) else None,
            ok=payload.get("ok") if isinstance(payload.get("ok"), bool) else None,
            result=result if isinstance(result, dict) else None,
            error=error if isinstance(error, dict) else None,
        )


def encode_gateway_link_frame(envelope: GatewayLinkEnvelope) -> bytes:
    payload = envelope.to_json_bytes()
    return len(payload).to_bytes(4, byteorder="big", signed=False) + payload


def decode_gateway_link_frame(frame: bytes) -> GatewayLinkEnvelope:
    if len(frame) < 4:
        raise GatewayLinkProtocolError("gateway-link frame is too short")
    payload_length = int.from_bytes(frame[:4], byteorder="big", signed=False)
    payload = frame[4:]
    if len(payload) != payload_length:
        raise GatewayLinkProtocolError("gateway-link frame length does not match payload size")
    data = json.loads(payload.decode("utf-8"))
    return GatewayLinkEnvelope.from_dict(data)


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = int(size)
    while remaining > 0:
        chunk = connection.recv(remaining)
        if not chunk:
            raise GatewayLinkProtocolError("gateway-link connection closed before frame completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_gateway_link_frame(connection: socket.socket) -> GatewayLinkEnvelope:
    header = _recv_exact(connection, 4)
    payload_length = int.from_bytes(header, byteorder="big", signed=False)
    payload = _recv_exact(connection, payload_length)
    return decode_gateway_link_frame(header + payload)


class MeshCoreGatewayLinkClient:
    def __init__(self, host: str, port: int = 7463, *, timeout_seconds: float = 5.0) -> None:
        self._host = str(host).strip()
        self._port = int(port)
        self._timeout_seconds = float(timeout_seconds)
        self._connection: socket.socket | None = None

    def __enter__(self) -> MeshCoreGatewayLinkClient:
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

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = str(uuid4())
        envelope = GatewayLinkEnvelope(
            version=PROTOCOL_VERSION,
            type="request",
            id=request_id,
            method=str(method).strip(),
            params=dict(params or {}),
        )
        if self._connection is None:
            self.connect()
        assert self._connection is not None

        response: GatewayLinkEnvelope
        try:
            self._connection.sendall(encode_gateway_link_frame(envelope))
            response = recv_gateway_link_frame(self._connection)
        finally:
            # The current Pi gateway-link server serves one request per connection.
            self.close()

        if response.type != "response":
            raise GatewayLinkProtocolError(f"unexpected gateway-link envelope type {response.type!r}")
        if response.version != PROTOCOL_VERSION:
            raise GatewayLinkProtocolError(f"unexpected gateway-link version {response.version!r}")
        if response.id != request_id:
            raise GatewayLinkProtocolError("gateway-link response id does not match request id")
        if not response.ok:
            message = "gateway-link request failed"
            if response.error and response.error.get("message"):
                message = str(response.error["message"])
            raise GatewayLinkRequestError(message, response=response.to_dict())
        return dict(response.result or {})

    def get_snapshot(self) -> dict[str, Any]:
        return self.request("get_snapshot")

    def list_channels(self) -> dict[str, Any]:
        return self.request("list_channels")

    def list_observed_nodes(self) -> dict[str, Any]:
        return self.request("list_observed_nodes")

    def list_gateway_inbound_events(self, *, limit: int = 50) -> dict[str, Any]:
        return self.request("list_gateway_inbound_events", {"limit": int(limit)})

    def list_gateway_outbound_status(self, *, limit: int = 50, state: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": int(limit)}
        if state:
            params["state"] = str(state)
        return self.request("list_gateway_outbound_status", params)

    def get_device_details(self) -> dict[str, Any]:
        return self.request("get_device_details")

    def send_directed_private_message(self, *, public_key: str, text: str) -> dict[str, Any]:
        return self.request(
            "send_directed_private_message",
            {
                "public_key": str(public_key),
                "text": str(text),
            },
        )
