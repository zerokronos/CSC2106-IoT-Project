# ble_client.py (Pico W 2 - Commissioning Tool / Client)
# Based on working lab ble_client.py
# Modified for CSC2106 Group 6 — HDB Fire Monitoring System
#
# This Pico acts as the technician's commissioning tool.
# It scans for a flat node, connects, and pushes config automatically.
# Edit CONFIG_TO_SEND below before flashing for each flat node.

import bluetooth
import time
import machine
import json
from micropython import const

# ----------------------------------------------------------------
# EDIT THIS before flashing — one config per flat node
# ----------------------------------------------------------------
CONFIG_TO_SEND = {
    "node_id": "flat01",
    "temp_warn": 45,
    "temp_alarm": 60,
    "smoke_warn": 500,
    "smoke_alarm": 800,
    "telemetry_interval": 2
}
# ----------------------------------------------------------------

TARGET_DEVICE = "HDB_FlatNode"

# --- UUIDs (must match server) ---
SERVICE_UUID     = bluetooth.UUID(0x1B02)
CONFIG_CHAR_UUID = bluetooth.UUID(0x1B00)
STATUS_CHAR_UUID = bluetooth.UUID(0x1B01)

# --- BLE Event codes ---
SCAN_RESULT          = const(5)
SCAN_DONE            = const(6)
PERIPHERAL_CONNECT   = const(7)
PERIPHERAL_DISCONNECT= const(8)
GATTC_SERVICE_RESULT = const(9)
GATTC_SERVICE_DONE   = const(10)
GATTC_CHAR_RESULT    = const(11)
GATTC_CHAR_DONE      = const(12)
GATTC_READ_RESULT    = const(15)
GATTC_WRITE_DONE     = const(17)
GATTC_NOTIFY         = const(18)
MTU_EXCHANGED        = const(21)

# --- Hardware ---
status_led = machine.Pin("LED", machine.Pin.OUT)

def blink_led(times=5, delay=0.15):
    for _ in range(times):
        status_led.on()
        time.sleep(delay)
        status_led.off()
        time.sleep(delay)


# --- BLE Client ---
class BLECommissioningClient:

    def __init__(self):
        self.ble = bluetooth.BLE()
        self.ble.active(True)
        # FIX: request 256-byte MTU so the 100-byte JSON fits in one write (MTU-3 = 253)
        self.ble.config(mtu=256)
        self.ble.irq(self._handle_event)
        self._reset_state()

    def _reset_state(self):
        self.server_addr_type  = None
        self.server_addr       = None
        self.connection_handle = None
        self.service_start     = None
        self.service_end       = None
        self.config_handle     = None
        self.status_handle     = None
        self.is_connected      = False
        # FIX: track two-phase write: first CCCD subscription, then config
        self._subscribed       = False
        self.config_sent       = False
        # FIX: flags for deferred actions (must not block inside IRQ)
        self._do_blink         = False
        self._do_disconnect    = None  # conn_handle to disconnect, or None

    def _handle_event(self, event, data):

        # Found a device during scan
        if event == SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            if TARGET_DEVICE.encode() in bytes(adv_data):
                self.server_addr_type = addr_type
                self.server_addr = bytes(addr)
                print(f"[SCAN] Found '{TARGET_DEVICE}' (RSSI={rssi}). Connecting...")
                self.ble.gap_scan(None)  # Stop scan

        # Scan finished
        elif event == SCAN_DONE:
            if self.server_addr:
                self.ble.gap_connect(self.server_addr_type, self.server_addr)
            else:
                print("[SCAN] Not found. Retrying...")
                self.start_scan()

        # Connected to flat node — exchange MTU before anything else
        elif event == PERIPHERAL_CONNECT:
            conn_handle, addr_type, addr = data
            self.connection_handle = conn_handle
            self.is_connected = True
            status_led.on()
            print("[BLE] Connected. Negotiating MTU...")
            self.ble.gattc_exchange_mtu(conn_handle)

        # MTU negotiation complete — now safe to discover services
        elif event == MTU_EXCHANGED:
            conn_handle, mtu = data
            print(f"[BLE] MTU set to {mtu}. Discovering services...")
            self.ble.gattc_discover_services(conn_handle)

        # Disconnected
        elif event == PERIPHERAL_DISCONNECT:
            print("[BLE] Disconnected.")
            status_led.off()
            self._reset_state()

        # Found a service
        elif event == GATTC_SERVICE_RESULT:
            conn_handle, start_handle, end_handle, uuid = data
            if uuid == SERVICE_UUID:
                self.service_start = start_handle
                self.service_end   = end_handle
                print(f"[DISC] Commissioning service found.")

        # Service discovery done — discover characteristics
        elif event == GATTC_SERVICE_DONE:
            if self.service_start and self.service_end:
                print("[DISC] Discovering characteristics...")
                self.ble.gattc_discover_characteristics(
                    self.connection_handle,
                    self.service_start,
                    self.service_end
                )

        # Found a characteristic
        elif event == GATTC_CHAR_RESULT:
            conn_handle, def_handle, value_handle, properties, uuid = data
            if uuid == CONFIG_CHAR_UUID:
                self.config_handle = value_handle
                print("[DISC] Found config characteristic.")
            elif uuid == STATUS_CHAR_UUID:
                self.status_handle = value_handle
                print("[DISC] Found status characteristic.")

        # Characteristic discovery done — subscribe to notifications first
        elif event == GATTC_CHAR_DONE:
            if self.config_handle and self.status_handle and not self._subscribed:
                self._subscribe_notifications()

        # Write acknowledged
        elif event == GATTC_WRITE_DONE:
            conn_handle, value_handle, status = data
            if status != 0:
                print(f"[BLE] Write failed (status={status})")
                return
            # FIX: two-phase write — CCCD first, then config
            if not self._subscribed:
                self._subscribed = True
                print("[BLE] Notifications enabled. Sending config...")
                self._send_config()
            elif not self.config_sent:
                self.config_sent = True
                print("[BLE] Config sent. Waiting for confirmation...")

        # Notification from server (confirmation)
        elif event == GATTC_NOTIFY:
            conn_handle, value_handle, notify_data = data
            if value_handle == self.status_handle:
                try:
                    response = bytes(notify_data).decode("utf-8")
                    print(f"\n[CONFIRM] Server response: {response}")

                    if response.startswith("OK:"):
                        node_id = response.split(":")[1]
                        print(f"[SUCCESS] Node provisioned as '{node_id}'")
                        # FIX: set flags instead of calling blink/sleep inside IRQ
                        self._do_blink = True
                        self._do_disconnect = conn_handle
                    else:
                        print("[ERROR] Provisioning failed.")
                        self._do_disconnect = conn_handle

                except Exception as e:
                    print(f"[NOTIFY] Error: {e}")

    def _subscribe_notifications(self):
        # CCCD is always at status_handle + 1 in MicroPython's GATT table
        cccd_handle = self.status_handle + 1
        print("[SUB] Enabling notifications on status characteristic...")
        self.ble.gattc_write(self.connection_handle, cccd_handle, b'\x01\x00', 1)

    def _send_config(self):
        payload = json.dumps(CONFIG_TO_SEND).encode("utf-8")
        print(f"\n[SEND] Pushing config: {CONFIG_TO_SEND}")
        self.ble.gattc_write(self.connection_handle, self.config_handle, payload, 1)

    def start_scan(self):
        print(f"[SCAN] Scanning for '{TARGET_DEVICE}'...")
        self.ble.gap_scan(0, 30000, 30000)


# --- Main ---
print("\n=== HDB Commissioning Tool ===")
print(f"Config to push:")
for k, v in CONFIG_TO_SEND.items():
    print(f"  {k}: {v}")
print()

client = BLECommissioningClient()
client.start_scan()

print("Scanning... will connect and push config automatically.\n")

while True:
    # FIX: deferred actions that must not run inside the BLE IRQ handler
    if client._do_blink:
        client._do_blink = False
        blink_led()

    if client._do_disconnect is not None:
        handle = client._do_disconnect
        client._do_disconnect = None
        time.sleep(1)  # brief pause before disconnect — safe here in main loop
        client.ble.gap_disconnect(handle)

    time.sleep_ms(50)
