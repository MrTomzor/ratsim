#!/usr/bin/env bash
# Launch a Unity ratsim build on a headless Linux box (no GPU, no display).
# Uses Xvfb for a virtual display and Mesa llvmpipe for software OpenGL so
# Unity can create a GL context and reach the scene where the TCP server starts.
#
# Usage:
#   ./start_ratsim_headless.sh /path/to/ForagerSimBuildV1.x86_64 [log_path]
set -u

BIN=${1:-}
LOG=${2:-/tmp/ratsim.log}

if [[ -z "$BIN" ]]; then
  echo "usage: $0 <path-to-unity-binary> [log_path]"
  exit 2
fi
if [[ ! -x "$BIN" ]]; then
  echo "binary not found or not executable: $BIN"
  exit 2
fi

for cmd in xvfb-run ss; do
  if ! command -v "$cmd" >/dev/null; then
    echo "missing dependency: $cmd"
    echo "install with: sudo apt install -y xvfb libgl1-mesa-dri libglu1-mesa iproute2"
    exit 2
  fi
done

BIN_BASE=$(basename "$BIN")
# Match process name only (not full command line) so we don't kill this script,
# whose argv contains the binary path.
pkill -9 "${BIN_BASE:0:15}" 2>/dev/null
pkill -9 Xvfb 2>/dev/null
sleep 1

LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  nohup xvfb-run -a -s "-screen 0 1280x720x24 +extension GLX +render -noreset" \
  "$BIN" -logFile "$LOG" >/dev/null 2>&1 &
disown

echo "launched $BIN, waiting up to 30s for port 9000..."
for i in {1..30}; do
  sleep 1
  if ss -tln | grep -q ':9000 '; then
    echo "TCP server up after ${i}s (log: $LOG)"
    exit 0
  fi
done

echo "timed out. last 40 log lines:"
tail -40 "$LOG"
exit 1
