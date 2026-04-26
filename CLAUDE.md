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

Liveness check (`_instance_alive`) combines a TCP probe with a pidfile read at
`/tmp/ratsim_<port>.pid` (written by `start_ratsim_headless.sh`). Editor Play
mode and manual launches won't have a pidfile — port-only is the fallback.

The launcher does not handle SIGTERM/SIGKILL on the parent process — if Python
dies hard, spawned Unity instances become orphans. Clean up with
`./scripts/stop_ratsim_headless.sh --all`.

## Headless Launch Scripts (`ratsim/scripts/`)

- **`setup_headless_display.sh`** — one-time `sudo` setup of an Xorg server on
  `:99` (NVIDIA-backed when available, llvmpipe fallback). Installed as a
  systemd unit. Re-run only after driver changes.
- **`start_ratsim_headless.sh [<bin>] [--port N] [--log path] [--force]`** —
  launches a Unity build attached to `:99` on the given port (default 9000).
  Writes a pidfile at `/tmp/ratsim_<port>.pid` and per-port log
  `/tmp/ratsim_<port>.log`. Refuses to clobber a live port unless `--force`.
  `<bin>` falls back to `$RATSIM_UNITY_BIN`.
- **`stop_ratsim_headless.sh (--port N | --all | <bin>)`** — pidfile-based
  shutdown for headless launches; legacy basename match still supported for
  Editor / manual runs that don't write a pidfile.

## Topic Naming Conventions
- Agent-specific: `/rat1_pose`, `/rat1_velocity`, `/rat1_teleport`
- Sensors: `/lidar2d`, `/rgbd`, `/visual_point_track_pcl`
- Control: `/cmd_vel`
- System: `/sim_control/do_step`, `/sim_control/step_finished`

## Code Conventions
- CamelCase for classes, snake_case for functions/variables
- Message types are Python dataclasses auto-generated from C# definitions
- Bags use pickle serialization (`.pickle` files)
