"""
CSC2106 Group 6 — HDB Fire Monitoring Simulator
================================================
Publishes fake telemetry, heartbeats, and alerts for 3 virtual flat nodes.

Requirements:
    pip install paho-mqtt

Usage:
    python simulator.py

Default broker: localhost:1883 (Mosquitto running locally)
To change broker: edit BROKER and PORT below.
"""

import json
import random
import time
import threading
import paho.mqtt.client as mqtt

# ─── CONFIG ───────────────────────────────────────────────────────────────────

BROKER = "localhost"
PORT = 1883

TELEMETRY_INTERVAL = 2       # seconds between telemetry publishes
HEARTBEAT_INTERVAL = 30      # seconds between heartbeats
ALERT_CHANCE = 0.01          # random alert 1% chance, node rolls a number between 0 and 1

NODES = ["flat01", "flat02", "flat03"]
ANOMALY_NODE = "flat03"      # this flat's temp will rise over time

# ─── STATE ────────────────────────────────────────────────────────────────────

# Shared baseline temperature
baseline_temp = 28.0

# Per-node state
state = {
    node: {
        "temp": baseline_temp + random.uniform(-0.5, 0.5),
        "smoke": random.uniform(50, 150),
        "seq": 0,
        "mode": "wifi",
        "buzzer": False,
        "led_state": "normal",
    }
    for node in NODES
}

# Anomaly drift — flat03 slowly rises
anomaly_drift = 0.0

# ─── MQTT SETUP ───────────────────────────────────────────────────────────────

client = mqtt.Client(client_id="hdb-simulator")

def on_connect(c, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected to broker at {BROKER}:{PORT}")
    else:
        print(f"[MQTT] Connection failed with code {rc}")

client.on_connect = on_connect

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def publish(topic, payload, qos=0):
    msg = json.dumps(payload)
    client.publish(topic, msg, qos=qos)
    print(f"  → {topic}: {msg}")

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def determine_led_state(temp, smoke):
    if temp > 60 or smoke > 800:
        return "alarm"
    elif temp > 45 or smoke > 500:
        return "warn"
    return "normal"

# ─── TELEMETRY LOOP ───────────────────────────────────────────────────────────

def telemetry_loop():
    global anomaly_drift

    while True:
        anomaly_drift += 0.15   # flat03 drifts up to 4.5°C per minute

        for node in NODES:
            s = state[node]
            s["seq"] += 1

            # Temperature: correlated baseline + small noise + anomaly if applicable
            noise = random.uniform(-0.3, 0.3)
            if node == ANOMALY_NODE:
                s["temp"] = baseline_temp + noise + anomaly_drift
            else:
                s["temp"] = baseline_temp + noise + random.uniform(-0.5, 0.5) #flat 1&2 incr/decr between rand.uniform

            # Smoke: mostly stable with some spikes
            s["smoke"] += random.uniform(-5, 5)
            s["smoke"] = max(30, min(1023, s["smoke"]))

            # Determine alert states
            s["led_state"] = determine_led_state(s["temp"], s["smoke"])
            s["buzzer"] = s["led_state"] == "alarm"

            # Publish telemetry
            payload = {
                "node_id": node,
                "timestamp": now_iso(),
                "mode": s["mode"],
                "temperature": round(s["temp"], 2),
                "smoke": round(s["smoke"], 1),
                "buzzer": s["buzzer"],
                "led_state": s["led_state"],
                "seq": s["seq"],
            }
            publish(f"telemetry/{node}", payload, qos=0)

            # Random alert event (independent of threshold — simulates spurious event)
            if random.random() < ALERT_CHANCE:
                fire_alert(node, s, reason="random")

            # Threshold-based alert
            if s["led_state"] in ("warn", "alarm"):
                fire_alert(node, s, reason="threshold")

        time.sleep(TELEMETRY_INTERVAL)

# ─── ALERT PUBLISHER ──────────────────────────────────────────────────────────

def fire_alert(node, s, reason="threshold"):
    alert_type = "combined" if s["temp"] > 45 and s["smoke"] > 500 else \
                 "temperature" if s["temp"] > 45 else "smoke"
    payload = {
        "node_id": node,
        "timestamp": now_iso(),
        "mode": s["mode"],
        "alert_type": alert_type,
        "severity": s["led_state"] if s["led_state"] != "normal" else "warn",
        "temperature": round(s["temp"], 2),
        "smoke": round(s["smoke"], 1),
        "seq": s["seq"],
        "reason": reason,
    }
    print(f"\n[ALERT] {node} — {alert_type} ({reason})")
    publish(f"alert/{node}", payload, qos=1)

# ─── HEARTBEAT LOOP ───────────────────────────────────────────────────────────

def heartbeat_loop():
    start_time = time.time()
    while True:
        for node in NODES:
            s = state[node]
            payload = {
                "node_id": node,
                "timestamp": now_iso(),
                "mode": s["mode"],
                "status": "online",
                "uptime_s": int(time.time() - start_time),
                "seq": s["seq"],
            }
            publish(f"heartbeat/{node}", payload, qos=0)
        time.sleep(HEARTBEAT_INTERVAL)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  CSC2106 Group 6 — HDB Monitoring Simulator")
    print("=" * 55)
    print(f"  Broker     : {BROKER}:{PORT}")
    print(f"  Nodes      : {', '.join(NODES)}")
    print(f"  Anomaly    : {ANOMALY_NODE} (temp rises over time)")
    print(f"  Telemetry  : every {TELEMETRY_INTERVAL}s")
    print(f"  Heartbeat  : every {HEARTBEAT_INTERVAL}s")
    print(f"  Alert odds : {ALERT_CHANCE*100:.0f}% per tick per node")
    print("=" * 55)
    print()

    try:
        client.connect(BROKER, PORT, keepalive=60)
    except ConnectionRefusedError:
        print("[ERROR] Could not connect to MQTT broker.")
        print("        Make sure Mosquitto is running: sudo systemctl start mosquitto")
        print("        Or on Mac/Windows: start Mosquitto from the app.")
        exit(1)

    client.loop_start()

    # Run telemetry and heartbeat in separate threads
    t1 = threading.Thread(target=telemetry_loop, daemon=True)
    t2 = threading.Thread(target=heartbeat_loop, daemon=True)
    t1.start()
    t2.start()

    print("Simulator running.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Simulator stopped.")
        client.loop_stop()
        client.disconnect()
