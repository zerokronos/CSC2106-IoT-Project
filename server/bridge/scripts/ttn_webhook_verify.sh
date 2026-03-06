#!/usr/bin/env bash
set -euo pipefail

NGROK_URL_FILE="/tmp/csc2106_ngrok_url.txt"
BRIDGE_LOG_FILE="/tmp/csc2106_bridge.log"
RESPONSE_FILE="/tmp/csc2106_ttn_verify_response.json"

if [[ ! -f "$NGROK_URL_FILE" ]]; then
  echo "ngrok URL file not found: $NGROK_URL_FILE"
  echo "Run ./scripts/ttn_ngrok_start.sh first"
  exit 1
fi

ngrok_url="$(tr -d '[:space:]' < "$NGROK_URL_FILE")"
if [[ -z "$ngrok_url" ]]; then
  echo "ngrok URL file is empty: $NGROK_URL_FILE"
  echo "Run ./scripts/ttn_ngrok_start.sh again"
  exit 1
fi

endpoint_url="${ngrok_url%/}/ttn/uplink"
timestamp="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
payload=$(cat <<JSON
{
  "node_id": "flat01",
  "msg_type": "telemetry",
  "temp_c": 28.4,
  "smoke": 0.02,
  "severity": "none",
  "reason": "ngrok-verify",
  "received_at": "$timestamp"
}
JSON
)

http_code="$(curl -sS -o "$RESPONSE_FILE" -w '%{http_code}' \
  -X POST "$endpoint_url" \
  -H 'Content-Type: application/json' \
  --data "$payload")"

if [[ "$http_code" != "200" ]]; then
  echo "Verification POST failed with HTTP $http_code"
  echo "Endpoint: $endpoint_url"
  if [[ -f "$RESPONSE_FILE" ]]; then
    echo "Response body:"
    cat "$RESPONSE_FILE"
  fi
  exit 1
fi

echo "Verification POST returned HTTP 200"
echo "Endpoint: $endpoint_url"
echo "Bridge response:"
cat "$RESPONSE_FILE"
echo
echo "Expected success indicators:"
echo "- /tmp/csc2106_bridge.log shows a fresh POST /ttn/uplink request with 200 OK"
echo "- /dashboard shows the new flat01 telemetry event"
echo
echo "Useful commands:"
echo "- tail -f $BRIDGE_LOG_FILE"
echo "- ./scripts/bridge_status.sh"
