#!/usr/bin/env bash
# Kill a running ratsim Unity binary launched via start_ratsim_headless.sh.
#
# Usage:
#   ./stop_ratsim_headless.sh /path/to/ForagerSimBuildV1.x86_64
#   ./stop_ratsim_headless.sh ForagerSimBuildV1.x86_64   # basename also works
set -u

BIN=${1:-}
if [[ -z "$BIN" ]]; then
  echo "usage: $0 <unity-binary-path-or-basename>"
  exit 2
fi

BIN_BASE=$(basename "$BIN")
# Linux caps comm names at 15 chars; pkill matches against comm by default.
PATTERN="${BIN_BASE:0:15}"

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
