#!/usr/bin/env python3
"""Integration smoke test: POST TTN uplink, verify MQTT publish."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

import paho.mqtt.client as mqtt


def post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", default="http://127.0.0.1:8000")
    parser.add_argument("--mqtt-host", default=os.getenv("MQTT_HOST", "localhost"))
    parser.add_argument("--mqtt-port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    node_id = "node007"
    topic = f"csc2106/v0/telemetry/{node_id}"

    got_event = threading.Event()
    seen_payload = {}

    def on_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        nonlocal seen_payload
        if msg.topic != topic:
            return
        seen_payload = json.loads(msg.payload.decode("utf-8"))
        got_event.set()

    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    sub.on_message = on_message
    sub.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
    sub.subscribe(topic, qos=0)
    sub.loop_start()

    raw = bytes([7, 1, 0x01, 0x2C, 0x00, 0x03, 0x00])
    frm_payload = base64.b64encode(raw).decode("ascii")

    body = {
        "end_device_ids": {"device_id": "smoke-node"},
        "received_at": "2026-02-27T12:00:00Z",
        "uplink_message": {
            "frm_payload": frm_payload,
        },
    }

    try:
        response = post_json(f"{args.http}/ttn/uplink", body)
    except urllib.error.URLError as exc:
        print(f"FAIL: cannot POST to bridge: {exc}")
        sub.loop_stop()
        sub.disconnect()
        return 1

    ok = got_event.wait(timeout=args.timeout)
    sub.loop_stop()
    sub.disconnect()

    if not ok:
        print("FAIL: did not receive MQTT message in time")
        return 1

    if seen_payload.get("node_id") != node_id:
        print(f"FAIL: unexpected node_id in MQTT payload: {seen_payload}")
        return 1

    print("PASS: bridge published TTN uplink to MQTT")
    print(json.dumps({"http_response": response, "mqtt_payload": seen_payload}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
