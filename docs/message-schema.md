# Message Schema

This document tracks payload schemas used for LoRa transport and MQTT transport.

## Common Fields

Required fields for both LoRa and MQTT messages:

| Field | Type | Required | Description |
|---|---|---|---|
| `node_id` | string | Yes | Unique node identifier (e.g., `node-01`). |
| `msg_type` | string | Yes | Message category (`telemetry`, `alert`, `ack`, `cmd_resp`, etc.). |
| `ts` | string | Yes | Event timestamp in ISO-8601 UTC format. |
| `hop_count` | integer | Yes | Number of hops/retransmissions observed in mesh path. |
| `msg_id` | string | Yes | Unique message ID for deduplication and tracing. |
| `payload` | object | Yes | Message-specific data block. |
| `signature` | string | Yes | Integrity/authentication signature (format TBD). |

## LoRa Payload Placeholder

```json
{
  "node_id": "node-01",
  "msg_type": "telemetry",
  "ts": "2026-02-18T00:00:00Z",
  "hop_count": 0,
  "msg_id": "<uuid-or-seq>",
  "payload": {
    "<sensor_key>": "<value>"
  },
  "signature": "<signature>"
}
```

## MQTT Payload Placeholder

```json
{
  "node_id": "node-01",
  "msg_type": "telemetry",
  "ts": "2026-02-18T00:00:00Z",
  "hop_count": 0,
  "msg_id": "<uuid-or-seq>",
  "payload": {
    "<sensor_key>": "<value>"
  },
  "signature": "<signature>"
}
```

## Validation Checklist (Placeholder)

- Field presence and type checks
- Timestamp format and clock skew handling
- `msg_id` uniqueness window
- Signature verification flow
