#!/usr/bin/env bash
# Kill a running ratsim Unity binary launched via start_ratsim_headless.sh.
#
# Usage:
#   ./stop_ratsim_headless.sh --port 9000        # kill via pidfile (preferred)
#   ./stop_ratsim_headless.sh --all              # kill every ratsim_*.pid instance
#   ./stop_ratsim_headless.sh /path/to/bin       # legacy: kill by basename match
set -u

PORT=""
ALL=0
BIN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --all)  ALL=1;     shift ;;
    -h|--help)
      sed -n '2,8p' "$0"; exit 0 ;;
    *)
      if [[ -z "$BIN" ]]; then BIN="$1"; shift
      else echo "unknown arg: $1"; exit 2; fi ;;
  esac
done

kill_by_pidfile() {
  local pf="$1"
  [[ -f "$pf" ]] || { echo "no pidfile: $pf"; return 1; }
  local pid
  pid="$(cat "$pf")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "killing pid $pid (from $pf)"
    kill -9 "$pid" 2>/dev/null || true
  else
    echo "pid $pid not running (stale pidfile $pf)"
  fi
  rm -f "$pf"
}

if [[ "$ALL" -eq 1 ]]; then
  shopt -s nullglob
  for pf in /tmp/ratsim_*.pid; do
    kill_by_pidfile "$pf"
  done
  exit 0
fi

if [[ -n "$PORT" ]]; then
  kill_by_pidfile "/tmp/ratsim_${PORT}.pid"
  exit 0
fi

# Legacy path: kill by binary basename. Used when launched without pidfile or
# from a non-headless start (Editor, manual ./bin run).
if [[ -z "$BIN" ]]; then
  echo "usage: $0 (--port <p> | --all | <unity-binary-path-or-basename>)"
  exit 2
fi

BIN_BASE=$(basename "$BIN")
PATTERN="${BIN_BASE:0:15}"  # comm names are capped at 15 chars

if ! pgrep -x "$PATTERN" >/dev/null; then
  echo "no process matching '$PATTERN' running"
  exit 0
fi

echo "killing '$PATTERN'..."
pkill -9 -x "$PATTERN"
sleep 1

if pgrep -x "$PATTERN" >/dev/null; then
  echo "warning: process still present"
  pgrep -a -x "$PATTERN"
  exit 1
fi

echo "stopped."
