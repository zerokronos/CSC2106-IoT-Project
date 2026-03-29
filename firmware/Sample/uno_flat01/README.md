# LoRaWAN UNO Template

This folder contains a sanitized Arduino sketch template for the Maker UNO Rev1.1 with the Cytron LoRa-RFM shield.

## Hardware Assumptions
- Board: Maker UNO Rev1.1
- Shield: Cytron LoRa-RFM
- Pin mapping:
  - `NSS=10`
  - `RST=7`
  - `DIO0=2`
  - `DIO1=5`
  - `DIO2=6`

## TTN Settings
- Region / frequency plan: `AU915 FSB2`
- LoRaWAN version: `1.0.2`
- Regional parameters: `RP001 1.0.2 rev B`
- Activation: `OTAA`

## Keys And IDs
- `APPEUI` stays zeroed in this template because it maps to `JoinEUI=0000000000000000`.
- `APPKEY` must be copied from TTN exactly as shown in TTN byte order.
- Never reverse the AppKey bytes.
- Never commit `AppKey` or session keys.

### DevEUI Conversion For LMIC
TTN shows `DevEUI` in MSB-first display order, but LMIC expects the array in LSB-first order, so reverse the byte order before pasting it into `DEVEUI`.

Example:
- TTN DevEUI: `70B3D57ED0075EC1`
- LMIC array: `{0xC1,0x5E,0x07,0xD0,0x7E,0xD5,0xB3,0x70}`

## AppKey Rule
Copy the TTN `AppKey` bytes into `APPKEY` exactly as shown by TTN.
Do not reverse the bytes.

## Serial Commands
Use the Arduino Serial Monitor at `9600` baud.

Examples:
```text
TEL 2 285 2
ALERT 2 350 90 2
HB 2
```

Command meanings:
- `TEL <node_id> <temp_x10> <smoke_x100>`
- `ALERT <node_id> <temp_x10> <smoke_x100> <severity>`
- `HB <node_id>`

## Payload Format
The sketch sends a fixed 7-byte uplink that matches `server/bridge/ttn_decoder.py`.

- `byte0`: `node_id`
- `byte1`: `msg_type`
  - `1=telemetry`
  - `2=heartbeat`
  - `3=alert`
- `byte2-3`: `temp_x10` as unsigned 16-bit big-endian
- `byte4-5`: `smoke_x100` as unsigned 16-bit big-endian
- `byte6`: `severity`
  - `0=none`
  - `1=warn`
  - `2=alarm`

## Safety
- Never commit real `AppKey` values.
- Never commit session keys.
- Replace placeholders locally before flashing.
