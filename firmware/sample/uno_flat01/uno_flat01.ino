#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>

// =====================================================
// TTN OTAA IDs / Keys (FOR TRAVIS NEO)
// =====================================================

// APPEUI: 0000000000000000 (LSB)
static const u1_t PROGMEM APPEUI[8] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
void os_getArtEui(u1_t* buf) { memcpy_P(buf, APPEUI, 8); }

// DEVEUI: 70B3D57ED0076901 (Reversed to LSB for LMIC)
static const u1_t PROGMEM DEVEUI[8] = { 0x01, 0x69, 0x07, 0xD0, 0x7E, 0xD5, 0xB3, 0x70 };
void os_getDevEui(u1_t* buf) { memcpy_P(buf, DEVEUI, 8); }

// APPKEY: AC5F79AEDDCC73CBEF164B6509CECEF0 (MSB - No change)
static const u1_t PROGMEM APPKEY[16] = {
  0xAC, 0x5F, 0x79, 0xAE, 0xDD, 0xCC, 0x73, 0xCB,
  0xEF, 0x16, 0x4B, 0x65, 0x09, 0xCE, 0xCE, 0xF0
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
static uint8_t default_node_id = 1; 
static bool lora_mode_enabled = false;
static unsigned long last_pico_contact_ms = 0;
static const unsigned long PICO_KEEPALIVE_TIMEOUT_MS = 6000;

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
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toUpperCase();

    if (cmd.length() == 0) {
      continue;
    }

    last_pico_contact_ms = millis();

    if (cmd == "PICO_HELLO" || cmd == "PICO_ONLINE") {
      if (lora_mode_enabled) {
        lora_mode_enabled = false;
        Serial.println(F("Pico keepalive restored WiFi mode."));
      }
    } else if (cmd == "LORA_ON" || cmd == "LORA_ENABLE") {
      lora_mode_enabled = true;
      Serial.println(F("{\"ack\":\"LORA_ON\"}"));
    } else if (cmd == "LORA_OFF" || cmd == "LORA_DISABLE") {
      lora_mode_enabled = false;
      Serial.println(F("{\"ack\":\"LORA_OFF\"}"));
    }
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
  last_pico_contact_ms = millis();

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
  static bool prev_fire_sim = false;
  bool fire_just_detected = fire_sim && !prev_fire_sim;

  // WiFi path: normal 3s telemetry; immediate + 500ms repeat on fire.
  static unsigned long lastMs = 0;
  if (!lora_mode_enabled) {
    unsigned long wifi_interval = fire_sim ? 500UL : 3000UL;
    if (fire_just_detected || (millis() - lastMs > wifi_interval)) {
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
  }

  // LoRa path: normal 30s; on fire, re-queue as fast as duty cycle allows
  // (queue_uplink skips if OP_TXRXPEND; LMIC enforces duty cycle internally).
  static unsigned long lastLoraMs = 0;
  if (lora_mode_enabled && joined) {
    unsigned long lora_interval = fire_sim ? 0UL : 30000UL;
    if (fire_just_detected || (millis() - lastLoraMs > lora_interval)) {
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

  prev_fire_sim = fire_sim;

  if (!lora_mode_enabled && (millis() - last_pico_contact_ms > PICO_KEEPALIVE_TIMEOUT_MS)) {
    lora_mode_enabled = true;
    Serial.println(F("Pico keepalive timed out. Switching to LoRa mode."));
  }
}
