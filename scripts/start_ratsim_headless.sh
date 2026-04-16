#!/usr/bin/env bash
# Launch a Unity ratsim build on a headless Linux box over SSH.
#
# Expects setup_headless_display.sh to have been run once — that sets up a
# virtual X server on :99 (GPU-backed on NVIDIA, CPU/llvmpipe otherwise).
# This script just attaches the Unity binary to :99 and waits for port 9000.
#
# Usage:
#   ./start_ratsim_headless.sh /path/to/ForagerSimBuildV1.x86_64 [log_path]
set -u

BIN=${1:-}
LOG=${2:-/tmp/ratsim.log}
DISPLAY_NUM=${DISPLAY_NUM:-:99}

if [[ -z "$BIN" ]]; then
  echo "usage: $0 <path-to-unity-binary> [log_path]"
  exit 2
fi
if [[ ! -x "$BIN" ]]; then
  echo "binary not found or not executable: $BIN"
  exit 2
fi
if ! command -v ss >/dev/null; then
  echo "missing 'ss' (install iproute2)"
  exit 2
fi

if [[ ! -e "/tmp/.X11-unix/X${DISPLAY_NUM#:}" ]]; then
  echo "no X server on $DISPLAY_NUM — run sudo ./scripts/setup_headless_display.sh first"
  exit 2
fi

BIN_BASE=$(basename "$BIN")
# Match process name only (not full command line) so we don't kill this script,
# whose argv contains the binary path.
pkill -9 "${BIN_BASE:0:15}" 2>/dev/null
sleep 1

echo "launching on DISPLAY=$DISPLAY_NUM (log: $LOG)"
DISPLAY=$DISPLAY_NUM nohup "$BIN" -logFile "$LOG" >/dev/null 2>&1 &
disown

echo "waiting up to 30s for port 9000..."
for i in {1..30}; do
  sleep 1
  if ss -tln | grep -q ':9000 '; then
    echo "TCP server up after ${i}s"
    exit 0
  fi
done

echo "timed out. last 40 log lines:"
tail -40 "$LOG"
exit 1
