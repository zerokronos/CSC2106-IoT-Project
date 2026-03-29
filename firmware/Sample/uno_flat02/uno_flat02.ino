#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>

// =====================================================
// TTN OTAA IDs / Keys (FOR TRAVIS NEO)
// =====================================================

// APPEUI: 0000000000000000 (LSB)
static const u1_t PROGMEM APPEUI[8] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
void os_getArtEui(u1_t* buf) { memcpy_P(buf, APPEUI, 8); }

// DEVEUI: 70B3D57ED00768FB (Reversed to LSB for LMIC)
static const u1_t PROGMEM DEVEUI[8] = { 0xFB, 0x68, 0x07, 0xD0, 0x7E, 0xD5, 0xB3, 0x70 };
void os_getDevEui(u1_t* buf) { memcpy_P(buf, DEVEUI, 8); }

// APPKEY: B30C1ABA8A44D909C0FDF3066AC7A3FF (MSB - No change)
static const u1_t PROGMEM APPKEY[16] = {
  0xB3, 0x0C, 0x1A, 0xBA, 0x8A, 0x44, 0xD9, 0x09,
  0xC0, 0xFD, 0xF3, 0x06, 0x6A, 0xC7, 0xA3, 0xFF
};
void os_getDevKey(u1_t* buf) { memcpy_P(buf, APPKEY, 16); }

// =====================================================
// Pin mapping for Cytron LoRa-RFM shield on Maker Uno
// =====================================================
const lmic_pinmap lmic_pins = {
  .nss = 10,
  .rxtx = LMIC_UNUSED_PIN,
  .rst = 7,
  .dio = { 2, 5, 6 } // DIO0=D2, DIO1=D5, DIO2=D6
};

static bool joined = false;
static uint8_t default_node_id = 2; 
static bool lora_mode_enabled = false;

// Simulated sensor data stream sent to Pico W over UART.
static const uint16_t SIM_TEMP_X10[] = { 248, 252, 259, 265, 272, 280, 288, 295 };
static const uint16_t SIM_SMOKE_X100[] = { 3, 4, 5, 7, 10, 15, 22, 30 };
static uint8_t sim_idx = 0;

// Helper to pack big-endian 16-bit
static void pack_u16_be(uint8_t* buf, uint16_t v) {
  buf[0] = (uint8_t)((v >> 8) & 0xFF);
  buf[1] = (uint8_t)(v & 0xFF);
}

void queue_uplink(uint8_t node_id, uint8_t msg_type, uint16_t temp_x10, uint16_t smoke_x100, uint8_t severity) {
  if (LMIC.opmode & OP_TXRXPEND) {
    Serial.println(F("OP_TXRXPEND, not sending"));
    return;
  }
  uint8_t payload[7];
  payload[0] = node_id;
  payload[1] = msg_type;
  pack_u16_be(&payload[2], temp_x10);
  pack_u16_be(&payload[4], smoke_x100);
  payload[6] = severity;

  LMIC_setTxData2(1, payload, sizeof(payload), 0);
  Serial.println(F("Uplink Queued. Check TTN Console."));
}

static void emit_uart_telemetry(uint8_t node_id, uint16_t temp_x10, uint16_t smoke_x100, uint8_t fire) {
  Serial.print(F("{\"node_id\":"));
  Serial.print(node_id);
  Serial.print(F(",\"msg_type\":1,\"temp\":"));
  Serial.print(temp_x10 / 10);
  Serial.print('.');
  Serial.print(temp_x10 % 10);
  Serial.print(F(",\"smoke\":"));
  Serial.print(smoke_x100 / 100);
  Serial.print('.');
  uint8_t smoke_frac = smoke_x100 % 100;
  if (smoke_frac < 10) {
    Serial.print('0');
  }
  Serial.print(smoke_frac);
  Serial.print(F(",\"fire\":"));
  Serial.print(fire);
  Serial.println(F("}"));
}

static void handle_pico_commands() {
  if (!Serial.available()) {
    return;
  }

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "LORA_ON" || cmd == "LORA_ENABLE") {
    lora_mode_enabled = true;
    Serial.println(F("{\"ack\":\"LORA_ON\"}"));
  } else if (cmd == "LORA_OFF" || cmd == "LORA_DISABLE") {
    lora_mode_enabled = false;
    Serial.println(F("{\"ack\":\"LORA_OFF\"}"));
  }
}

void onEvent(ev_t ev) {
  Serial.print(os_getTime());
  Serial.print(F(": "));
  switch (ev) {
    case EV_JOINING: Serial.println(F("EV_JOINING...")); break;
    case EV_JOINED:
      Serial.println(F("EV_JOINED! SUCCESS!"));
      joined = true;
      LMIC_setLinkCheckMode(0);
      break;
    case EV_JOIN_TXCOMPLETE: 
      Serial.println(F("EV_JOIN_TXCOMPLETE: No JoinAccept yet.")); 
      break;
    case EV_TXSTART: 
      Serial.println(F("EV_TXSTART (Check D2 LED on Maker Uno)")); 
      break;
    case EV_TXCOMPLETE: 
      Serial.println(F("EV_TXCOMPLETE (Uplink Finished)")); 
      break;
    default:
      Serial.print(F("Event "));
      Serial.println((unsigned)ev);
      break;
  }
}

#define FIRE_SIM_PIN    9   // INPUT_PULLUP — reads LOW when fire active
#define FIRE_SIM_GND    3   // OUTPUT LOW — connect to pin 9 to trigger fire

void setup() {
  Serial.begin(9600);
  while (!Serial) {}

  pinMode(FIRE_SIM_PIN, INPUT_PULLUP);
  pinMode(FIRE_SIM_GND, OUTPUT);
  digitalWrite(FIRE_SIM_GND, LOW);
  Serial.println(F("=== Starting LoRaWAN Node (AU915 FSB2) ==="));

  os_init();
  LMIC_reset();
  LMIC_selectSubBand(1);

  // --- FIX 1: AGGRESSIVE SUB-BAND FILTERING (AU915 FSB2) ---
  for (int i = 0; i < 72; i++) {
    if (i < 8 || i > 15) {
      LMIC_disableChannel(i);
    }
  }

  // --- FIX 2: EXTREME CLOCK TOLERANCE (Fixes Event 8) ---
  // Vital for Maker Uno's inaccurate crystal
  LMIC_setClockError(MAX_CLOCK_ERROR * 30 / 100);

  // --- FIX 3: SANE JOIN DATA RATE ---
  LMIC_setDrTxpow(DR_SF10, 14);

  LMIC_startJoining();
}

void loop() {
  os_runloop_once();
  handle_pico_commands();

  bool fire_sim = (digitalRead(FIRE_SIM_PIN) == LOW);

  // Produce simulated telemetry for Pico W every 3 seconds while in WiFi path.
  static unsigned long lastMs = 0;
  if (!lora_mode_enabled && (millis() - lastMs > 3000)) {
    lastMs = millis();
    uint16_t t, s;
    uint8_t fire_flag;
    if (fire_sim) {
      t = 655; s = 11000; fire_flag = 1;
    } else {
      t = SIM_TEMP_X10[sim_idx]; s = SIM_SMOKE_X100[sim_idx]; fire_flag = 0;
      sim_idx = (uint8_t)((sim_idx + 1) % (sizeof(SIM_TEMP_X10) / sizeof(SIM_TEMP_X10[0])));
    }
    emit_uart_telemetry(default_node_id, t, s, fire_flag);
  }

  // During failover, send directly over LoRa every 30 seconds once joined.
  static unsigned long lastLoraMs = 0;
  if (lora_mode_enabled && joined && (millis() - lastLoraMs > 30000)) {
    lastLoraMs = millis();
    uint16_t t, s;
    uint8_t fire_flag;
    if (fire_sim) {
      t = 655; s = 11000; fire_flag = 1;
    } else {
      t = SIM_TEMP_X10[sim_idx]; s = SIM_SMOKE_X100[sim_idx]; fire_flag = 0;
      sim_idx = (uint8_t)((sim_idx + 1) % (sizeof(SIM_TEMP_X10) / sizeof(SIM_TEMP_X10[0])));
    }
    queue_uplink(default_node_id, 1, t, s, fire_flag);
  }
}
