WISGATE + TTN + NGROK + BRIDGE TEST RUNBOOK (TRAVIS-PROOF)
Version: v1.0
Last updated: 2026-03-06

=====================================================================
0) Goal
=====================================================================

Verify the full LoRaWAN fallback chain end-to-end:

  Maker UNO (LoRaWAN OTAA uplink)
    -> WisGate (RAK7268CV2) gateway
    -> TTN (The Things Stack) receives uplink
    -> TTN Custom Webhook sends uplink to public URL
    -> ngrok forwards public URL to local bridge
    -> local bridge POST /ttn/uplink republishes into MQTT contract
    -> dashboard (SSE) displays node updates and alerts with mode=lorawan

Success means ALL of these are true:
  A) TTN Device Live Data shows uplinks from your end device.
  B) /tmp/csc2106_bridge.log shows POST /ttn/uplink 200 OK from a non-local IP.
  C) Dashboard shows node/alert updates with mode=lorawan.

=====================================================================
1) Prerequisites
=====================================================================

Hardware
  - RAK7268CV2 WisGate gateway with LoRa antenna attached
  - Maker UNO Rev1.1 + Cytron LoRa-RFM shield with antenna attached
  - USB cable for UNO

Accounts / Access
  - Access to the TTN Application used for the project
  - Access to the TTN Gateway entry for the WisGate

Software / Tools (Mac)
  - ngrok installed and authtoken configured (one-time)
  - mosquitto installed
  - Python virtualenv for the bridge already created at:
      server/bridge/.venv

Repo
  - Latest code that includes server/bridge scripts:
      bridge_start.sh, mqtt_status.sh, ttn_ngrok_start.sh, ttn_webhook_verify.sh
  - Bridge runs on localhost:8000
  - MQTT broker runs on localhost:1883

=====================================================================
2) Critical settings (do not improvise)
=====================================================================

Frequency plan MUST be consistent everywhere:
  - AU915 (Australia 915–928 MHz), FSB2

TTN Device activation:
  - OTAA
  - LoRaWAN version: 1.0.2
  - Regional Parameters: RP001 1.0.2 revision B (or closest 1.0.2)

UNO LMIC requirements:
  - AU915 enabled in LMIC library config
  - LMIC_selectSubBand(1) after LMIC_reset()
    (FSB2 behavior in this project)

=====================================================================
3) Part A — Start local system (MQTT + bridge + dashboard)
=====================================================================

All commands below assume you are in:
  /Users/<you>/.../CSC2106-IoT-Project/server/bridge

A1) Confirm MQTT broker status
  ./scripts/mqtt_status.sh

Expected:
  - shows something listening on 1883
  - ideally shows mosquitto

If broker is NOT running, start it in a separate terminal:
  mosquitto -v

Note:
  If you see "Address already in use", mosquitto is already running. That is fine.

A2) Start bridge in stable detached mode
  ./scripts/bridge_start.sh
  ./scripts/bridge_status.sh

Expected:
  - bridge pid file exists: /tmp/csc2106_bridge.pid
  - port 8000 is listening
  - logs exist: /tmp/csc2106_bridge.log

A3) Open dashboard
  http://127.0.0.1:8000/dashboard

A4) Tail bridge logs (use another terminal)
  tail -f /tmp/csc2106_bridge.log

=====================================================================
4) Part B — Start ngrok and verify public webhook path BEFORE TTN
=====================================================================

B1) Start ngrok helper (automates bridge start and ngrok tunnel)
  ./scripts/ttn_ngrok_start.sh

Expected output includes a line like:
  Base URL = https://<something>.ngrok-free.dev/ttn/uplink

Important:
  Copy EXACTLY what it prints including the domain suffix.
  (Common failure is mixing .dev vs .app.)

B2) Verify ngrok -> bridge works (no TTN yet)
  ./scripts/ttn_webhook_verify.sh

Expected:
  - HTTP 200
  - dashboard shows an event with reason "ngrok-verify" (or similar)
  - bridge log shows POST /ttn/uplink 200 OK

If B2 fails:
  Stop here. Fix ngrok/bridge first before configuring TTN.

Useful logs:
  tail -f /tmp/csc2106_bridge.log
  tail -f /tmp/csc2106_ngrok.log

=====================================================================
5) Part C — Configure TTN Custom Webhook (TTN -> ngrok -> bridge)
=====================================================================

In TTN Console (The Things Stack):
  Application -> Integrations -> Webhooks -> Add webhook -> Custom webhook

Set these fields:
  - Webhook format: JSON
  - Base URL: paste EXACTLY the Base URL printed by ttn_ngrok_start.sh
      It MUST end with /ttn/uplink
  - Enabled event types:
      Enable "Uplink message" (must be ON)

Save the webhook.

Post-save sanity checks:
  - There should be a webhook "Events" / "Deliveries" view (UI varies)
  - After uplinks happen, you should see delivery attempts

=====================================================================
6) Part D — Confirm WisGate gateway is online and correct
=====================================================================

D1) TTN gateway checks
  TTN Console -> Gateways -> <WisGate gateway>

Confirm:
  - Status: connected / last seen recently
  - Frequency plan: AU915 FSB2 (must match project)
  - Live data shows periodic gateway status messages

D2) Optional: WisGate local UI
  If you can access WisGate web UI:
  - Confirm region is AU915
  - Confirm packet forwarder / TTN connection is correct
  TTN is still the source of truth.

=====================================================================
7) Part E — UNO end device setup and sending uplinks
=====================================================================

E1) Use the repo template sketch (no secrets committed)
  firmware/node/lorawan_uno_template/lorawan_uno_template.ino

You MUST fill:
  - DEVEUI (LMIC uses LSB-first, reverse from TTN display)
  - APPKEY (copy as-is from TTN, DO NOT reverse)

JoinEUI:
  - stays 0000000000000000 (matches template)

E2) Register end device in TTN
  Application -> End devices -> Add end device

Set:
  - OTAA
  - JoinEUI = 0000000000000000
  - DevEUI = must match the device you are using (DO NOT typo last byte)
  - Frequency plan = AU915 FSB2
  - LoRaWAN version = 1.0.2
  - RP version = 1.0.2 rev B

Copy AppKey from TTN into the sketch.

E3) Confirm UNO join and uplink behavior
In Arduino Serial Monitor (9600 baud, newline):
  - Telemetry:
      TEL 2 285 2
  - Alert:
      ALERT 2 350 90 2
  - Heartbeat:
      HB 2

Expected on Arduino:
  - EV_JOINED (once) then periodic EV_TXSTART / EV_TXCOMPLETE
  - "Queued uplink ..." lines after TEL/ALERT/HB

Expected on TTN Device Live Data:
  - Uplink entries
  - FPort 1
  - frm_payload present
  - Payload bytes match the 7-byte format

=====================================================================
8) Part F — End-to-end success checklist
=====================================================================

You are done when ALL three are true:

F1) TTN Device Live Data
  - Uplinks are arriving for the end device

F2) Local bridge log shows TTN delivering
  - /tmp/csc2106_bridge.log contains:
      POST /ttn/uplink ... 200 OK
    from a non-local IP (not 127.0.0.1)

F3) Dashboard shows LoRaWAN mode
  - Node row shows mode=lorawan (especially during active alert)
  - Alerts feed shows the reason you sent (e.g., ngrok_test)

Optional: confirm MQTT publish stream:
  mosquitto_sub -h localhost -t 'csc2106/v0/#' -v -C 3

=====================================================================
9) Common failure modes (fast triage)
=====================================================================

9.1 TTN sees uplinks but bridge log shows nothing
  - TTN webhook Base URL wrong
    - common: copied .app but tunnel is .dev
  - ngrok tunnel restarted, URL changed, TTN webhook not updated
  - TTN webhook event type not enabled (Uplink message must be enabled)

9.2 Bridge receives POST but dashboard doesn't update
  - Refresh dashboard (SSE reconnect)
  - Check MQTT is running and bridge can publish
  - Tail /tmp/csc2106_bridge.log for errors
  - Verify MQTT stream:
      mosquitto_sub -h localhost -t 'csc2106/v0/#' -v -C 3

9.3 Gateway receives nothing (no uplinks)
  - Wrong frequency plan on gateway/device (must be AU915 FSB2)
  - Antenna loose
  - Device not joined due to wrong DevEUI/AppKey

9.4 Device won't join (no JoinAccept)
  - DevEUI mismatch in TTN (very common)
  - AppKey mismatch (one hex digit wrong breaks join)
  - Subband mismatch (ensure LMIC_selectSubBand(1) after reset)
  - If you change device identity repeatedly, reset DevNonces in TTN

=====================================================================
10) Evidence to capture (for report and demo)
=====================================================================

Save under docs/figures/ (suggested filenames):

  - docs/figures/ttn-live-data-lorawan-fallback.png
      Screenshot: TTN Device Live Data showing uplink payload and FPort

  - docs/figures/bridge-log-ttn-uplink-200.txt
      Copy/paste: relevant /tmp/csc2106_bridge.log lines showing POST /ttn/uplink 200 OK

  - docs/figures/dashboard-lorawan-alert.png
      Screenshot: dashboard showing mode=lorawan and an alert reason

Do NOT capture or share:
  - AppKey
  - session keys (AppSKey/NwkSKey)
  - ngrok authtoken

=====================================================================
11) Stop / Cleanup
=====================================================================

Stop bridge:
  ./scripts/bridge_stop.sh

Stop ngrok (if PID exists):
  [[ -f /tmp/csc2106_ngrok.pid ]] && kill "$(cat /tmp/csc2106_ngrok.pid)" 2>/dev/null || true
  rm -f /tmp/csc2106_ngrok.pid /tmp/csc2106_ngrok_url.txt

Logs remain at:
  /tmp/csc2106_bridge.log
  /tmp/csc2106_ngrok.log

END OF RUNBOOK
