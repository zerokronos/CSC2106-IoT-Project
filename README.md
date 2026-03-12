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
For the step-by-step WisGate/TTN verification walkthrough, see `docs/wisgate-ttn-test-runbook.md`.

## Dashboard Setup

```bash
cd dashboard
npm install
npm run dev

## IF Dashboard Blackscreen
cd dashboard
npm run build
scp -r src pi_usernmae@pi_ip:~/yourfolder/dashboard/ example

Open `http://pi_ip:5173` in your browser.


## Raspberry Pi Setup

1. Install Required
```

sudo apt update
sudo apt install nodejs npm -y
sudo apt install mosquitto mosquitto-clients -y

````

3. Configure Mosquitto
`sudo nano /etc/mosquitto/conf.d/websockets.conf`

Add the following into your websockets.conf:
```listener 1883
listener 9001
protocol websockets
allow_anonymous true
````

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


## Full setup guide

## LoRa WisGate Setup
1. Attach Antenna into Wisgate
2. Attach power cable and power On
3. Look for Wifi network RAK7268CV2_XXXX where XXXX is last 4 digits of SN for WisGate
4. Connect to the Wifi network
5. Go to web browser and type in the following details
- Browser Address: 192.168.230.1
- Username: Root
- Password: admin12345678! (Do not change the password)
6. Once entered, access the network settings (3rd vertical button on the left)
7. click on wifi and click on settings
8. Set the following settings
- Interface Enabled
- SSID click scan and look for wifi network
- Select encrpytion of the wifi network
- Enter key (password)
- Protocol set as DHCP
- Click Save
9. Disconnection to the LoRa wifi network is normal. Wait for it to restart.
10. Look at the LoRa for "Blue Breathing" of the LED. If blue the network is successfully configured. If "Red Breathing" of the LED, means that failure.
11. Once connected go to https://www.thethingsnetwork.org/
12. Click on login on the top right side of the bar and then click on "Login to The Things Network"  and enter the details behind the WisGate under "ID" and "PW"
13. Once login is successful, go to the link https://console.cloud.thethings.network/ and click on Austraila 1.

## Pico W Setup
1. Open up wifi folder and open wifi-mqtt.py using thonny
2. Plug in Pico W into laptop
3. Change WIFI_SSID to the wifi name of the wifi network being used
4. Change WIFI_PASS to the password of the wifi network being used
5. Change MQTT_BROKER to Raspberry Pi IP Address
6. Run code in thorny and observe

## Raspberry Pi Setup
1. Connect Pi and PC to same wifi network
2. Copy dashboard and bridge into Pi (Do it on your PC terminal)
```
scp -r <Location_Of_dashboard_Folder_In_Your_PC> <Pi_Username_Here>@<PI_IP/PI_NAME>:~/<Location_That_You_Want_To_Save>
scp -r <Location_Of_server/bridge_Folder_In_Your_PC> <Pi_Username_Here>@<PI_IP/PI_NAME>:~/<Location_That_You_Want_To_Save>
```
3. SSH into Pi
`ssh <Pi_Username_Here>@<PI_IP/PI_NAME>`
4. Install Pi packages
```
sudo apt udate
sudo apt install -y mosquitto mosquitto-clients modejs npm python3 python3-venv python
```
5. Configure Mosquitto (MQTT + WebSocket)
```
cd /etc/mosquitto/conf.d
nano webscokets.conf
```
Input the following:
```
listener 1883
allow_anonymous true

listener 9001
protocol websockets
allow_anonymous true
```
6. Restart and Enable Mosquitto
```
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto
```
7. Verify ports
`sudo ss -lntp | grep -E '1883|9001'`
You should see something similar:
```
LISTEN 0 100 0.0.0.0:1883 0.0.0.0:* users:(("mosquitto",pid=2121,fd=5))
LISTEN 0 4096 0.0.0.0:9001 0.0.0.0:* users:(("mosquitto",pid=2121,fd=10))
LISTEN 0 100 [::]:1883 [::]:* users:(("mosquitto",pid=2121,fd=6))
LISTEN 0 4096 [::]:9001 [::]:* users:(("mosquitto",pid=2121,fd=11))
```
8. Configure and run bridge on Pi
```
cd <bridge_folder_location>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
9. Start Bridge
```
export MQTT_HOST=localhost
export MQTT_PORT=1883
export BRIDGE_HTTP_PORT=8000
uvicorn app:app --host 0.0.0.0 --port 8000
```
10. Open new terminal and SSH into Pi (Refer to 3)
11. Health Check
`curl http://127.0.0.1:8000/health`
You should see the following: (Focus on "ok":true)
url http://127.0.0.1:8000/health
{"ok":true,"mqtt_host":"localhost","mqtt_port":1883,"dashboard":"/dashboard"}
12. Install and run ngrok on Pi
```
cd /tmp
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz
tar -xzf ngrok-v3-stable-linux-arm64.tgz
sudo mv ngrok /usr/local/bin/ngrok
ngrok version
```
13. Go to https://ngrok.com and sign up for an account
14. In your dashboard, on the vertical bar, click on Your Authtoken and copy the token
15. In your dashboard, on the vertical bar, click on domains and create a new domain and copy the domain
16. Add auth token:
`ngrok config add-authtoken <YOUR_NGROK_TOKEN>`
17. Start tunnel
` ngrok http 8000`
18. Go to your TTN console (Refer to LoRa WisGate Setup)
19. In your TTN console go to Applications (vertical bar on the left) -> Your Application Name -> Webhooks(vertical bar on the left) -> Add webhook -> Custom webhook
Input the following details:
Webhook ID: What you want to name the webhook (not important)
Webhook Format: JSON
Base URL: Paste your ngrok domain here
Uplink Message: Tick (Enabled)
Click Add Webhook
20. Go to dashboard
```
cd <dashboard_folder_location>
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```
21. Open another terminal and SSH into Pi (Refer to 3)
22. Run this command to see if MQTT messages are being sent to Pi
` mosquitto_sub -h localhost -t "#" -v`

## Maker Uno Setup
1. Install Arduino Libraries
- Go to Sketch (top horizontal bar) -> Include Library -> Manage Library
- Top horizontal bar search for "MCCI LoRaWAN LMIC library"
- Select latest version and Install
2. Get APPEUI, DEVEUI and APPKEY from The Things Network
3. Put APEUI, reversed DEVEUI and APPKEY into Maker Uno
4. Upload into Maker Uno
5. Connect GPIO 0, 1 and GND of Maker Uno to GPIO 0, 1 and GND of Pico W Respectively