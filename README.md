# INF2007-IoT-Project-

## Links

- Final Report (Google Docs): `<add-report-link>`
- Poster: `<add-poster-link>`
- Demo Video: `<add-demo-video-link>`

## Repo Structure

- `firmware/node/`: Embedded node firmware source and node-side scripts.
- `firmware/node/lorawan_uno_template/`: Sanitized Maker UNO + Cytron LoRa-RFM LoRaWAN OTAA template (no secrets).
- `firmware/gateway/`: Gateway firmware/services for LoRa-to-MQTT bridging.
- `dashboard/`: UI/dashboard application and related assets.
- `docs/`: Working documentation for topics, schemas, and experiment logs.
- `docs/figures/`: Diagrams and images referenced by documentation.

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

Run the local pipeline from repo root:

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

Evidence to capture under `docs/figures/`:
- `ttn-live-data-lorawan-fallback.png`
- `bridge-log-ttn-uplink-200.txt`
- `dashboard-lorawan-alert.png`

For the full operator runbook, evidence checklist, and local verification steps, see `docs/runbook.md`.

## Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

> **Note:** Dashboard runs in simulation mode by default. To connect to the live MQTT broker, set `USE_REAL_MQTT = true` and update `MQTT_BROKER_URL` in `src/hooks/useDashboard.js`.

## Raspberry Pi Setup

1. Install Required
```
sudo apt update
sudo apt install nodejs npm -y
sudo apt install mosquitto mosquitto-clients -y
```

3. Configure Mosquitto
`sudo nano /etc/mosquitto/conf.d/websockets.conf`

Add the following into your websockets.conf:
```listener 1883
listener 9001
protocol websockets
allow_anonymous true
```

3. Restart Mosquito
`sudo systemctl restart mosquitto`

4. SCP dashboard files into Raspberry Pi
`scp (files location) (piusername)@(piaddress):(locationtosaveto)`

5. Navigate to dashboard folder
`cd (location)`

6. Delete existing node modules (skip this step if scp from clean copy which has not run npm install on a different operating system)
`rm -rf node_modules`

7. Install Node modules
`npm install`

8. Run Dashboard
`npm run dev`

9. For MQTT receive verification
`mosquitto_sub -h localhost -t "#" -v`

## Pico W Setup
1. Open up wifi folder and edit wifi-mqtt.py
2. Change WIFI_SSID to the wifi name of the wifi being used
3. Change WIFI_PASS to the password of the wifi being used
4. Change MQTT_BROKER to Raspberry Pi's IP Address
5. Run code in thorny and observe

## Local PC Connect to Dashboard
1. Connect to wifi network that devices are used
2. Open web browser
3. Type the link: RaspberryIp:5173 (change RaspberryIp to the actual Ip address of the Pi)
