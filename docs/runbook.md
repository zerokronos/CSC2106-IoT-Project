# Local Runbook: TTN Bridge + MQTT + Dashboard + Simulator

## Assumptions
- Mosquitto is installed on the machine.
- Python 3.10+ is installed.
- You are at repo root: `CSC2106-IoT-Project`.

## 1) Start Mosquitto broker (local)

```bash
mosquitto -v
```

If you prefer a config file:

```bash
mosquitto -c /etc/mosquitto/mosquitto.conf -v
```

## 2) Install bridge dependencies

```bash
cd server/bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Run bridge HTTP server

```bash
cd server/bridge
source .venv/bin/activate
export MQTT_HOST=localhost
export MQTT_PORT=1883
export BRIDGE_HTTP_PORT=8000
uvicorn app:app --host 0.0.0.0 --port "$BRIDGE_HTTP_PORT"
```

## Stable run (recommended on mobile data)

Use the helper scripts so the bridge keeps running even if your terminal session drops.

```bash
cd server/bridge
./scripts/mqtt_status.sh
./scripts/bridge_start.sh
./scripts/bridge_status.sh
```

Stop it cleanly when needed:

```bash
cd server/bridge
./scripts/bridge_stop.sh
```

The helper scripts use these defaults unless you override them before starting:
- `MQTT_HOST=localhost`
- `MQTT_PORT=1883`
- `BRIDGE_HTTP_PORT=8000`

Bridge runtime files:
- log: `/tmp/csc2106_bridge.log`
- pid: `/tmp/csc2106_bridge.pid`

## Real TTN webhook via ngrok (works on phone hotspot)

For the full WisGate + TTN + ngrok + bridge end-to-end verification checklist, see `docs/wisgate-ttn-test-runbook.md`.

Start the local pieces, expose the bridge publicly with ngrok, then verify the full public path before configuring TTN:

```bash
cd server/bridge
./scripts/mqtt_status.sh
./scripts/bridge_start.sh
./scripts/ttn_ngrok_start.sh
./scripts/ttn_webhook_verify.sh
```

The ngrok helper stores:
- ngrok log: `/tmp/csc2106_ngrok.log`
- ngrok pid: `/tmp/csc2106_ngrok.pid`
- ngrok HTTPS URL: `/tmp/csc2106_ngrok_url.txt`

TTN Console steps for a Custom webhook:
- Open your TTN application.
- Go to `Integrations` -> `Webhooks`.
- Click `Add Webhook`.
- Select `Custom webhook`.
- Set `Webhook ID` to a stable name such as `csc2106-bridge-ngrok`.
- Set `Webhook format` to `JSON`.
- Set `Base URL` to the exact ngrok endpoint printed by `./scripts/ttn_ngrok_start.sh`, for example `<NGROK_HTTPS_URL>/ttn/uplink`.
- In `Enabled event types`, enable `Uplink message`.
- Save the webhook.

Notes from TTN webhook behavior:
- TTN docs say a Custom webhook is configured with a `Webhook ID`, `JSON` format, and a `Base URL`.
- TTN appends event paths only if you configure them. For this bridge, keep the Base URL itself as `.../ttn/uplink` so TTN posts directly to the bridge endpoint.
- TTN requires the endpoint to be reachable. A successful check should return `HTTP 200 OK`.
- If your ngrok URL changes, update the TTN webhook Base URL and save again.

Useful commands while testing:

```bash
tail -f /tmp/csc2106_bridge.log
tail -f /tmp/csc2106_ngrok.log
open http://127.0.0.1:8000/dashboard
```

Stop everything cleanly:

```bash
cd server/bridge
./scripts/bridge_stop.sh
[[ -f /tmp/csc2106_ngrok.pid ]] && kill "$(cat /tmp/csc2106_ngrok.pid)" 2>/dev/null || true
rm -f /tmp/csc2106_ngrok.pid /tmp/csc2106_ngrok_url.txt
```

## LoRaWAN Fallback (WisGate + TTN) — Status: Verified

Architecture overview:
- `UNO -> WisGate -> TTN -> webhook -> ngrok -> bridge -> MQTT -> dashboard`

Radio/network settings:
- Frequency plan: `AU915 FSB2`

Payload contract:
- 7-byte uplink matching the bridge decoder in `server/bridge/ttn_decoder.py`
- `byte0=node_id`
- `byte1=msg_type`
- `byte2-3=temp_x10` (big-endian unsigned integer)
- `byte4-5=smoke_x100` (big-endian unsigned integer)
- `byte6=severity`

Run the verified local pipeline from repo root:

```bash
server/bridge/scripts/mqtt_status.sh
server/bridge/scripts/bridge_start.sh
server/bridge/scripts/ttn_ngrok_start.sh
server/bridge/scripts/ttn_webhook_verify.sh
```

TTN Console steps:
- Create a `Custom webhook`.
- Set `Base URL` to `<NGROK_HTTPS_URL>/ttn/uplink`.
- Enable `Uplink message` events.

Known gotchas:
- The ngrok domain must match exactly. Do not mix `.dev`, `.app`, or any stale ngrok hostname.
- TTN `DevEUI` must match the device `DevEUI` exactly.
- `mosquitto` may already be running on port `1883`.

### Evidence
- Capture a TTN Live Data screenshot and save it as `docs/figures/ttn-live-data-lorawan-fallback.png`.
- Capture the bridge log showing `POST /ttn/uplink 200 OK` and save it as `docs/figures/bridge-log-ttn-uplink-200.txt`.
- Capture a dashboard screenshot showing `mode=lorawan` and an alert state, and save it as `docs/figures/dashboard-lorawan-alert.png`.
- Do not include secrets in screenshots or logs. Use placeholders for `AppKey`, session keys, ngrok auth tokens, or any other credentials.

## 4) Run simulator (new terminal)

```bash
cd server/bridge
source .venv/bin/activate
cd ../..
python3 tools/simulator/publish_simulated_flats.py
```

Simulator publishes:
- telemetry every 2 seconds for `flat01`, `flat02`, `flat03`
- heartbeat every 30 seconds
- injected anomaly + alert for `flat02`

## 5) Open dashboard

With bridge running:

```bash
open http://127.0.0.1:8000/dashboard
```

On Raspberry Pi OS (headless or remote):

```bash
# from another machine browser
http://<pi-ip>:8000/dashboard
```

## 6) Test TTN webhook via curl

Binary payload format:
- byte0 node_id
- byte1 msg_type
- byte2-3 temp_x10
- byte4-5 smoke_x100
- byte6 severity

Example (`node_id=7`, `msg_type=1`, `temp=30.0C`, `smoke=0.03`, `severity=0`):

```bash
curl -X POST http://127.0.0.1:8000/ttn/uplink \
  -H 'Content-Type: application/json' \
  -d '{
    "end_device_ids": {"device_id": "flat07"},
    "received_at": "2026-02-27T12:00:00Z",
    "uplink_message": {"frm_payload": "BwEBLAADAA=="}
  }'
```

Dev/test direct format example:

```bash
curl -X POST http://127.0.0.1:8000/ttn/uplink \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "flat01",
    "msg_type": "telemetry",
    "temp_c": 28.4,
    "smoke": 0.02,
    "severity": "none",
    "reason": "manual-test"
  }'
```

## 7) Run tests

Unit tests:

```bash
cd server/bridge
source .venv/bin/activate
pytest -q
```

Integration smoke (requires broker + bridge already running):

```bash
cd server/bridge
source .venv/bin/activate
python tests/smoke_ttn_to_mqtt.py --http http://127.0.0.1:8000
```

## Troubleshooting
- Address already in use on `1883`: run `lsof -nP -iTCP:1883` or `./server/bridge/scripts/mqtt_status.sh` to see what already owns the broker port. Stop the conflicting process, or start your intended broker only once.
- `ConnectionRefusedError` to MQTT: make sure Mosquitto is actually running with `mosquitto -v` in another terminal, then restart the bridge with `./server/bridge/scripts/bridge_stop.sh` and `./server/bridge/scripts/bridge_start.sh`.
- Tail logs: use `tail -f /tmp/csc2106_bridge.log` for live output, or `./server/bridge/scripts/bridge_status.sh` for the latest 20 lines.
