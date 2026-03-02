class TaskTracker:
    """Computes per-step reward and episode termination from Unity messages.

    Driven by a task config dict (loaded from task_presets/default.json).

    Topics are matched by suffix so that both bare topics (e.g. ``/collisions``)
    and agent-namespaced topics (e.g. ``/rat1/collisions``) are handled
    automatically.  Reward pickups are summed across all agents; termination
    triggers if *any* agent hits the condition.

    Usage::

        tracker = TaskTracker(task_config)
        tracker.reset()
        # ...each step:
        tracker.update_with_unity_msgs(msgs)
        reward     = tracker.get_this_step_score()
        terminated = tracker.is_terminated()
    """

    # Topic suffixes (matched against the end of every incoming topic name)
    _COLLISION_SUFFIX = "collisions"
    _REWARD_PICKUP_SUFFIX = "reward_pickup"
    _HEALTH_SUFFIX = "health"
    _BATTERY_SUFFIX = "battery"
    _ALL_REWARDS_COLLECTED_SUFFIX = "all_rewards_collected"

    def __init__(self, task_config: dict):
        self.episode_max_steps = task_config.get("episode_max_steps", 300)

        foraging = task_config.get("foraging_settings", {})
        self.pickup_reward_modifier = foraging.get("reward_object_pickup_modifier", 1.0)
        self.negative_pickup_modifier = foraging.get("negative_pickups_modifier", 1.0)

        collision = task_config.get("collision_settings", {})
        self.penalize_collisions = collision.get("penalize_collisions", True)
        self.penalization_variable = collision.get("penalization_variable", "velocity")
        self.collision_penalty_modifier = collision.get("collision_penalty_modifier", 0.3)
        self.collision_flat_penalty = collision.get("collision_flat_penalty", 0.0)
        self.min_col_velocity = collision.get("min_col_velocity", 1.0)

        termination = task_config.get("termination_settings", {})
        self.terminate_on_collision = termination.get("terminate_on_collision", True)
        self.collision_termination_reward = termination.get("collision_termination_reward", 0.0)
        self.terminate_on_zero_battery = termination.get("terminate_on_zero_battery", True)
        self.zero_battery_termination_reward = termination.get("zero_battery_termination_reward", 0.0)
        self.terminate_on_zero_health = termination.get("terminate_on_zero_health", True)
        self.zero_health_termination_reward = termination.get("zero_health_termination_reward", 0.0)
        self.terminate_on_all_rewards_collected = termination.get("terminate_on_all_rewards_collected", True)
        self.all_rewards_collected_termination_reward = termination.get("all_rewards_collected_termination_reward", 0.0)

        self.reset()

    def reset(self):
        """Reset all episode state. Call at the start of each episode."""
        self._step_score = 0.0
        self._total_score = 0.0
        self._terminated = False
        self._termination_reason = None
        self._num_reward_objs_picked_up = 0
        self._collision_count = 0

    def update_with_unity_msgs(self, msgs: dict):
        """Process one step's Unity messages, updating score and termination state.

        Args:
            msgs: dict mapping topic strings to lists of message objects,
                  as returned by RoslikeUnityConnector.read_messages_from_unity().
        """
        self._step_score = 0.0

        # --- Collisions (any agent) ---
        for col_vel in self._get_values_by_suffix(msgs, self._COLLISION_SUFFIX):
            if col_vel is None or abs(col_vel) < self.min_col_velocity:
                continue
            self._collision_count += 1
            if self.penalize_collisions:
                if self.penalization_variable == "velocity":
                    penalty = self.collision_penalty_modifier * abs(col_vel)
                else:
                    penalty = self.collision_penalty_modifier
                penalty += self.collision_flat_penalty
                self._step_score -= penalty
                print(f"[TaskTracker] Collision vel={col_vel:.2f}, penalty={penalty:.3f}")

            if self.terminate_on_collision and not self._terminated:
                self._step_score += self.collision_termination_reward
                self._terminated = True
                self._termination_reason = "collision"
                print("[TaskTracker] Terminating: collision")

        # --- Health from Unity (any agent) ---
        if self.terminate_on_zero_health and not self._terminated:
            for health in self._get_values_by_suffix(msgs, self._HEALTH_SUFFIX):
                if health is not None and health <= 0.0:
                    self._step_score += self.zero_health_termination_reward
                    self._terminated = True
                    self._termination_reason = "zero_health"
                    print("[TaskTracker] Terminating: zero health")
                    break

        # --- Reward object pickups (all agents summed) ---
        num_pickups = self._get_total_pickups(msgs)
        if num_pickups > 0:
            self._step_score += num_pickups * self.pickup_reward_modifier
            self._num_reward_objs_picked_up += num_pickups
            print(f"[TaskTracker] Picked up {num_pickups} objects, score += {num_pickups * self.pickup_reward_modifier:.2f}")

        # --- Battery depletion (any agent) ---
        if self.terminate_on_zero_battery and not self._terminated:
            for battery in self._get_values_by_suffix(msgs, self._BATTERY_SUFFIX):
                if battery is not None and battery <= 0.0:
                    self._step_score += self.zero_battery_termination_reward
                    self._terminated = True
                    self._termination_reason = "zero_battery"
                    print("[TaskTracker] Terminating: zero battery")
                    break

        # --- All rewards collected ---
        if self.terminate_on_all_rewards_collected and not self._terminated:
            for topic in self._topics_by_suffix(msgs, self._ALL_REWARDS_COLLECTED_SUFFIX):
                if msgs[topic][0].data:
                    self._step_score += self.all_rewards_collected_termination_reward
                    self._terminated = True
                    self._termination_reason = "all_rewards_collected"
                    print("[TaskTracker] Terminating: all rewards collected")
                    break

        self._total_score += self._step_score

    # --- Score / state accessors ---

    def get_this_step_score(self) -> float:
        """Return the reward accumulated in the most recent update_with_unity_msgs call."""
        return self._step_score

    def get_total_score(self) -> float:
        """Return the cumulative reward across the episode (for debugging)."""
        return self._total_score

    def is_terminated(self) -> bool:
        """Return True if a termination condition was triggered this episode."""
        return self._terminated

    def get_termination_reason(self) -> "str | None":
        """Return a string describing why the episode terminated, or None."""
        return self._termination_reason

    def get_num_reward_objs_picked_up(self) -> int:
        return self._num_reward_objs_picked_up

    def get_collision_count(self) -> int:
        return self._collision_count

    # --- Topic matching helpers ---

    def _topics_by_suffix(self, msgs: dict, suffix: str) -> list:
        """Return all topic names whose last path component equals suffix."""
        return [t for t in msgs if t == f"/{suffix}" or t.endswith(f"/{suffix}")]

    def _get_values_by_suffix(self, msgs: dict, suffix: str) -> list:
        """Return the .data value from the first message on each matching topic."""
        return [msgs[t][0].data for t in self._topics_by_suffix(msgs, suffix)]

    def _get_total_pickups(self, msgs: dict) -> int:
        """Sum .data across all messages on all reward_pickup topics."""
        total = 0
        for topic in self._topics_by_suffix(msgs, self._REWARD_PICKUP_SUFFIX):
            total += sum(msg.data for msg in msgs[topic])
        return total
