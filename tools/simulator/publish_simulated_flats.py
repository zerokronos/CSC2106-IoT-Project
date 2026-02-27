#!/usr/bin/env python3
"""Publish correlated flat telemetry to local MQTT for dashboard development."""

from __future__ import annotations

import math
import os
import random
import time
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

TOPIC_PREFIX = "csc2106/v0"
FLATS = ["flat01", "flat02", "flat03"]

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def publish_json(client: mqtt.Client, topic: str, payload: dict[str, Any]) -> None:
    import json

    client.publish(topic, json.dumps(payload, separators=(",", ":")), qos=0, retain=False)


def make_payload(
    node_id: str,
    msg_status: str,
    temp_c: float,
    smoke: float,
    severity: str = "none",
    reason: str = "",
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "ts": now_iso(),
        "mode": "wifi",
        "temp_c": round(temp_c, 2),
        "smoke": round(smoke, 3),
        "status": msg_status,
        "severity": severity,
        "reason": reason,
        "values": {"temp_c": round(temp_c, 2), "smoke": round(smoke, 3)},
        "meta": {"source": "simulator", "model": "correlated_flats_v1"},
    }


def run() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD or None)

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    print(f"Simulator connected to mqtt://{MQTT_HOST}:{MQTT_PORT}")

    rng = random.Random(2106)
    tick = 0
    anomaly_triggered = False
    last_heartbeat = 0.0

    base_temp = 27.2
    flat_offsets = {"flat01": -0.2, "flat02": 0.1, "flat03": 0.0}
    anomaly_slope = 0.0

    try:
        while True:
            tick += 1
            t_now = time.time()

            seasonal = math.sin(tick / 16.0) * 0.08
            drift = rng.uniform(-0.02, 0.02)
            base_temp += seasonal + drift

            smoke_base = max(0.01, 0.02 + rng.uniform(-0.005, 0.005))

            if tick >= 45:
                anomaly_slope += 0.07

            for node_id in FLATS:
                local_noise = rng.uniform(-0.12, 0.12)
                temp_c = base_temp + flat_offsets[node_id] + local_noise

                if node_id == "flat02" and tick >= 45:
                    temp_c += anomaly_slope

                smoke = smoke_base + rng.uniform(-0.004, 0.004)
                if node_id == "flat02" and tick >= 45:
                    smoke += min(0.08, anomaly_slope * 0.02)

                status = "ok"
                severity = "none"
                reason = ""

                if node_id == "flat02" and tick >= 45 and anomaly_slope > 0.9:
                    status = "warn"
                    severity = "warn"
                    reason = "temp_above_neighbors_and_rising"

                    if not anomaly_triggered:
                        alert_payload = make_payload(
                            node_id=node_id,
                            msg_status="warn",
                            temp_c=temp_c,
                            smoke=smoke,
                            severity="warn",
                            reason=reason,
                        )
                        publish_json(client, f"{TOPIC_PREFIX}/alert/{node_id}", alert_payload)
                        anomaly_triggered = True
                        print(f"alert published for {node_id}: {reason}")

                telemetry_payload = make_payload(
                    node_id=node_id,
                    msg_status=status,
                    temp_c=temp_c,
                    smoke=smoke,
                    severity=severity,
                    reason=reason,
                )
                publish_json(client, f"{TOPIC_PREFIX}/telemetry/{node_id}", telemetry_payload)

            if t_now - last_heartbeat >= 30:
                last_heartbeat = t_now
                for node_id in FLATS:
                    hb_payload = make_payload(
                        node_id=node_id,
                        msg_status="ok",
                        temp_c=base_temp + flat_offsets[node_id],
                        smoke=smoke_base,
                        severity="none",
                        reason="heartbeat",
                    )
                    publish_json(client, f"{TOPIC_PREFIX}/heartbeat/{node_id}", hb_payload)

            time.sleep(2)
    except KeyboardInterrupt:
        print("Simulator stopped")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run()
