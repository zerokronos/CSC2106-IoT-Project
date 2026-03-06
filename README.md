# INF2007-IoT-Project-

## Links

- Final Report (Google Docs): `<add-report-link>`
- Poster: `<add-poster-link>`
- Demo Video: `<add-demo-video-link>`

## Repo Structure

- `firmware/node/`: Embedded node firmware source and node-side scripts.
- `firmware/gateway/`: Gateway firmware/services for LoRa-to-MQTT bridging.
- `dashboard/`: UI/dashboard application and related assets.
- `docs/`: Working documentation for topics, schemas, and experiment logs.
- `docs/figures/`: Diagrams and images referenced by documentation.

## Recent Changes (March 2026)

- **New Thresholds**: Updated the system-wide alarm triggers to **57°C** for temperature and **80 PPM** for smoke levels.
- **Improved UI Monitoring**:
    - **Visual Flagging**: Nodes exceeding thresholds are now highlighted in **bright red** with an "ALARM" badge in the Node List.
    - **PPM Units**: Smoke levels are now displayed and logged in **PPM** (Parts Per Million) for better precision.
    - **Independent Breach Detection**: The system now tracks Temperature, Smoke, and Fire flags independently, allowing the Alert Feed to show complex fire scenarios (e.g., "High Temp & High Smoke").
    - **Recovery Alerts**: The Alert Feed now pushes a **"RECOVERED"** message once all sensor values for a flat return to nominal levels.
- **Timing Update**: The system watchdog, heartbeat, and simulation intervals have been synchronized to **10 seconds** to optimize network traffic and reliability.
- **Bug Fixes**: Resolved "Black Screen" runtime crashes by adding robust type-checking for numeric node IDs and defensive safety checks across all React components.

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
```bash
sudo apt update
sudo apt install nodejs npm -y
sudo apt install mosquitto mosquitto-clients -y
```

2. Configure Mosquitto
`sudo nano /etc/mosquitto/conf.d/websockets.conf`

Add the following into your websockets.conf:
```
listener 1883
listener 9001
protocol websockets
allow_anonymous true
```

3. Restart Mosquitto
`sudo systemctl restart mosquitto`

4. Build and Deploy Dashboard (Recommended for Stability)
   
   **On your Local PC:**
   ```bash
   cd dashboard
   npm run build
   # SCP the built 'dist' folder to the Pi
   scp -r dist/* (piusername)@(piaddress):/home/(piusername)/dashboard
   ```

   **On the Raspberry Pi:**
   Navigate to the dashboard folder:
   ```bash
   cd /home/(piusername)/dashboard
   # Serve the dashboard using a simple web server
   npx serve -s . -l 5173
   ```

   *(Alternative: If you prefer running in dev mode on the Pi, SCP the entire project, run `npm install`, then `npm run dev`.)*

5. For MQTT receive verification
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
