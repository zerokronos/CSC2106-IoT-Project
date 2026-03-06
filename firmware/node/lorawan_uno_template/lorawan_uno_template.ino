#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>

// =====================================================
// TTN OTAA IDs / Keys
// =====================================================
// JoinEUI (AppEUI) in LSB order.
// TTN JoinEUI: 0000000000000000
// This stays zeroed because it maps to JoinEUI=0000000000000000.
static const u1_t PROGMEM APPEUI[8] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};
void os_getArtEui(u1_t* buf) { memcpy_P(buf, APPEUI, 8); }

// DevEUI in LSB order.
// FILL FROM TTN DevEUI displayed MSB-first; LMIC expects LSB-first reversed bytes.
static const u1_t PROGMEM DEVEUI[8] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};
void os_getDevEui(u1_t* buf) { memcpy_P(buf, DEVEUI, 8); }

// AppKey in MSB order.
// FILL FROM TTN APPKEY (MSB order, do not reverse). Do not commit keys.
static const u1_t PROGMEM APPKEY[16] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};
void os_getDevKey(u1_t* buf) { memcpy_P(buf, APPKEY, 16); }

// =====================================================
// Pin mapping for Cytron LoRa-RFM shield on UNO
// NSS=10, RST=7, DIO0=2, DIO1=5, DIO2=6
// =====================================================
const lmic_pinmap lmic_pins = {
  .nss = 10,
  .rxtx = LMIC_UNUSED_PIN,
  .rst = 7,
  .dio = { 2, 5, 6 }
};

// =====================================================
// Payload format expected by your bridge
// byte0: node_id (1..255)
// byte1: msg_type (1=telemetry,2=heartbeat,3=alert)
// byte2-3: temp_x10 (uint16 BE)
// byte4-5: smoke_x100 (uint16 BE)
// byte6: severity (0 none, 1 warn, 2 alarm; used when msg_type=3)
// =====================================================
enum MsgType : uint8_t {
  MSG_TELEMETRY = 1,
  MSG_HEARTBEAT = 2,
  MSG_ALERT     = 3
};

enum Severity : uint8_t {
  SEV_NONE  = 0,
  SEV_WARN  = 1,
  SEV_ALARM = 2
};

static bool joined = false;

// Default demo values
static uint8_t  default_node_id = 2;   // flat02
static uint16_t demo_temp_x10   = 285; // 28.5C
static uint16_t demo_smoke_x100 = 2;   // 0.02

static void pack_u16_be(uint8_t* buf, uint16_t v) {
  buf[0] = (uint8_t)((v >> 8) & 0xFF);
  buf[1] = (uint8_t)(v & 0xFF);
}

static void queue_uplink(uint8_t node_id, uint8_t msg_type,
                         uint16_t temp_x10, uint16_t smoke_x100,
                         uint8_t severity) {
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

  Serial.print(F("Queued uplink: node="));
  Serial.print(node_id);
  Serial.print(F(" type="));
  Serial.print(msg_type);
  Serial.print(F(" temp_x10="));
  Serial.print(temp_x10);
  Serial.print(F(" smoke_x100="));
  Serial.print(smoke_x100);
  Serial.print(F(" sev="));
  Serial.println(severity);
}

// Serial commands:
// TEL <node_id> <temp_x10> <smoke_x100>
// ALERT <node_id> <temp_x10> <smoke_x100> <severity0-2>
// HB <node_id>
static void handle_serial_command(const String& line) {
  String s = line;
  s.trim();
  if (s.length() == 0) return;

  int sp = s.indexOf(' ');
  String cmd = (sp == -1) ? s : s.substring(0, sp);
  cmd.toUpperCase();

  auto readIntAt = [&](int& idx) -> long {
    while (idx < (int)s.length() && s[idx] == ' ') idx++;
    int start = idx;
    while (idx < (int)s.length() && s[idx] != ' ') idx++;
    if (start == idx) return -1;
    return s.substring(start, idx).toInt();
  };

  int idx = (sp == -1) ? s.length() : sp + 1;

  if (cmd == "TEL") {
    long nid = readIntAt(idx);
    long t   = readIntAt(idx);
    long sm  = readIntAt(idx);
    if (nid < 0 || t < 0 || sm < 0) {
      Serial.println(F("Usage: TEL <node_id> <temp_x10> <smoke_x100>"));
      return;
    }
    queue_uplink((uint8_t)nid, MSG_TELEMETRY, (uint16_t)t, (uint16_t)sm, SEV_NONE);
    return;
  }

  if (cmd == "ALERT") {
    long nid = readIntAt(idx);
    long t   = readIntAt(idx);
    long sm  = readIntAt(idx);
    long sev = readIntAt(idx);
    if (nid < 0 || t < 0 || sm < 0 || sev < 0) {
      Serial.println(F("Usage: ALERT <node_id> <temp_x10> <smoke_x100> <severity0-2>"));
      return;
    }
    if (sev > 2) sev = 2;
    queue_uplink((uint8_t)nid, MSG_ALERT, (uint16_t)t, (uint16_t)sm, (uint8_t)sev);
    return;
  }

  if (cmd == "HB") {
    long nid = readIntAt(idx);
    if (nid < 0) {
      Serial.println(F("Usage: HB <node_id>"));
      return;
    }
    queue_uplink((uint8_t)nid, MSG_HEARTBEAT, demo_temp_x10, demo_smoke_x100, SEV_NONE);
    return;
  }

  Serial.println(F("Unknown cmd. Use TEL/ALERT/HB"));
}

void onEvent(ev_t ev) {
  Serial.print(os_getTime());
  Serial.print(F(": "));

  switch (ev) {
    case EV_JOINING:
      Serial.println(F("EV_JOINING"));
      break;

    case EV_JOINED:
      Serial.println(F("EV_JOINED"));
      joined = true;
      LMIC_setLinkCheckMode(0);
      Serial.println(F("Joined OK"));
      break;

    case EV_JOIN_TXCOMPLETE:
      Serial.println(F("EV_JOIN_TXCOMPLETE: no JoinAccept"));
      break;

    case EV_TXSTART:
      Serial.println(F("EV_TXSTART"));
      break;

    case EV_TXCOMPLETE:
      Serial.println(F("EV_TXCOMPLETE (includes waiting for RX windows)"));
      break;

    default:
      Serial.print(F("Event "));
      Serial.println((unsigned)ev);
      break;
  }
}

String lineBuf;

void setup() {
  Serial.begin(9600);
  while (!Serial) {}

  Serial.println(F("Starting LoRaWAN node (AU915 FSB2)"));

  os_init();
  LMIC_reset();

  // AU915 TTN FSB2 -> subband 1 (channels 8-15)
  LMIC_selectSubBand(1);

  // Force a sane join DR while debugging (comment out if your LMIC build lacks DR_SF10)
  LMIC_setDrTxpow(DR_SF10, 14);

  // Help RX timing on cheap clocks
  LMIC_setClockError(MAX_CLOCK_ERROR * 1 / 100);

  LMIC_startJoining();

  Serial.println(F("Commands: TEL/ALERT/HB"));
  Serial.println(F("Example: TEL 2 285 2"));
}

void loop() {
  os_runloop_once();

  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      handle_serial_command(lineBuf);
      lineBuf = "";
    } else {
      if (lineBuf.length() < 120) lineBuf += c;
    }
  }

  // Optional periodic telemetry once joined
  static unsigned long lastMs = 0;
  if (joined) {
    unsigned long now = millis();
    if (now - lastMs > 15000) {
      lastMs = now;
      queue_uplink(default_node_id, MSG_TELEMETRY, demo_temp_x10, demo_smoke_x100, SEV_NONE);
    }
  }
}
