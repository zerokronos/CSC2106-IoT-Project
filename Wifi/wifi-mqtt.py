import network
import time
import json
import ubinascii
import random
from machine import UART, Pin
from umqtt.simple import MQTTClient

# Import test data from separate file
try:
    from test_data import TEST_SENSOR_DATA
    TEST_DATA_AVAILABLE = True
except ImportError:
    TEST_SENSOR_DATA = None
    TEST_DATA_AVAILABLE = False

# --- 1. CONFIGURATION ---
WIFI_SSID = "changethis"
WIFI_PASS = "changethis"
MQTT_BROKER = "changethis"  # <-- USE YOUR PI's IP ADDRESS
NODE_ID = "flat02"  # <-- CHANGE THIS FOR EACH FLAT (flat01, flat02, flat03, etc.)
CLIENT_ID = ubinascii.hexlify(machine.unique_id()) # Unique ID for this Pico
TOPIC_TELEMETRY = b"telemetry/site1/" + NODE_ID.encode() # Main data channel
TOPIC_HEARTBEAT = b"heartbeat/site1/" + NODE_ID.encode()
HEARTBEAT_INTERVAL = 10 # Seconds between keep-alive signals
MAX_RETRIES = 3
SIMULATION_MODE = True  # Set to False when Arduino is connected
SIMULATION_INTERVAL = 10  # Send simulated data every N seconds

# --- 2. HARDWARE SETUP ---
# UART 0: TX=GP0, RX=GP1 (9600 baud to match Arduino)
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
led = Pin("LED", Pin.OUT)
failover_button = Pin(21, Pin.IN, Pin.PULL_UP)

# --- Global state for toggle ---
manual_lora_override = False
last_button_press_time = 0
DEBOUNCE_MS = 200 # 200ms debounce time
last_simulation_time = 0  # Track simulation data sending
test_data_index = 0  # Index for cycling through test data

# --- 3. FUNCTIONS ---

def connect_wifi():
    """Initializes WiFi and keeps trying until connected."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Debug: Scan and print available networks
    print("Scanning for WiFi networks...")
    nets = wlan.scan()
    for net in nets:
        print(f"Found SSID: '{net[0].decode('utf-8')}' | Signal: {net[3]}")

    if not wlan.isconnected():
        print(f"Connecting to {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        # Wait up to 20 seconds for a connection
        for _ in range(20):
            status = wlan.status()
            if status < 0 or status >= 3: # Break on error or success
                break
            time.sleep(1)

    status = wlan.status()
    if status == 3: # STAT_GOT_IP
        print("WiFi Connected! IP:", wlan.ifconfig()[0])
        led.on() # Solid LED means system is ready
        return True
    else:
        error_msg = "Unknown error"
        if status == -1: error_msg = "Connection failed"
        elif status == -2: error_msg = "No AP found (check SSID)"
        elif status == -3: error_msg = "Wrong password"
        print(f"WiFi Connection Failed. Status: {status} ({error_msg})")
        led.off()
        return False

def publish_mqtt_safe(topic, payload):
    """Attempts to publish to MQTT with retries. Returns True if success."""
    # Check manual override
    if manual_lora_override:
        print("Manual Override: Simulating WiFi Failure")
        return False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"MQTT Attempt {attempt}/{MAX_RETRIES}...")
            client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=10)
            client.connect()
            client.publish(topic, payload)
            client.disconnect()
            print("Publish Success")
            return True
        except Exception as e:
            print(f"Publish Failed: {e}")
            time.sleep(1) # Wait 1s before retry
            
            # Attempt to reconnect WiFi if it dropped
            if not network.WLAN(network.STA_IF).isconnected():
                print("WiFi dropped, reconnecting...")
                connect_wifi()
                
    return False

def send_heartbeat():
    """Sends a periodic keep-alive signal."""
    try:
        # Check manual override
        if manual_lora_override:
            return # Don't send heartbeat in override mode

        # Prevent error logs if WiFi is already known to be down
        if not network.WLAN(network.STA_IF).isconnected():
            return

        client = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)
        client.connect()
        
        payload = json.dumps({
            "node_id": NODE_ID,
            "msg_type": "heartbeat",
            "ts": time.time(),
            "mode": "wifi"
        })
        
        print(f"Sending Heartbeat: {payload}")
        client.publish(TOPIC_HEARTBEAT, payload)
        print("Heartbeat sent.")
        client.disconnect()
    except Exception as e:
        print(f"Heartbeat Failed: {e}")

# --- 4. MAIN LOOP ---

# Initial connection
connect_wifi()
print("System Online. Monitoring Arduino sensor data...")

last_heartbeat = time.time()


while True:
    # --- Button Check for Manual Failover Toggle ---
    now_ms = time.ticks_ms()
    if failover_button.value() == 0 and time.ticks_diff(now_ms, last_button_press_time) > DEBOUNCE_MS:
        last_button_press_time = now_ms
        manual_lora_override = not manual_lora_override # Toggle the state
        if manual_lora_override:
            print("TOGGLE: Manual LoRa override ACTIVATED.")
            led.off()
        else:
            print("TOGGLE: Manual LoRa override DEACTIVATED. Reverting to WiFi.")
            # Restore LED status based on actual WiFi connection
            if network.WLAN(network.STA_IF).isconnected():
                led.on()

    # Get sensor data from test data or Arduino
    data = None
    
    # --- SIMULATION MODE: Use test data from test_data.py ---
    if SIMULATION_MODE and (time.time() - last_simulation_time) > SIMULATION_INTERVAL:
        last_simulation_time = time.time()
        
        if TEST_DATA_AVAILABLE and TEST_SENSOR_DATA:
            # Cycle through test data
            test_case = TEST_SENSOR_DATA[test_data_index]
            test_data_index = (test_data_index + 1) % len(TEST_SENSOR_DATA)
            
            data = {
                "temp": test_case["temp"],
                "smoke": test_case["smoke"],
                "fire": test_case["fire"]
            }
            print(f"[TEST DATA #{test_data_index}] {test_case['description']}")
            print(f"[TEST DATA] {data}")
        else:
            # Fallback to random if test data not available
            print("[WARNING] test_data.py not found, using random data")
            data = {
                "temp": 25.0 + random.uniform(-2, 2),  # 23-27°C range
                "smoke": random.uniform(0, 0.5),        # 0-0.5 range
                "fire": 0
            }
            print(f"[SIMULATED] Data: {data}")
    
    # --- REAL MODE: Read from Arduino via UART ---
    elif not SIMULATION_MODE and uart.any():
        # Read the message from the Uno
        line = uart.readline()
        try:
            # Expecting JSON from Uno: {"temp": 30.5, "smoke": 0.2, "fire": 0}
            data = json.loads(line.decode('utf-8').strip())
            print(f"Data from Uno: {data}")
        except ValueError:
            print("Received invalid data from Uno (not JSON)")
    
    # --- PUBLISH DATA IF AVAILABLE ---
    if data:
        # Prepare Payload for Dashboard
        payload = json.dumps({
            "node_id": NODE_ID,
            "temp": data.get("temp", 0),
            "smoke": data.get("smoke", 0),
            "fire_detected": data.get("fire", 0),
            "mode": "wifi",
            "ts": time.time()
        })
        
        print(f"Sending Telemetry: {payload}")
        # Attempt to send via WiFi (with Retries)
        success = publish_mqtt_safe(TOPIC_TELEMETRY, payload)
        
        if success:
            # MQTT is back/online -> Tell Uno to STOP LoRa
            print("WiFi Success -> Sending LORA_OFF")
            if not SIMULATION_MODE:
                uart.write("LORA_OFF\n")
            led.on()
        else:
            # After N times unsuccessfully -> Tell Uno to START LoRa
            print("WiFi Failed -> Sending LORA_ON")
            if not SIMULATION_MODE:
                uart.write("LORA_ON\n")
            led.off()

    # Periodic check to ensure the Pico stays connected to WiFi
    if not network.WLAN(network.STA_IF).isconnected():
        connect_wifi()

    # Periodic Heartbeat
    if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
        send_heartbeat()
        last_heartbeat = time.time()
        
    time.sleep(0.1) # Small delay to prevent CPU overheating