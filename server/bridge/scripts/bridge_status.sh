#!/usr/bin/env bash
set -euo pipefail

PID_FILE="/tmp/csc2106_bridge.pid"
LOG_FILE="/tmp/csc2106_bridge.log"
PORT="8000"

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE")"
  echo "PID file: $PID_FILE"
  echo "PID: $pid"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Process status: running"
  else
    echo "Process status: not running (stale PID file)"
  fi
else
  echo "PID file: not found"
fi

echo
echo "Listeners on port $PORT:"
if ! lsof -nP -iTCP:"$PORT"; then
  echo "Nothing is listening on port $PORT"
fi

echo
echo "Last 20 log lines:"
if [[ -f "$LOG_FILE" ]]; then
  tail -n 20 "$LOG_FILE"
else
  echo "Log file not found: $LOG_FILE"
fi
