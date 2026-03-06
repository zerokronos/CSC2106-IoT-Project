#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGROK_PID_FILE="/tmp/csc2106_ngrok.pid"
NGROK_LOG_FILE="/tmp/csc2106_ngrok.log"
NGROK_URL_FILE="/tmp/csc2106_ngrok_url.txt"
NGROK_API_URL="http://127.0.0.1:4040/api/tunnels"
BRIDGE_HTTP_PORT="${BRIDGE_HTTP_PORT:-8000}"
MQTT_PORT="${MQTT_PORT:-1883}"

extract_https_url() {
  python3 - "$BRIDGE_HTTP_PORT" <<'PY'
import json
import sys

bridge_port = sys.argv[1]
try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(1)

for tunnel in payload.get("tunnels", []):
    public_url = str(tunnel.get("public_url", ""))
    addr = str((tunnel.get("config") or {}).get("addr", ""))
    normalized_addr = addr.replace("http://", "").replace("https://", "")
    if public_url.startswith("https://") and normalized_addr.endswith(f":{bridge_port}"):
        print(public_url)
        sys.exit(0)
sys.exit(1)
PY
}

get_ngrok_url() {
  local api_json
  api_json="$(curl -fsS "$NGROK_API_URL" 2>/dev/null || true)"
  if [[ -z "$api_json" ]]; then
    return 1
  fi
  printf '%s' "$api_json" | extract_https_url
}

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok is not installed or not on PATH"
  echo "Install it first, for example on macOS with: brew install ngrok/ngrok/ngrok"
  echo "Then authenticate it once with: ngrok config add-authtoken <YOUR_TOKEN>"
  exit 1
fi

if ! lsof -nP -iTCP:"$MQTT_PORT" | grep -q LISTEN; then
  echo "Mosquitto is not listening on port $MQTT_PORT"
  echo "Start it first with: mosquitto -v"
  echo "You can also check with: ./scripts/mqtt_status.sh"
  exit 1
fi

"$SCRIPT_DIR/bridge_start.sh"

ngrok_url="$(get_ngrok_url || true)"
if [[ -n "$ngrok_url" ]]; then
  echo "Reusing existing ngrok tunnel: $ngrok_url"
else
  if [[ -f "$NGROK_PID_FILE" ]]; then
    existing_pid="$(cat "$NGROK_PID_FILE")"
    if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
      echo "ngrok PID file exists for PID $existing_pid, but no HTTPS tunnel was found yet"
    else
      rm -f "$NGROK_PID_FILE"
    fi
  fi

  if [[ ! -f "$NGROK_PID_FILE" ]]; then
    nohup ngrok http "$BRIDGE_HTTP_PORT" >"$NGROK_LOG_FILE" 2>&1 &
    ngrok_pid=$!
    echo "$ngrok_pid" > "$NGROK_PID_FILE"
    echo "Started ngrok with PID $ngrok_pid"
  fi

  for _ in $(seq 1 20); do
    sleep 1
    ngrok_url="$(get_ngrok_url || true)"
    if [[ -n "$ngrok_url" ]]; then
      break
    fi

    if [[ -f "$NGROK_PID_FILE" ]]; then
      ngrok_pid="$(cat "$NGROK_PID_FILE")"
      if [[ -n "$ngrok_pid" ]] && ! kill -0 "$ngrok_pid" 2>/dev/null; then
        echo "ngrok exited before the local API became ready"
        echo "Check the log: $NGROK_LOG_FILE"
        rm -f "$NGROK_PID_FILE"
        exit 1
      fi
    fi
  done
fi

if [[ -z "$ngrok_url" ]]; then
  echo "Could not determine ngrok HTTPS URL from $NGROK_API_URL"
  echo "Check the log: $NGROK_LOG_FILE"
  exit 1
fi

printf '%s\n' "$ngrok_url" > "$NGROK_URL_FILE"
endpoint_url="${ngrok_url%/}/ttn/uplink"

echo "ngrok HTTPS URL: $ngrok_url"
echo "Saved URL to: $NGROK_URL_FILE"
echo
echo "TTN Custom Webhook settings:"
echo "- Webhook format: JSON"
echo "- Base URL = $endpoint_url"
echo "- Enable Uplink message event"
echo
echo "Tail logs:"
echo "- tail -f /tmp/csc2106_bridge.log"
echo "- tail -f $NGROK_LOG_FILE"
echo
echo "Stop cleanly:"
echo "- ./scripts/bridge_stop.sh"
echo "- [[ -f $NGROK_PID_FILE ]] && kill \"\$(cat $NGROK_PID_FILE)\" 2>/dev/null || true"
echo "- rm -f $NGROK_PID_FILE $NGROK_URL_FILE"
