"""MQTT publisher/subscriber wrapper for the bridge."""

from __future__ import annotations

import json
from typing import Any, Callable

import paho.mqtt.client as mqtt

from config import settings


class MQTTService:
    def __init__(self, on_message: Callable[[str, dict[str, Any]], None]) -> None:
        self._on_message = on_message
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password or None)

        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message

    @property
    def client(self) -> mqtt.Client:
        return self._client

    def start(self) -> None:
        self._client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        try:
            self._client.loop_stop()
        finally:
            self._client.disconnect()

    def publish_json(self, topic: str, payload: dict[str, Any], retain: bool = False) -> None:
        self._client.publish(topic, json.dumps(payload, separators=(",", ":")), qos=0, retain=retain)

    def _handle_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.value != 0:
            return

        client.subscribe("csc2106/v0/telemetry/+", qos=0)
        client.subscribe("csc2106/v0/heartbeat/+", qos=0)
        client.subscribe("csc2106/v0/alert/+", qos=0)
        client.subscribe("csc2106/v0/logs/system", qos=0)

    def _handle_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        topic = message.topic
        raw_payload = message.payload.decode("utf-8", errors="replace")

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            payload = {
                "node_id": "system",
                "ts": "",
                "mode": "",
                "temp_c": None,
                "smoke": None,
                "status": "error",
                "severity": "warn",
                "reason": "invalid_json_payload",
                "values": {"raw": raw_payload},
                "meta": {"source": "mqtt_service"},
            }

        self._on_message(topic, payload)
