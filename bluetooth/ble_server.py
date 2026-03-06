# ble_server.py (Pico W 1 - Flat Node / Server)
# Based on working lab ble_server.py
# Modified for CSC2106 Group 6 — HDB Fire Monitoring System
#
# This Pico acts as the flat node.
# A technician connects via ble_client.py and pushes config (node_id, thresholds).
# Config is saved to flash and persists after reboot.

import bluetooth
import time
import machine
import json
from micropython import const

# --- UUIDs (must match client) ---
SERVICE_UUID     = bluetooth.UUID(0x1B02)
CONFIG_CHAR_UUID = bluetooth.UUID(0x1B00)  # Client writes config JSON here
STATUS_CHAR_UUID = bluetooth.UUID(0x1B01)  # Server notifies confirmation here

# --- BLE Event constants ---
CENTRAL_CONNECT    = const(1)
CENTRAL_DISCONNECT = const(2)
GATTS_WRITE        = const(3)
MTU_EXCHANGED      = const(21)

ADV_INTERVAL = 200000

# --- Hardware ---
led = machine.Pin("LED", machine.Pin.OUT)

# --- Default config (before commissioning) ---
node_config = {
    "node_id": "unprovisioned",
    "temp_warn": 45,
    "temp_alarm": 60,
    "smoke_warn": 500,
    "smoke_alarm": 800,
    "telemetry_interval": 2
}

def save_config(config):
    """Save config to flash so it persists after reboot."""
    try:
        with open("node_config.json", "w") as f:
            json.dump(config, f)
        print("[CONFIG] Saved to flash.")
    except Exception as e:
        print(f"[CONFIG] Save failed: {e}")

def load_config():
    """Load config from flash if it exists."""
    try:
        with open("node_config.json", "r") as f:
            return json.load(f)
    except:
        print("[CONFIG] No saved config, using defaults.")
        return node_config

def blink_led(times=5, delay=0.15):
    """Blink LED to signal config received successfully."""
    for _ in range(times):
        led.on()
        time.sleep(delay)
        led.off()
        time.sleep(delay)


# --- BLE Server ---
class BLECommissioningServer:

    def __init__(self, device_name):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._handle_event)

        # FIX: advertise willingness to use 256-byte MTU
        # Allows client to send JSON payloads up to 253 bytes (MTU-3)
        self.ble.config(mtu=256)

        # Define service with 2 characteristics
        config_characteristic = (CONFIG_CHAR_UUID, 0x000A)  # READ | WRITE
        status_characteristic  = (STATUS_CHAR_UUID, 0x0012)  # READ | NOTIFY
        service = (SERVICE_UUID, (config_characteristic, status_characteristic))

        # Register and extract handles
        handles = self.ble.gatts_register_services((service,))
        self.config_handle = handles[0][0]
        self.status_handle = handles[0][1]

        # FIX: enlarge server-side buffer for config characteristic (default is 20 bytes)
        self.ble.gatts_set_buffer(self.config_handle, 256)

        self.connected_clients = set()
        self.device_name = device_name

        # FIX: flags for deferred actions (must not block or call gap_advertise inside IRQ)
        self._do_blink     = False
        self._do_advertise = False

        # Write initial status
        self.ble.gatts_write(self.status_handle, b"unprovisioned")
        self._start_advertising()

        print(f"[BLE] Server started. Advertising as '{device_name}'")

    def _handle_event(self, event, data):

        if event == CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self.connected_clients.add(conn_handle)
            led.on()
            print("[BLE] Commissioning tool connected.")

        elif event == CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self.connected_clients.discard(conn_handle)
            led.off()
            # FIX: defer gap_advertise — calling it directly here causes ENODEV
            self._do_advertise = True
            print("[BLE] Disconnected. Will resume advertising...")

        elif event == GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self.config_handle:
                try:
                    raw = self.ble.gatts_read(value_handle)
                    received = json.loads(raw.decode("utf-8"))
                    print(f"[CONFIG] Received: {received}")

                    # Update and save config
                    global node_config
                    for key in received:
                        node_config[key] = received[key]
                    save_config(node_config)

                    # Send confirmation back via notify
                    confirmation = f"OK:{node_config['node_id']}"
                    self.ble.gatts_write(self.status_handle, confirmation.encode("utf-8"))
                    for client in self.connected_clients:
                        self.ble.gatts_notify(client, self.status_handle)

                    print(f"[CONFIG] Node provisioned as: {node_config['node_id']}")
                    # FIX: set flag instead of calling blink_led() inside IRQ
                    self._do_blink = True

                except Exception as e:
                    print(f"[CONFIG] Error: {e}")
                    self.ble.gatts_write(self.status_handle, b"ERROR:invalid_json")
                    for client in self.connected_clients:
                        self.ble.gatts_notify(client, self.status_handle)

    def _start_advertising(self):
        name_bytes = self.device_name.encode("utf-8")
        adv_packet = bytearray(b'\x02\x01\x06\x03\x03\x02\x1B')
        adv_packet += bytearray([len(name_bytes) + 1, 0x09])
        adv_packet += name_bytes
        self.ble.gap_advertise(ADV_INTERVAL, adv_data=adv_packet)


# --- Main ---
node_config = load_config()
print(f"[BOOT] Current node_id: {node_config['node_id']}")

server = BLECommissioningServer("HDB_FlatNode")

print("\n=== Flat Node Ready for Commissioning ===")
print("Waiting for commissioning tool to connect...\n")

while True:
    if server._do_blink:
        server._do_blink = False
        blink_led()

    # FIX: resume advertising here, not inside the disconnect IRQ
    if server._do_advertise:
        server._do_advertise = False
        server._start_advertising()
        print("[BLE] Advertising again...")

    time.sleep_ms(100)
