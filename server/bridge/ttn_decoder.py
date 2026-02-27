"""TTN webhook payload parsing and binary decode."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from contract import iso_now


@dataclass
class DecodedInput:
    node_id: Any
    msg_type: Any
    ts: str
    temp_c: float | None
    smoke: float | None
    severity: Any
    reason: str
    meta: dict[str, Any]


class TTNDecodeError(ValueError):
    """Raised when incoming TTN webhook JSON cannot be parsed."""


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def decode_binary_payload(frm_payload_b64: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(frm_payload_b64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise TTNDecodeError("frm_payload is not valid base64") from exc

    if len(raw) < 7:
        raise TTNDecodeError("binary payload must be at least 7 bytes")

    node_id = raw[0]
    msg_type = raw[1]
    temp_x10 = int.from_bytes(raw[2:4], byteorder="big", signed=False)
    smoke_x100 = int.from_bytes(raw[4:6], byteorder="big", signed=False)
    severity = raw[6]

    return {
        "node_id": node_id,
        "msg_type": msg_type,
        "temp_c": round(temp_x10 / 10.0, 2),
        "smoke": round(smoke_x100 / 100.0, 3),
        "severity": severity,
    }


def parse_uplink(payload: dict[str, Any]) -> DecodedInput:
    if not isinstance(payload, dict):
        raise TTNDecodeError("request body must be a JSON object")

    if "node_id" in payload and "msg_type" in payload:
        return DecodedInput(
            node_id=payload.get("node_id"),
            msg_type=payload.get("msg_type"),
            ts=payload.get("ts") or payload.get("received_at") or iso_now(),
            temp_c=_as_float(payload.get("temp_c")),
            smoke=_as_float(payload.get("smoke")),
            severity=payload.get("severity"),
            reason=str(payload.get("reason", "")),
            meta={"source": "dev_json"},
        )

    end_device_ids = payload.get("end_device_ids", {})
    uplink_message = payload.get("uplink_message", {})

    device_id = end_device_ids.get("device_id") or end_device_ids.get("dev_eui")
    ts = payload.get("received_at") or uplink_message.get("received_at") or iso_now()

    decoded_payload = uplink_message.get("decoded_payload")
    if isinstance(decoded_payload, dict):
        msg_type = decoded_payload.get("msg_type", 1)
        severity = decoded_payload.get("severity")
        reason = str(decoded_payload.get("reason", ""))

        temp_c = _as_float(decoded_payload.get("temp_c"))
        if temp_c is None and decoded_payload.get("temp_x10") is not None:
            temp_c = _as_float(decoded_payload.get("temp_x10"), 0.0)
            temp_c = round(temp_c / 10.0, 2) if temp_c is not None else None

        smoke = _as_float(decoded_payload.get("smoke"))
        if smoke is None and decoded_payload.get("smoke_x100") is not None:
            smoke = _as_float(decoded_payload.get("smoke_x100"), 0.0)
            smoke = round(smoke / 100.0, 3) if smoke is not None else None

        node_id = decoded_payload.get("node_id") or device_id
        if node_id is None:
            raise TTNDecodeError("node_id missing in decoded_payload and end_device_ids")

        return DecodedInput(
            node_id=node_id,
            msg_type=msg_type,
            ts=ts,
            temp_c=temp_c,
            smoke=smoke,
            severity=severity,
            reason=reason,
            meta={"source": "ttn_decoded", "device_id": device_id or ""},
        )

    frm_payload = uplink_message.get("frm_payload")
    if frm_payload:
        decoded_binary = decode_binary_payload(frm_payload)
        return DecodedInput(
            node_id=decoded_binary["node_id"],
            msg_type=decoded_binary["msg_type"],
            ts=ts,
            temp_c=decoded_binary["temp_c"],
            smoke=decoded_binary["smoke"],
            severity=decoded_binary["severity"],
            reason="",
            meta={"source": "ttn_frm_payload", "device_id": device_id or ""},
        )

    raise TTNDecodeError("unsupported uplink payload: expected dev JSON, decoded_payload, or frm_payload")
