"""Helpers for launching/discovering Unity ratsim instances.

Supports two operational tiers:

1. **Manual / interactive**: user launches Unity themselves (Editor Play mode
   or `start_ratsim_headless.sh`). Scripts default to port 9000, find the
   running instance, attach. Only works for n_envs=1.
2. **Auto-spawn**: `RATSIM_UNITY_BIN` env var points at the build. Scripts can
   spawn additional instances on demand. n_envs=1 still reuses port 9000 if
   alive (debug-friendly); n_envs>1 always spawns fresh on a separate range
   so it can't clobber the persistent debug instance.

The intended usage from a training script::

    from ratsim.unity_launcher import allocate_unity_instances

    instances = allocate_unity_instances(n_envs=8, fresh=False)
    # instances is a list of UnityInstance(port=..., owned=...) — one per env.
    # Owned instances are killed at process exit; reused ones are left alone.

This module never assumes a port is alive just because it answers — callers
that need a heartbeat should send one over TCP after connecting.
"""

from __future__ import annotations

import atexit
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


PERSISTENT_PORT = 9000
"""Port reserved for the long-running interactive instance.

n_envs=1 reuses this; n_envs>1 always spawns fresh elsewhere.
"""

FRESH_PORT_BASE = 9100
"""Starting port for auto-spawned training instances. Range 9100..9199."""

PIDFILE_TEMPLATE = "/tmp/ratsim_{port}.pid"


@dataclass
class UnityInstance:
    """A handle to a Unity instance the launcher chose for an env.

    Attributes:
        port: TCP port the instance listens on.
        owned: If True, the launcher spawned this and is responsible for
            killing it at exit. If False, it was reused (don't touch lifecycle).
    """

    port: int
    owned: bool


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Return True if something is accepting TCP connections on port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _read_pidfile(port: int) -> Optional[int]:
    p = Path(PIDFILE_TEMPLATE.format(port=port))
    if not p.exists():
        return None
    try:
        return int(p.read_text().strip())
    except (ValueError, OSError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def _instance_alive(port: int) -> bool:
    """Combined liveness: port is open AND, if a pidfile exists, that pid runs.

    The pidfile is written by start_ratsim_headless.sh. Editor Play mode and
    manually-launched binaries won't have one — in that case we fall back to
    just probing the port.
    """
    if not _port_open(port):
        return False
    pid = _read_pidfile(port)
    if pid is not None and not _pid_alive(pid):
        return False
    return True


def _resolve_binary() -> Optional[Path]:
    raw = os.environ.get("RATSIM_UNITY_BIN")
    if not raw:
        return None
    p = Path(raw).expanduser()
    if not p.exists() or not os.access(p, os.X_OK):
        raise RuntimeError(
            f"RATSIM_UNITY_BIN points at {p} but it isn't an executable file"
        )
    return p


def _launcher_script() -> Path:
    """Find start_ratsim_headless.sh next to this module's repo."""
    here = Path(__file__).resolve()
    candidate = here.parent.parent / "scripts" / "start_ratsim_headless.sh"
    if candidate.exists():
        return candidate
    raise RuntimeError(f"could not locate start_ratsim_headless.sh (looked at {candidate})")


def _spawn_via_script(binary: Path, port: int, log_path: Optional[str] = None,
                      timeout_s: float = 30.0) -> None:
    """Launch a Unity instance via start_ratsim_headless.sh and block until ready.

    The script handles the X display, pidfile, and per-port log. It exits 0 once
    the TCP listener is up.
    """
    script = _launcher_script()
    cmd = [str(script), str(binary), "--port", str(port)]
    if log_path:
        cmd.extend(["--log", log_path])
    print(f"[unity_launcher] spawning Unity on port {port} via {script.name}")
    res = subprocess.run(cmd, timeout=timeout_s + 5)
    if res.returncode != 0:
        raise RuntimeError(f"start_ratsim_headless.sh failed for port {port} (rc={res.returncode})")


def _kill_owned(port: int) -> None:
    """Best-effort: kill the instance we spawned on this port."""
    pid = _read_pidfile(port)
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError as e:
        print(f"[unity_launcher] failed to kill pid {pid} on port {port}: {e}")
    pidfile = Path(PIDFILE_TEMPLATE.format(port=port))
    try:
        pidfile.unlink(missing_ok=True)
    except OSError:
        pass


def _register_cleanup(port: int) -> None:
    """Ensure spawned instances die when the parent Python process exits."""
    atexit.register(_kill_owned, port)


def allocate_unity_instances(
    n_envs: int = 1,
    fresh: bool = False,
    base_port: Optional[int] = None,
) -> List[UnityInstance]:
    """Pick (and spawn if needed) Unity instances for ``n_envs`` envs.

    Rules:
      * n_envs == 1, no ``base_port``, not ``fresh``: probe :9000. Reuse if
        alive; else spawn fresh on :9000 (requires RATSIM_UNITY_BIN). Useful
        for debug runs alongside a manually-launched Unity.
      * n_envs == 1 with ``fresh=True`` or an explicit ``base_port``: always
        spawn on ``base_port`` (default :9100 if ``fresh=True`` and no
        base_port given). Use when you don't want to touch the persistent
        instance — e.g. running a second training process in parallel.
      * n_envs > 1: always spawn fresh on ``base_port..base_port+n-1``
        (default base_port :9100). Refuses to use port 9000. Requires
        RATSIM_UNITY_BIN.

    Returns one UnityInstance per env. ``.owned`` is True for spawned ones
    (cleaned up at process exit) and False for the reused persistent instance.
    """
    if n_envs < 1:
        raise ValueError(f"n_envs must be >= 1, got {n_envs}")

    binary = _resolve_binary()
    base_port_specified = base_port is not None
    if base_port is None:
        base_port = FRESH_PORT_BASE

    # n_envs=1 reuse path: only when the caller didn't ask for a specific port.
    if n_envs == 1 and not fresh and not base_port_specified:
        if _instance_alive(PERSISTENT_PORT):
            print(f"[unity_launcher] reusing existing instance on port {PERSISTENT_PORT}")
            return [UnityInstance(port=PERSISTENT_PORT, owned=False)]
        if binary is None:
            raise RuntimeError(
                f"no Unity instance on port {PERSISTENT_PORT} and RATSIM_UNITY_BIN is unset.\n"
                f"either: (a) launch Unity manually (Editor Play / start_ratsim_headless.sh) "
                f"so it listens on {PERSISTENT_PORT}, or (b) export RATSIM_UNITY_BIN to enable auto-spawn."
            )
        _spawn_via_script(binary, PERSISTENT_PORT)
        _register_cleanup(PERSISTENT_PORT)
        return [UnityInstance(port=PERSISTENT_PORT, owned=True)]

    # Fresh-spawn path (n_envs > 1, fresh=True, or explicit base_port)
    if binary is None:
        raise RuntimeError(
            "auto-spawn requested but RATSIM_UNITY_BIN is unset.\n"
            "export RATSIM_UNITY_BIN=/path/to/ForagerSimBuild.x86_64 to enable multi-env training."
        )

    ports = list(range(base_port, base_port + n_envs))
    # Refuse to overwrite the persistent slot or any port already alive.
    for p in ports:
        if p == PERSISTENT_PORT:
            raise ValueError(
                f"fresh-spawn range {ports} overlaps the persistent port {PERSISTENT_PORT}; "
                f"pick a different base_port"
            )
        if _instance_alive(p):
            raise RuntimeError(
                f"port {p} is already in use; kill it first "
                f"(./scripts/stop_ratsim_headless.sh --port {p}) or pick a different base_port"
            )

    instances: List[UnityInstance] = []
    for p in ports:
        _spawn_via_script(binary, p)
        _register_cleanup(p)
        instances.append(UnityInstance(port=p, owned=True))

    print(f"[unity_launcher] spawned {n_envs} fresh instances on ports {ports}")
    return instances


__all__ = [
    "UnityInstance",
    "PERSISTENT_PORT",
    "FRESH_PORT_BASE",
    "allocate_unity_instances",
]
