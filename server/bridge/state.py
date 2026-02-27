"""In-memory dashboard projection from MQTT events."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any


class StateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nodes: dict[str, dict[str, Any]] = {}
        self._alerts: deque[dict[str, Any]] = deque(maxlen=50)

    def apply_message(self, topic: str, payload: dict[str, Any]) -> None:
        node_id = payload.get("node_id") or topic.rsplit("/", 1)[-1]
        status = payload.get("status") or "unknown"
        is_alert = "/alert/" in topic
        is_telemetry = "/telemetry/" in topic or "/heartbeat/" in topic
        mode = payload.get("mode")

        with self._lock:
            node = self._nodes.get(node_id, {
                "node_id": node_id,
                "mode": "",
                "last_telemetry_mode": "",
                "last_alert_mode": "",
                "status": status,
                "last_seen": payload.get("ts", ""),
                "temp_c": payload.get("temp_c"),
                "smoke": payload.get("smoke"),
                "current_alert": "",
            })

            if is_telemetry and mode:
                node["last_telemetry_mode"] = mode
                node["mode"] = mode
            elif is_alert and mode:
                node["last_alert_mode"] = mode
                if not node.get("mode"):
                    node["mode"] = mode

            node["status"] = status
            node["last_seen"] = payload.get("ts", node.get("last_seen", ""))
            node["temp_c"] = payload.get("temp_c", node.get("temp_c"))
            node["smoke"] = payload.get("smoke", node.get("smoke"))

            if is_alert:
                reason = payload.get("reason") or payload.get("severity") or "alert"
                node["current_alert"] = str(reason)

                alert_entry = {
                    "node_id": node_id,
                    "ts": payload.get("ts", ""),
                    "severity": payload.get("severity", "none"),
                    "reason": payload.get("reason", ""),
                    "temp_c": payload.get("temp_c"),
                    "smoke": payload.get("smoke"),
                }
                self._alerts.appendleft(alert_entry)

            self._nodes[node_id] = node

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            nodes = [self._nodes[key] for key in sorted(self._nodes.keys())]
            alerts = list(self._alerts)
        return {"nodes": nodes, "alerts": alerts}
