#!/usr/bin/env bash
set -euo pipefail

PID_FILE="/tmp/csc2106_bridge.pid"

stopped=0

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "Stopped bridge PID $pid"
    stopped=1
  else
    echo "PID file exists but process is not running: $pid"
  fi
else
  echo "PID file not found"
fi

if [[ "$stopped" -eq 0 ]]; then
  if pkill -f "uvicorn app:app" 2>/dev/null; then
    echo "Stopped bridge via pkill fallback"
  else
    echo "No matching uvicorn process found"
  fi
fi

rm -f "$PID_FILE"
echo "Removed PID file: $PID_FILE"
