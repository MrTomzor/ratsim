"""
Run the simulator in human control mode using ZeroMQ for communication.

Usage:
    python -m ratsim.human_control_test_zmq
    python -m ratsim.human_control_test_zmq --world default --agent sphereagent_2d_lidar
    python -m ratsim.human_control_test_zmq --world hilly_forest --task default --seed 42

When imported, use run_human_session() directly.
"""

import argparse
import time
import numpy as np

from ratsim.ZMQ_connector.connector import ZmqUnityConnector
from ratsim.ZMQ_connector.message_definitions import (
    BoolMessage,
    Float32Message,
    Lidar3DMessage,
    RawLidarMessage,
    StringMessage,
)
from ratsim.config_blender import blend_presets, to_entries_json
from ratsim.config_blender.blender import flatten_config
from ratsim.task_tracker import TaskTracker


def run_human_session(
    conn: ZmqUnityConnector,
    world_config: dict,
    agent_config: dict,
    task_config: dict,
    seed: int | None = None,
    rtf: float = 1.0,
    max_steps: int | None = None,
    fps_report_interval: int = 50,
) -> dict:
    """Run a single human-controlled episode. Returns metrics dict when the episode ends.

    Assumes conn is already connected and scene is selected.
    Blocks until episode termination or truncation.
    If max_steps is None, uses the task config's episode_max_steps.
    If max_steps <= 0, the episode runs indefinitely (no truncation).
    """
    flat_world = flatten_config(world_config)
    flat_agent = flatten_config(agent_config)
    agent_prefix = flat_agent.get("name_prefix", "rat1")
    tracker = TaskTracker(
        task_config,
        world_width=float(flat_world["world_bounds/width"]) if "world_bounds/width" in flat_world else None,
        world_height=float(flat_world["world_bounds/height"]) if "world_bounds/height" in flat_world else None,
        pose_topic=f"/{agent_prefix}/gt_pose",
        lidar_topic="/lidar2d",
    )
    tracker.reset()

    # Apply seed if given
    cfg = dict(world_config)
    if seed is not None:
        cfg["seed"] = seed

    # Send configs and reset
    conn.publish(StringMessage(data=to_entries_json(cfg)), "/sim_control/world_config")
    conn.publish(BoolMessage(data=True), "/sim_control/reset_episode")
    conn.send_messages_and_step(enable_physics_step=True)
    conn.read_messages_from_unity()

    # Let worldgen settle
    conn.publish(BoolMessage(data=True), "/enable_human_control")
    conn.send_messages_and_step(enable_physics_step=True)
    conn.read_messages_from_unity()

    # Episode loop — Python just ticks the sim and reads metrics,
    # Unity handles human input directly.
    # Physics step is 0.02s (50Hz). RTF=1.0 means 50 ticks/s real-time.
    PHYSICS_DT = 0.02
    target_dt = PHYSICS_DT / rtf  # wall-clock seconds between ticks
    step_count = 0
    if max_steps is None:
        max_steps = tracker.episode_max_steps

    print(f"Human control active (ZMQ). Max steps: {max_steps if max_steps > 0 else 'unlimited'}, RTF: {rtf}")

    run_start = time.perf_counter()
    window_start = run_start
    window_steps = 0
    window_active_time = 0.0

    while True:
        frame_start = time.perf_counter()

        conn.send_messages_and_step(enable_physics_step=True)
        msgs = conn.read_messages_from_unity()

        step_count += 1
        window_steps += 1

        

        tracker.update_with_unity_msgs(msgs)

        # Send step score back to Unity for UI visualization
        conn.publish(Float32Message(data=tracker.get_this_step_score()), "/step_score")

        terminated = tracker.is_terminated()
        truncated = max_steps > 0 and step_count >= max_steps

        if terminated:
            print(f"Episode terminated at step {step_count}: {tracker.get_termination_reason()}")
            tracker.print_exploration_summary(prefix="end-of-episode")
            break
        if truncated:
            print(f"Episode truncated at step {step_count} (max steps reached)")
            tracker.print_exploration_summary(prefix="end-of-episode")
            break

        elapsed = time.perf_counter() - frame_start
        window_active_time += elapsed
        sleep_time = target_dt - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

        if fps_report_interval > 0 and step_count % fps_report_interval == 0:
            now = time.perf_counter()
            window_dt = now - window_start
            window_fps = window_steps / window_dt if window_dt > 0 else 0.0
            raw_fps = window_steps / window_active_time if window_active_time > 0 else 0.0
            print(f"[Step {step_count}] FPS: {window_fps:.1f} (raw sim: {raw_fps:.1f} FPS)")
            window_start = now
            window_steps = 0
            window_active_time = 0.0

            for topic, msg_list in msgs.items():
                for m in msg_list:
                    if isinstance(m, (RawLidarMessage, Lidar3DMessage)):
                        print(f"[Step {step_count}] Received 3D LiDAR on '{topic}' ({type(m).__name__}): n_rays: {np.array(m.ranges).shape} | n_descriptors_per_category: {np.array(m.descriptors).sum(axis=0)}")

    # Disable human control
    conn.publish(BoolMessage(data=False), "/enable_human_control")
    conn.send_messages_and_step(enable_physics_step=False)
    conn.read_messages_from_unity()

    total_dt = time.perf_counter() - run_start
    mean_fps = step_count / total_dt if total_dt > 0 else 0.0

    return {
        "steps": step_count,
        "mean_fps": round(mean_fps, 1),
        "total_score": tracker.get_total_score(),
        "objects_found": tracker.get_num_reward_objs_picked_up(),
        "collisions": tracker.get_collision_count(),
        "explored_area_m2": tracker.get_explored_area_m2(),
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": tracker.get_termination_reason(),
    }


def main():
    parser = argparse.ArgumentParser(description="Run simulator in human control mode using ZeroMQ")
    parser.add_argument("--unity_connector_ip", default="0.0.0.0")
    parser.add_argument("--world", default="default")
    parser.add_argument("--agent", default="sphereagent_2d_lidar")
    parser.add_argument("--task", default="default")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--rtf", type=float, default=1.0,
                        help="Real-time factor. 1.0 = real-time, 0.5 = half speed, 2.0 = double speed")
    parser.add_argument("--fps-interval", type=int, default=50,
                        help="Print rolling FPS every N steps (0 to disable, default: 50)")
    args = parser.parse_args()

    world_config = blend_presets("world", [args.world])
    agent_config = blend_presets("agents", [args.agent])
    task_config = blend_presets("task", [args.task])

    conn = ZmqUnityConnector(verbose=False, host_ip=args.unity_connector_ip)
    conn.connect()

    # Select scene and send agent config
    conn.publish(StringMessage(data="Wildfire"), "/sim_control/scene_select")
    conn.send_messages_and_step(enable_physics_step=False)
    conn.read_messages_from_unity()

    conn.publish(StringMessage(data=to_entries_json(agent_config)), "/sim_control/agent_config")
    conn.send_messages_and_step(enable_physics_step=False)
    conn.read_messages_from_unity()

    print(f"World: {args.world}, Agent: {args.agent}, Task: {args.task}")

    episode = 0
    try:
        while True:
            episode += 1
            print(f"\n{'='*60}")
            print(f"Episode {episode}")

            result = run_human_session(
                conn,
                world_config,
                agent_config,
                task_config,
                seed=args.seed,
                rtf=args.rtf,
                max_steps=0,
                fps_report_interval=args.fps_interval,
            )
            print(f"\nResults: {result}")
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
