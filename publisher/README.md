# CSC2106 Group 6 — HDB Fire Monitoring Simulator

Simulator that publishes fake MQTT telemetry, heartbeats, and alerts for 3 virtual flat nodes.

---

## Prerequisites

- Python 3 — download from [python.org](https://www.python.org/downloads/)
- MQTT Explorer (optional) — download from [mqtt-explorer.com](https://mqtt-explorer.com)
- Mac: [Homebrew](https://brew.sh)
- Windows: Mosquitto installer from [mosquitto.org/download](https://mosquitto.org/download/)

---

## One-Time Setup

### Install Mosquitto (MQTT Broker)

**Mac:**
```bash
brew install mosquitto
```

**Windows:**
1. Go to [mosquitto.org/download](https://mosquitto.org/download/)
2. Download the Windows installer (`.exe`)
3. Run the installer and follow the steps
4. After installing, add Mosquitto to your PATH:
   - Search "Environment Variables" in the Start menu
   - Under System Variables, find `Path` and click Edit
   - Add `C:\Program Files\mosquitto`
   - Click OK

---

### Install Python MQTT Library

**Mac:**
```bash
pip3 install paho-mqtt
```

**Windows:**
```bash
pip install paho-mqtt
```

---

## Running the Simulator

### Step 1 — Start Mosquitto

**Mac:**
```bash
brew services start mosquitto
```
> Mosquitto will auto-start on every reboot after this.

**Windows (run Command Prompt as Administrator):**
```bash
net start mosquitto
```
> If that doesn't work, run Mosquitto manually in its own window:
> ```bash
> mosquitto -v
> ```
> Keep that window open and open a new Command Prompt for Step 2.

---

### Step 2 — Run the Simulator

**Mac:**
```bash
python3 simulator.py
```

**Windows:**
```bash
python simulator.py
```

You should see messages publishing in the terminal every 2 seconds.

---

### Step 3 — View Messages in MQTT Explorer (optional)

1. Open MQTT Explorer
2. Click **+** to add a new connection
3. Set:
   - Name: `Local Mosquitto`
   - Host: `localhost`
   - Port: `1883`
4. Click **Connect**

You will see live messages under:
- `telemetry/flat01`, `flat02`, `flat03` — sensor readings every 2s
- `heartbeat/flat01`, `flat02`, `flat03` — liveness ping every 30s
- `alert/flat03` — alerts when thresholds are crossed

---

## Stopping the Simulator

Press `Ctrl+C` in the terminal running `simulator.py`.

**Mac — stop Mosquitto:**
```bash
brew services stop mosquitto
```

**Windows — stop Mosquitto:**
```bash
net stop mosquitto
```

---

## What the Simulator Does

| Node | Behaviour |
|------|-----------|
| flat01 | Stable ~28°C, small random fluctuation |
| flat02 | Stable ~28°C, small random fluctuation |
| flat03 | Starts at 28°C, rises ~4.5°C per minute (anomaly) |

### Alert Thresholds

| Level | Condition | Buzzer | LED State |
|-------|-----------|--------|-----------|
| normal | temp < 45°C and smoke < 500 | off | normal |
| warn | temp > 45°C or smoke > 500 | off | warn |
| alarm | temp > 60°C or smoke > 800 | ON | alarm |

---

## Troubleshooting

### Mac

**`[ERROR] Could not connect to MQTT broker`**
```bash
brew services stop mosquitto
brew services start mosquitto
python3 simulator.py
```

**`Address already in use`**

Mosquitto is already running. Just run the simulator directly:
```bash
python3 simulator.py
```

**`zsh: command not found: pip`**
```bash
pip3 install paho-mqtt
```

---

### Windows

**`[ERROR] Could not connect to MQTT broker`**

Run Mosquitto manually in a separate window:
```bash
mosquitto -v
```
Then run the simulator in a new window:
```bash
python simulator.py
```

**`mosquitto is not recognized as a command`**

Mosquitto is not in your PATH. Either:
- Add `C:\Program Files\mosquitto` to your PATH (see setup above), or
- Navigate to the Mosquitto folder and run it directly:
```bash
cd "C:\Program Files\mosquitto"
mosquitto -v
```

**`pip is not recognized as a command`**
```bash
python -m pip install paho-mqtt
```
