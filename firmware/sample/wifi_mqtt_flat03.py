import network
import time
import json
import ubinascii
import random
import usocket as socket
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
WIFI_SSID = "CHANGE_THIS"    # <-- USE YOUR WIFI NAME
WIFI_PASS = "CHANGE_THIS"    # <-- USE YOUR WIFI PASSWORD
MQTT_BROKER = "CHANGE_THIS"  # <-- USE YOUR PI's IP ADDRESS
NODE_ID = "flat03"  # <-- CHANGE THIS FOR EACH FLAT (flat01, flat02, flat03, etc.)
CLIENT_ID = ubinascii.hexlify(machine.unique_id()) # Unique ID for this Pico
TOPIC_TELEMETRY = b"telemetry/site1/" + NODE_ID.encode() # Main data channel
TOPIC_HEARTBEAT = b"heartbeat/site1/" + NODE_ID.encode()
HEARTBEAT_INTERVAL = 10 # Seconds between keep-alive signals
MAX_RETRIES = 3
MQTT_TOTAL_WINDOW_MS = 6000
MQTT_CONNECT_TIMEOUT_S = 2
MAX_UART_LINE_BYTES = 256
SIMULATION_MODE = False  # Set to False when Arduino is connected
SIMULATION_INTERVAL = 10  # Send simulated data every N seconds
PICO_KEEPALIVE_INTERVAL = 2  # Seconds between UART keepalive messages to Uno

# --- 2. HARDWARE SETUP ---
# UART 0: TX=GP0, RX=GP1 (9600 baud to match Arduino)
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
led = Pin("LED", Pin.OUT)
failover_button = Pin(21, Pin.IN, Pin.PULL_UP)

# --- Global state for toggle ---
manual_lora_override = False
lora_failover_active = False
last_button_press_time = 0
DEBOUNCE_MS = 200 # 200ms debounce time
last_simulation_time = 0  # Track simulation data sending
test_data_index = 0  # Index for cycling through test data
last_pico_keepalive = 0

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

    start_ms = time.ticks_ms()
    previous_timeout = None
    has_setdefault = hasattr(socket, "setdefaulttimeout")
    if has_setdefault:
        if hasattr(socket, "getdefaulttimeout"):
            previous_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(MQTT_CONNECT_TIMEOUT_S)

    try:
        for attempt in range(1, MAX_RETRIES + 1):
            elapsed_ms = time.ticks_diff(time.ticks_ms(), start_ms)
            if elapsed_ms >= MQTT_TOTAL_WINDOW_MS:
                break

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
                if attempt < MAX_RETRIES and not network.WLAN(network.STA_IF).isconnected():
                    print("WiFi dropped, reconnecting...")
                    connect_wifi()
    finally:
        if has_setdefault:
            socket.setdefaulttimeout(previous_timeout)

    return False

def send_heartbeat():
    """Sends a periodic keep-alive signal."""
    try:
        # Don't send heartbeat in LoRa override — simulate full WiFi loss
        if manual_lora_override:
            return

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

        # WiFi+MQTT confirmed working — exit LoRa failover if active
        if not SIMULATION_MODE:
            set_uno_lora_mode(False)
    except Exception as e:
        print(f"Heartbeat Failed: {e}")


def read_uno_json_line():
    """Read one UART line from Uno and parse JSON if valid."""
    if not uart.any():
        return None

    line = uart.readline()
    if not line:
        return None

    # Guard against garbage/oversized frames from serial noise.
    if len(line) > MAX_UART_LINE_BYTES:
        print("Discarded oversized UART line")
        return None

    try:
        decoded = line.decode('utf-8').strip()
    except Exception:
        return None

    if not decoded or not decoded.startswith("{"):
        # Ignore LMIC/debug text from Uno that is not JSON payload/ack.
        return None

    try:
        return json.loads(decoded)
    except ValueError:
        print(f"Received invalid JSON from Uno: {decoded}")
        return None


def sanitize_sensor_data(data):
    """Validate and normalize telemetry payload before publishing."""
    if not isinstance(data, dict):
        return None

    if "temp" not in data or "smoke" not in data:
        return None

    try:
        temp = float(data.get("temp"))
        smoke = float(data.get("smoke"))
    except (TypeError, ValueError):
        print(f"Rejected non-numeric sensor payload: {data}")
        return None

    # Conservative bounds to reject corrupted frames.
    if temp < -20 or temp > 120:
        print(f"Rejected temp out of range: {temp}")
        return None
    if smoke < 0 or smoke > 1:
        print(f"Rejected smoke out of range: {smoke}")
        return None

    fire_raw = data.get("fire", 0)
    try:
        fire = 1 if int(fire_raw) else 0
    except (TypeError, ValueError):
        fire = 0

    node_id = data.get("node_id", NODE_ID)
    if not isinstance(node_id, str) or not node_id.strip():
        node_id = NODE_ID

    return {
        "node_id": node_id,
        "temp": round(temp, 2),
        "smoke": round(smoke, 4),
        "fire": fire,
    }


def set_uno_lora_mode(enable):
    """Send mode toggle to Uno only when state changes."""
    global lora_failover_active

    if enable == lora_failover_active:
        return

    cmd = "LORA_ON\n" if enable else "LORA_OFF\n"
    uart.write(cmd)
    lora_failover_active = enable
    print(f"Sent to Uno: {cmd.strip()}")


def send_pico_keepalive(force=False):
    """Tell the Uno this Pico is alive and WiFi-capable."""
    global last_pico_keepalive

    if manual_lora_override:
        return

    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        return

    now = time.time()
    if not force and (now - last_pico_keepalive) < PICO_KEEPALIVE_INTERVAL:
        return

    try:
        uart.write("PICO_HELLO\n")
        last_pico_keepalive = now
    except Exception as e:
        print(f"Failed to send Pico keepalive: {e}")

# --- 4. MAIN LOOP ---

# Initial connection
if connect_wifi():
    send_pico_keepalive(force=True)
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
            set_uno_lora_mode(True)
            led.off()
        else:
            print("TOGGLE: Manual LoRa override DEACTIVATED. Reverting to WiFi.")
            set_uno_lora_mode(False)
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
        parsed = read_uno_json_line()
        if parsed and "temp" in parsed and "smoke" in parsed:
            data = parsed
            print(f"Data from Uno: {data}")
    
    # --- PUBLISH DATA IF AVAILABLE ---
    if data:
        # Prepare Payload for Dashboard
        payload = json.dumps({
            "node_id": NODE_ID,
            "temp": data.get("temp", 0),
            "smoke": data.get("smoke", 0),
            "fire_detected": data.get("fire", 0),
            "mode": "lora" if lora_failover_active else "wifi",
            "ts": time.time()
        })

        print(f"Sending Telemetry: {payload}")
        # Attempt to send via WiFi (with Retries)
        success = publish_mqtt_safe(TOPIC_TELEMETRY, payload)

        if success:
            # MQTT is back/online -> Tell Uno to STOP LoRa (only if state changed)
            print("WiFi Success -> Sending LORA_OFF")
            if not SIMULATION_MODE:
                set_uno_lora_mode(False)
            led.on()
        else:
            # After N times unsuccessfully -> Tell Uno to START LoRa (only if state changed)
            print("WiFi Failed -> Sending LORA_ON")
            if not SIMULATION_MODE:
                set_uno_lora_mode(True)
            led.off()

    # Periodic check to ensure the Pico stays connected to WiFi
    if not network.WLAN(network.STA_IF).isconnected():
        if connect_wifi():
            send_pico_keepalive(force=True)

    # UART keepalive so the Uno can detect Pico power loss and recovery.
    send_pico_keepalive()

    # Periodic Heartbeat
    if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
        send_heartbeat()
        last_heartbeat = time.time()
        
    time.sleep(0.1) # Small delay to prevent CPU overheating