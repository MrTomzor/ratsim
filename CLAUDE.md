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

## Topic Naming Conventions
- Agent-specific: `/rat1_pose`, `/rat1_velocity`, `/rat1_teleport`
- Sensors: `/lidar2d`, `/rgbd`, `/visual_point_track_pcl`
- Control: `/cmd_vel`
- System: `/sim_control/do_step`, `/sim_control/step_finished`

## Code Conventions
- CamelCase for classes, snake_case for functions/variables
- Message types are Python dataclasses auto-generated from C# definitions
- Bags use pickle serialization (`.pickle` files)
