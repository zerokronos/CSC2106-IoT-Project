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
