#!/usr/bin/env bash
set -euo pipefail

PORT="1883"

lsof_output="$(lsof -nP -iTCP:"$PORT" 2>/dev/null || true)"

echo "Listeners on port $PORT:"
if [[ -n "$lsof_output" ]]; then
  printf '%s\n' "$lsof_output"
else
  echo "Nothing is listening on port $PORT"
fi

echo
if [[ "$lsof_output" == *"mosquitto"* ]] || pgrep -f "[m]osquitto" >/dev/null 2>&1; then
  echo "Mosquitto is running"
else
  echo "Mosquitto is not running"
  echo "Start it with: mosquitto -v"
fi
