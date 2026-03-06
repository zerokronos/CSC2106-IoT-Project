#!/usr/bin/env bash
set -euo pipefail

BRIDGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$BRIDGE_DIR/.venv"
LOG_FILE="/tmp/csc2106_bridge.log"
PID_FILE="/tmp/csc2106_bridge.pid"

cd "$BRIDGE_DIR"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtual environment not found at $VENV_DIR"
  echo "Create it first with: cd $BRIDGE_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE")"
  if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "Bridge is already running with PID $existing_pid"
    echo "URL: http://127.0.0.1:${BRIDGE_HTTP_PORT:-8000}/dashboard"
    echo "Log: $LOG_FILE"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

export MQTT_HOST="${MQTT_HOST:-localhost}"
export MQTT_PORT="${MQTT_PORT:-1883}"
export BRIDGE_HTTP_PORT="${BRIDGE_HTTP_PORT:-8000}"

nohup uvicorn app:app --host 0.0.0.0 --port "$BRIDGE_HTTP_PORT" >"$LOG_FILE" 2>&1 &
bridge_pid=$!
echo "$bridge_pid" > "$PID_FILE"

sleep 1
if ! kill -0 "$bridge_pid" 2>/dev/null; then
  echo "Bridge failed to stay up. Check the log: $LOG_FILE"
  rm -f "$PID_FILE"
  exit 1
fi

echo "Bridge started with PID $bridge_pid"
echo "URL: http://127.0.0.1:${BRIDGE_HTTP_PORT}/dashboard"
echo "Log: $LOG_FILE"
echo "PID file: $PID_FILE"
