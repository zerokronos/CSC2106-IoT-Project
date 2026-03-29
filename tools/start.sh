#!/usr/bin/env bash
set -e

BRIDGE_DIR="$HOME/Desktop/CSC2106Project/Server"
DASHBOARD_DIR="$HOME/Desktop/CSC2106Project/dashboard"

# Track background process IDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo "==> Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    exit 0
}
trap cleanup SIGINT SIGTERM

# --- Bridge setup ---
echo "==> Setting up Python virtual environment..."
cd "$BRIDGE_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -q

export MQTT_HOST=localhost
export MQTT_PORT=1883
export BRIDGE_HTTP_PORT=8000

echo "==> Starting uvicorn (bridge) on port 8000..."
uvicorn app:app --host 0.0.0.0 --port 8000 &
PIDS+=($!)

echo "==> Starting ngrok tunnel on port 8000..."
ngrok http 8000 &
PIDS+=($!)

# --- Dashboard setup ---
echo "==> Starting dashboard on port 5173..."
cd "$DASHBOARD_DIR"
npm run dev -- --host 0.0.0.0 --port 5173 &
PIDS+=($!)

echo ""
echo "==> All services running. Press Ctrl+C to stop."
echo "    Bridge:    http://localhost:8000"
echo "    Dashboard: http://localhost:5173"
echo "    Ngrok UI:  http://localhost:4040"
echo ""

# Wait for all background processes
wait
