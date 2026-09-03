# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ratsim** is a Python SDK for robotics simulation and reinforcement learning. It provides a TCP socket-based communication layer (ROS-like pub/sub) for connecting Python agents to environments simulated in Unity. Used by AI Gym and ROS2 wrappers in other repos.

## Build & Install

```bash
pip install -e .           # Development install (only core dep: numpy)
pip install torch torchvision scipy opencv-python scikit-learn  # Optional deps for training/nav
```

## Running Tests

There is no formal test framework. Test files are standalone scripts requiring a running Unity simulator on `localhost:9000`:

```bash
cd ratsim
python test_connection.py          # Basic connectivity
python test_vel_cmd.py             # Velocity commands
python record_human_trajectory.py output.pickle   # Record trajectory
```

## Architecture

### Core: `ratsim/roslike_unity_connector/`
- **`connector.py`** — `RoslikeUnityConnector` class: TCP socket client using non-blocking I/O (`selectors`). Handles JSON message serialization over newline-delimited protocol. Key methods: `connect()`, `publish()`, `send_messages_and_step()`, `read_messages_from_unity()`.
- **`message_definitions.py`** — Auto-generated message dataclasses (from C# via `generate_python_msgs.py`). Types include `PoseMessage`, `TwistMessage`, `Lidar2DMessage`, `FloatArrayMessage`, `RGBDMessage`, `MapGenTemplate2D`, etc. All registered in `MESSAGE_TYPE_REGISTRY` for dynamic dispatch.
- **`message_envelope.py`** — Wrapper for message serialization.
- **`bag.py`** — `MessageBag` for recording/replaying simulation steps (pickle format).

### Visualization: `ratsim/ratsim_vis/`
- `bag_plotting.py` — Matplotlib trajectory and sensor data visualization from recorded bags.

### Configuration: `ratsim/config_blender/`
- JSON presets for agents (`agents_presets/`) and worlds (`world_presets/`). Meant to be mixed/applied to configure simulation runs.

### Task Tracking: `ratsim/task_tracker/`
- **`task_tracker.py`** — `TaskTracker`: single source of truth for per-episode reward + termination + metrics. Consumes Unity msgs (collision, pickup, health, battery, pose, lidar), emits `get_this_step_score()`/`get_total_score()`/`is_terminated()`/`get_termination_reason()`. Topics are matched by suffix so `/collisions` and `/rat1/collisions` both work.
- **`exploration_tracker.py`** — `ExplorationTracker`: 2D occupancy grid (nav_msgs convention: -1 unknown / 0 free / 100 occupied), axis-aligned, centered on world origin. `update_from_lidar()` ray-casts via Bresenham, marks free/occupied cells and returns stats (`newly_known`, `rays_total`, `rays_out_of_bounds`, `rays_zero_len`, `agent_in_bounds`). `to_rgb_image()` renders the grid rotated/flipped to match Unity's top-down view (ROS +x / Unity +Z = top, ROS +y / Unity -X = left).
- **Exploration reward** is driven by TaskTracker when `volumetric_exploration_settings` is present in the task config: each step's newly-known cell area × `reward_per_m2` is added to the step score. Config keys: `reward_per_m2`, `grid_resolution` (m/cell), `visualize` (bool — live matplotlib viewer), `debug` (0/1/2 verbosity), `debug_every` (print period).
- **Pose topic for exploration**: the tracker subscribes to the agent's ground-truth pose (`/<name_prefix>/gt_pose`, published by `AbsolutePose2DSensor` which AgentLoader force-enables regardless of the user's `sensors` config — this sensor is not exposed as an RL observation, it's infrastructure). The lidar angle convention differs between Unity (`sin(θ), 0, cos(θ)`, CW from +Z) and ROS math (CCW from +x), so the tracker negates `angleStartDeg`/`angleIncrementDeg` when converting to radians — without this the occupied hits get mirrored left↔right around the agent.

### Deprecated: `ratsim/nav_DEPRECATED/`
Legacy navigation module (noise models, reactive controller, occupancy mapping). Being phased out.

## Simulation Loop Pattern

```python
connector = RoslikeUnityConnector(host_ip='127.0.0.1', port=9000)
connector.connect()
connector.publish(message, "/topic_name")
connector.send_messages_and_step(enable_physics_step=True)
observations = connector.read_messages_from_unity()
msgs = connector.get_received_messages("/lidar2d")
```

## Worldgen Dump & Compare (`ratsim/worldgen_dump.py`)

Verification tool for world generation. With `worldgen_dump/enabled: 1` in the world
config, Unity publishes a JSON snapshot of every structure, reward, well and agent on
`/sim_control/worldgen_dump` one frame after generation (see `WorldGenDump.cs`).
`fetch_worldgen_dump(conn, world_config, seed)` drives a reset with that flag and returns
the parsed dict; `diff_dumps(a, b)` lists differences (structures matched by geometry, not
by the per-process `DeterministicId`; objects as a multiset by kind/name/position).

```bash
python -m ratsim.worldgen_dump dump maze_memorymaze_11x11 --seed 42 --out /tmp/a.json
python -m ratsim.worldgen_dump compare default rules_default --seed 42
python -m ratsim.worldgen_dump compare-prefix rules_        # every preset vs its rules_ twin
```

Needs the Editor/build in play mode on port 9000 (`--port` to override). Used to check that
a preset rewritten in the generation-rules language reproduces the same world, and as a
regression test for loader changes. Known limits (both pre-existing sim behaviour): retry
seeds derived via `System.HashCode.Combine` differ between Unity processes, so compare
within one session; and collision-checked uniform reward spawns in chunks loaded during
the reset frame see the previous episode's colliders, so consecutive resets of a world with
`reward_objects/uniform_density > 0` can differ — interleave an empty world or compare
structure-mode presets.

## Unity Instance Launcher (`ratsim/unity_launcher.py`)

`allocate_unity_instances(n_envs, fresh=False)` is the single entry point for
deciding which Unity port(s) a script should use. Two operational tiers:

1. **Manual / interactive (no `RATSIM_UNITY_BIN`)**: user launches Unity
   themselves (Editor Play or `start_ratsim_headless.sh`). `n_envs=1` probes
   port 9000 and reuses it. `n_envs>1` raises with a clear error pointing the
   user at the env var.
2. **Auto-spawn (`RATSIM_UNITY_BIN` set)**: launcher can spawn additional
   instances on demand via `scripts/start_ratsim_headless.sh --port N`.
   `n_envs=1` still reuses port 9000 if alive (debug-friendly); `n_envs>1`
   always allocates from `FRESH_PORT_BASE` (9100+) so it can never clobber the
   persistent debug instance. Spawned instances are killed at process exit
   via `atexit`.

Port conventions:
- **9000** — `PERSISTENT_PORT`. Reserved for the long-running interactive
  instance (Editor Play, manual launches, human control test). Reused, never
  spawned over.
- **9100–9199** — `FRESH_PORT_BASE` range. Auto-spawned training instances.
  Multiple parallel runs should use non-overlapping subranges (e.g. run A on
  9100–9107, run B on 9110–9117) — pass a different `base_port` per run.

Liveness check (`_instance_alive`) is an open-port TCP probe: if a client can
connect, there's a Unity to attach to (Editor Play mode, a manual launch, or a
spawned build). The pidfile at `$RATSIM_RUNDIR/ratsim_<port>.pid` (written by
`start_ratsim_headless.sh`; `$RATSIM_RUNDIR` defaults to `/tmp`) is used only
for cleanup of instances we spawned, NOT for liveness — a stale pidfile must not
mask a live listener, otherwise an n_envs=1 run would spawn a fresh build on top
of a running Editor on 9000 instead of attaching to it. Stale dead-pid pidfiles
are cleared on probe.

`$RATSIM_RUNDIR` must be the same for the script and for `unity_launcher.py`
(`_rundir()`) — if they disagree, Python reads a pidfile the script never wrote
and silently fails to kill what it spawned. Point it at per-job scratch on any
machine where several runs share `/tmp`, or one job will kill another's Unity.

The launcher does not handle SIGTERM/SIGKILL on the parent process — if Python
dies hard, spawned Unity instances become orphans. Clean up with
`./scripts/stop_ratsim_headless.sh --all`.

## Headless Launch Scripts (`ratsim/scripts/`)

- **`setup_headless_display.sh`** — one-time `sudo` setup of an Xorg server on
  `:99` (NVIDIA-backed when available, llvmpipe fallback). Installed as a
  systemd unit. Re-run only after driver changes. Only needed for `gfx` mode
  below.
- **`start_ratsim_headless.sh [<bin>] [--port N] [--log path] [--force]
  [--xvfb|--gfx]`** — launches a Unity build on the given port (default 9000).
  `<bin>` falls back to `$RATSIM_UNITY_BIN`. Writes a pidfile at
  `$RATSIM_RUNDIR/ratsim_<port>.pid` and per-port log
  `$RATSIM_RUNDIR/ratsim_<port>.log`. Refuses to clobber a live port unless
  `--force`. Two display modes:
  - **`xvfb`** (default when xvfb is installed) — starts a throwaway X server
    for this instance and runs Unity `-batchmode -nographics`. No root needed,
    works on an HPC node, **~2.2× faster**. Uses `xvfb-run -a` when present,
    otherwise starts `Xvfb` itself on a free display (`-terminate`, so it exits
    with Unity). The pidfile holds the **Unity** pid, not the `xvfb-run`
    wrapper's — the wrapper's child survives killing the wrapper, so a wrapper
    pid there would leave an instance holding the port. Sidecars
    `.pgid` / `.xpid` let the stop path reap the wrapper and our own Xvfb.
  - **`gfx`** — attaches to an existing server (default `:99`, override with
    `$DISPLAY_NUM`) and renders normally. **Required for camera/RGBD agents**:
    `-nographics` gives Unity a null graphics device. Verifies the X socket
    exists first — Unity segfaults against a `DISPLAY` with no server behind it.

  Force a mode with `--xvfb`/`--gfx` or `RATSIM_XVFB=1`/`0`.
- **`stop_ratsim_headless.sh (--port N | --all | <bin>)`** — pidfile-based
  shutdown for headless launches, including the X server the launcher started
  for that instance; legacy basename match still supported for Editor / manual
  runs that don't write a pidfile.

## Topic Naming Conventions
- Agent-specific: `/rat1_pose`, `/rat1_velocity`, `/rat1_teleport`
- Sensors: `/lidar2d`, `/rgbd`, `/visual_point_track_pcl`
- Control: `/cmd_vel`
- System: `/sim_control/do_step`, `/sim_control/step_finished`

## Code Conventions
- CamelCase for classes, snake_case for functions/variables
- Message types are Python dataclasses auto-generated from C# definitions
- Bags use pickle serialization (`.pickle` files)
