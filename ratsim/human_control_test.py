"""
Run the simulator in human control mode for a single world/agent/task preset.

Usage:
    python -m ratsim.human_control_test
    python -m ratsim.human_control_test --world_preset default --agent_preset sphereagent_2d_lidar
    python -m ratsim.human_control_test --world_preset hilly_forest --task_preset default --seed 42

When imported, use run_human_session() directly.
"""

import argparse
import time

from ratsim.roslike_unity_connector.connector import RoslikeUnityConnector
from ratsim.roslike_unity_connector.message_definitions import (
    BoolMessage,
    StringMessage,
)
from ratsim.config_blender import blend_presets, to_entries_json
from ratsim.task_tracker import TaskTracker


def run_human_session(
    conn: RoslikeUnityConnector,
    world_config: dict,
    agent_config: dict,
    task_config: dict,
    seed: int | None = None,
    rtf: float = 1.0,
    max_steps: int | None = None,
) -> dict:
    """Run a single human-controlled episode. Returns metrics dict when the episode ends.

    Assumes conn is already connected and scene is selected.
    Blocks until episode termination or truncation.
    If max_steps is None, uses the task config's episode_max_steps.
    If max_steps <= 0, the episode runs indefinitely (no truncation).
    """
    tracker = TaskTracker(task_config)
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

    print(f"Human control active. Max steps: {max_steps if max_steps > 0 else 'unlimited'}, RTF: {rtf}")

    while True:
        frame_start = time.perf_counter()

        conn.send_messages_and_step(enable_physics_step=True)
        msgs = conn.read_messages_from_unity()

        step_count += 1
        tracker.update_with_unity_msgs(msgs)

        terminated = tracker.is_terminated()
        truncated = max_steps > 0 and step_count >= max_steps

        if terminated:
            print(f"Episode terminated at step {step_count}: {tracker.get_termination_reason()}")
            break
        if truncated:
            print(f"Episode truncated at step {step_count} (max steps reached)")
            break

        elapsed = time.perf_counter() - frame_start
        sleep_time = target_dt - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Disable human control
    conn.publish(BoolMessage(data=False), "/enable_human_control")
    conn.send_messages_and_step(enable_physics_step=False)
    conn.read_messages_from_unity()

    return {
        "steps": step_count,
        "total_score": tracker.get_total_score(),
        "objects_found": tracker.get_num_reward_objs_picked_up(),
        "collisions": tracker.get_collision_count(),
        "terminated": terminated,
        "truncated": truncated,
        "termination_reason": tracker.get_termination_reason(),
    }


def main():
    parser = argparse.ArgumentParser(description="Run simulator in human control mode")
    parser.add_argument("--world", default="default")
    parser.add_argument("--agent", default="sphereagent_2d_lidar")
    parser.add_argument("--task", default="default")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--rtf", type=float, default=1.0,
                        help="Real-time factor. 1.0 = real-time, 0.5 = half speed, 2.0 = double speed")
    args = parser.parse_args()

    world_config = blend_presets("world", [args.world])
    agent_config = blend_presets("agents", [args.agent])
    task_config = blend_presets("task", [args.task])

    conn = RoslikeUnityConnector(verbose=False)
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
            print(f"Episode {episode}. Press Enter to start (Ctrl+C to quit)...")
            input()

            result = run_human_session(conn, world_config, agent_config, task_config, seed=args.seed, rtf=args.rtf, max_steps=0)
            print(f"\nResults: {result}")
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
