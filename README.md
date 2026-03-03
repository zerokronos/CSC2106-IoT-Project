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

## Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

> **Note:** Dashboard runs in simulation mode by default. To connect to the live MQTT broker, set `USE_REAL_MQTT = true` and update `MQTT_BROKER_URL` in `src/hooks/useDashboard.js`.

#Raspberry Pi Setup

1. Install Required
sudo apt update
sudo apt install nodejs npm -y
sudo apt install mosquitto mosquitto-clients -y

2. Configure Mosquitto
sudo nano /etc/mosquitto/conf.d/websockets.conf

Add the following into your websockets.conmf:
listener 1883
listener 9001
protocol websockets
allow_anonymous true

3. Restart Mosquito
sudo systemctl restart mosquitto

4. SCP dashboard files into Raspberry Pi
scp (files location) (piusername)@(piaddress):(locationtosaveto)

5. Navigate to dashboard folder
cd (location)

6. Delete existing node modules (skip this step if scp from clean copy which has not run npm install on a different operating system)
rm -rf node_modules

7. Install Node modules
npm install

8. Run Dashboard
npm run dev


# Pico W Setup
1. Open up wifi folder and edit wifi-mqtt.py
2. Change WIFI_SSID to the wifi name of the wifi being used
3. Change WIFI_PASS to the password of the wifi being used
4. Change MQTT_BROKER to Raspberry Pi's IP Address

# Local PC Connect to Dashboard
1. Connect to wifi network that devices are used
2. Open web browser
3. Type the link: RaspberryIp:5173 (change RaspberryIp to the actual Ip address of the Pi)
