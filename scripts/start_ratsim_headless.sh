#!/usr/bin/env bash
# Launch a Unity ratsim build on a headless Linux box over SSH.
#
# Expects setup_headless_display.sh to have been run once — that sets up a
# virtual X server on :99 (GPU-backed on NVIDIA, CPU/llvmpipe otherwise).
# This script attaches the Unity binary to :99, passes it -port, and waits
# for the TCP listener on that port. Multiple instances on different ports
# coexist (the script is per-port, never kills other ports).
#
# Usage:
#   ./start_ratsim_headless.sh <bin> [--port 9000] [--log /path/log] [--force]
#   ./start_ratsim_headless.sh --port 9001                    # uses $RATSIM_UNITY_BIN
#
# If <bin> is omitted the env var RATSIM_UNITY_BIN must be set.
# Default port is 9000. Default log is /tmp/ratsim_<port>.log.
# A pidfile is written to /tmp/ratsim_<port>.pid for liveness checks.
# --force kills the existing instance on this port (if any) before launching.
set -u

BIN=""
PORT=9000
LOG=""
FORCE=0
DISPLAY_NUM=${DISPLAY_NUM:-:99}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --log)  LOG="$2";  shift 2 ;;
    --force) FORCE=1;  shift ;;
    -h|--help)
      sed -n '2,17p' "$0"; exit 0 ;;
    *)
      if [[ -z "$BIN" ]]; then BIN="$1"; shift
      else echo "unknown arg: $1"; exit 2; fi ;;
  esac
done

if [[ -z "$BIN" ]]; then
  BIN="${RATSIM_UNITY_BIN:-}"
fi
if [[ -z "$BIN" ]]; then
  echo "no binary path: pass as first arg or set RATSIM_UNITY_BIN"
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

LOG="${LOG:-/tmp/ratsim_${PORT}.log}"
PIDFILE="/tmp/ratsim_${PORT}.pid"

if [[ ! -e "/tmp/.X11-unix/X${DISPLAY_NUM#:}" ]]; then
  echo "no X server on $DISPLAY_NUM — run sudo ./scripts/setup_headless_display.sh first"
  exit 2
fi

# Refuse to clobber a live instance on this port unless --force.
if ss -tln | grep -q ":${PORT} "; then
  if [[ "$FORCE" -eq 1 ]]; then
    echo "port ${PORT} in use — --force given, killing previous instance"
    if [[ -f "$PIDFILE" ]]; then
      kill -9 "$(cat "$PIDFILE")" 2>/dev/null || true
      rm -f "$PIDFILE"
    fi
    sleep 1
  else
    echo "port ${PORT} already in use (pidfile: $(cat "$PIDFILE" 2>/dev/null || echo "?"))"
    echo "use --force to replace, or pick a different --port"
    exit 1
  fi
fi

echo "launching $(basename "$BIN") on DISPLAY=$DISPLAY_NUM port=$PORT (log: $LOG)"
DISPLAY="$DISPLAY_NUM" nohup "$BIN" -port "$PORT" -logFile "$LOG" >/dev/null 2>&1 &
PID=$!
disown
echo "$PID" > "$PIDFILE"

echo "waiting up to 30s for port ${PORT}..."
for i in {1..30}; do
  sleep 1
  if ss -tln | grep -q ":${PORT} "; then
    echo "TCP server up on port ${PORT} after ${i}s (pid ${PID})"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Unity process died before opening port ${PORT}. last 40 log lines:"
    tail -40 "$LOG"
    rm -f "$PIDFILE"
    exit 1
  fi
done

echo "timed out. last 40 log lines:"
tail -40 "$LOG"
exit 1
