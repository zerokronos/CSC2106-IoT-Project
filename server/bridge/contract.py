"""MQTT contract and topic mapping helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

TOPIC_PREFIX = "csc2106/v0"
TOPIC_TELEMETRY = TOPIC_PREFIX + "/telemetry/{node_id}"
TOPIC_HEARTBEAT = TOPIC_PREFIX + "/heartbeat/{node_id}"
TOPIC_ALERT = TOPIC_PREFIX + "/alert/{node_id}"
TOPIC_SYSTEM_LOGS = TOPIC_PREFIX + "/logs/system"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_node_id(value: Any) -> str:
    if value is None:
        raise ValueError("node_id is required")

    if isinstance(value, int):
        if value <= 0:
            raise ValueError("node_id integer must be > 0")
        return f"node{value:03d}"

    text = str(value).strip()
    if not text:
        raise ValueError("node_id is empty")

    if text.isdigit():
        return f"node{int(text):03d}"

    return text


def message_route(msg_type: Any) -> str:
    table = {
        1: "telemetry",
        2: "heartbeat",
        3: "alert",
        "1": "telemetry",
        "2": "heartbeat",
        "3": "alert",
        "telemetry": "telemetry",
        "heartbeat": "heartbeat",
        "alert": "alert",
    }
    route = table.get(msg_type)
    if route is None:
        raise ValueError(f"unsupported msg_type: {msg_type}")
    return route


def topic_for(node_id: str, msg_type: Any) -> str:
    route = message_route(msg_type)
    safe_node = normalize_node_id(node_id)

    if route == "telemetry":
        return TOPIC_TELEMETRY.format(node_id=safe_node)
    if route == "heartbeat":
        return TOPIC_HEARTBEAT.format(node_id=safe_node)
    return TOPIC_ALERT.format(node_id=safe_node)


def severity_name(value: Any) -> str:
    table = {
        None: "none",
        "": "none",
        0: "none",
        1: "warn",
        2: "alarm",
        "0": "none",
        "1": "warn",
        "2": "alarm",
        "none": "none",
        "warn": "warn",
        "alarm": "alarm",
    }
    mapped = table.get(value)
    if mapped is not None:
        return mapped
    return str(value)


def make_contract_payload(
    *,
    node_id: Any,
    mode: str,
    ts: str | None,
    temp_c: Any = None,
    smoke: Any = None,
    status: str = "ok",
    severity: Any = None,
    reason: str = "",
    values: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "node_id": normalize_node_id(node_id),
        "ts": ts or iso_now(),
        "mode": mode,
        "temp_c": temp_c,
        "smoke": smoke,
        "status": status,
        "severity": severity_name(severity),
        "reason": reason or "",
        "values": values or {},
        "meta": meta or {},
    }
    return payload
