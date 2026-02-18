# Topic Map

This document defines MQTT topic naming conventions and the canonical topic list used by this project.

## Naming Convention

Use lowercase, slash-separated segments with stable ordering:

`<project>/<site>/<layer>/<node_id>/<msg_type>`

Guidelines:
- Use lowercase alphanumeric and underscores only.
- Keep `node_id` stable across reboots.
- Keep `msg_type` concise (`telemetry`, `alert`, `ack`, etc.).
- Avoid wildcard subscriptions in production unless explicitly required.

## Suggested Base Prefix

`iot/csc2106`

## Topic List (Placeholders)

| Purpose | Topic Pattern | Publisher | Subscriber(s) | QoS | Retained |
|---|---|---|---|---|---|
| Node telemetry uplink | `iot/csc2106/<site>/node/<node_id>/telemetry` | Node/Gateway | Dashboard/Backend | 1 | No |
| Node status heartbeat | `iot/csc2106/<site>/node/<node_id>/status` | Node/Gateway | Dashboard/Backend | 1 | Yes |
| Gateway health | `iot/csc2106/<site>/gateway/<gw_id>/health` | Gateway | Dashboard/Backend | 1 | Yes |
| Command downlink | `iot/csc2106/<site>/node/<node_id>/cmd` | Dashboard/Backend | Gateway/Node | 1 | No |
| Acknowledgement | `iot/csc2106/<site>/node/<node_id>/ack` | Node/Gateway | Dashboard/Backend | 1 | No |
| Alerts/events | `iot/csc2106/<site>/events/<event_type>` | Node/Gateway | Dashboard/Backend | 1 | No |

## Notes

- Replace `<site>`, `<node_id>`, `<gw_id>`, and `<event_type>` with final project values.
- Keep this file synchronized with `docs/message-schema.md`.
