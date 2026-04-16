#!/usr/bin/env bash
# Launch a Unity ratsim build on a headless Linux box over SSH.
#
# If an NVIDIA driver is present (nvidia-smi works), launches the binary
# directly — Unity uses EGL through the driver, no X server needed.
# Otherwise falls back to Xvfb + Mesa llvmpipe software GL.
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
if ! command -v ss >/dev/null; then
  echo "missing 'ss' (install iproute2)"
  exit 2
fi

BIN_BASE=$(basename "$BIN")
# Match process name only (not full command line) so we don't kill this script,
# whose argv contains the binary path.
pkill -9 "${BIN_BASE:0:15}" 2>/dev/null
pkill -9 Xvfb 2>/dev/null
sleep 1

if command -v nvidia-smi >/dev/null && nvidia-smi >/dev/null 2>&1; then
  echo "nvidia driver detected, launching with -force-glcore via EGL (no X server)"
  # __GLX_VENDOR_LIBRARY_NAME=nvidia ensures glvnd routes GL calls to the
  # NVIDIA userspace driver. Unity on Linux can create an offscreen EGL
  # context through it without needing an X display.
  __GLX_VENDOR_LIBRARY_NAME=nvidia \
    nohup "$BIN" -force-glcore -logFile "$LOG" >/dev/null 2>&1 &
  disown
else
  if ! command -v xvfb-run >/dev/null; then
    echo "no nvidia driver and xvfb-run not installed"
    echo "install with: sudo apt install -y xvfb libgl1-mesa-dri libglu1-mesa"
    exit 2
  fi
  echo "no nvidia driver, falling back to xvfb + llvmpipe software GL"
  LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
    nohup xvfb-run -a -s "-screen 0 1280x720x24 +extension GLX +render -noreset" \
    "$BIN" -logFile "$LOG" >/dev/null 2>&1 &
  disown
fi

echo "waiting up to 30s for port 9000..."
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
