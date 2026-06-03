#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

# Defaults can be overridden when invoking the script.
RELAY_PORT="${RELAY_PORT:-/dev/cu.usbserial-210}"
RECEIVER_HOST="${RECEIVER_HOST:-127.0.0.1}"
RECEIVER_PORT="${RECEIVER_PORT:-5001}"
RECEIVER_URL="http://${RECEIVER_HOST}:${RECEIVER_PORT}/execute"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[ERROR] Missing Python venv at $PYTHON_BIN"
  echo "Create it first or adjust PYTHON_BIN in this script."
  exit 1
fi

cd "$ROOT_DIR"

echo "[*] Starting hardware run"
echo "    Relay port: $RELAY_PORT"
echo "    Receiver:   http://${RECEIVER_HOST}:${RECEIVER_PORT}"

# Clean up any stale receiver process to avoid port conflicts.
pkill -f "utils/receiver.py" >/dev/null 2>&1 || true

# Run receiver in known-good relay mode.
HARDWARE_MODE=relay RELAY_PORT="$RELAY_PORT" "$PYTHON_BIN" utils/receiver.py > /tmp/human_operator_receiver.log 2>&1 &
RECEIVER_PID=$!

cleanup() {
  if kill -0 "$RECEIVER_PID" >/dev/null 2>&1; then
    echo "\n[*] Stopping receiver (pid=$RECEIVER_PID)..."
    kill "$RECEIVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

# Wait for receiver health endpoint.
echo "[*] Waiting for receiver health..."
for i in {1..30}; do
  if curl -sS "http://${RECEIVER_HOST}:${RECEIVER_PORT}/health" >/tmp/human_operator_health.json 2>/dev/null; then
    break
  fi
  sleep 0.5
done

if [[ ! -f /tmp/human_operator_health.json ]]; then
  echo "[ERROR] Receiver did not start in time."
  echo "--- receiver log ---"
  cat /tmp/human_operator_receiver.log || true
  exit 1
fi

if ! grep -q '"relay_hardware_connected":true' /tmp/human_operator_health.json; then
  echo "[ERROR] Relay not connected according to /health"
  echo "Health response:"
  cat /tmp/human_operator_health.json
  echo "\n--- receiver log ---"
  cat /tmp/human_operator_receiver.log || true
  exit 1
fi

echo "[✓] Receiver ready with real relay hardware"
echo "[*] Launching app.py (Ctrl+C to stop all)"

RECEIVER_URL="$RECEIVER_URL" "$PYTHON_BIN" app.py
