import yaml
import numpy as np

from roslike_unity_connector.message_definitions import Twist2DMessage

class NavTask:
    def __init__(self, start_position, start_rotation_deg_clockwise, goal_position, max_distance_from_goal, max_steps):
        self.start_position = tuple(start_position)
        self.start_rotation_deg_clockwise = start_rotation_deg_clockwise
        self.goal_position = tuple(goal_position)
        self.max_distance_from_goal = max_distance_from_goal
        self.max_steps = max_steps

    def __repr__(self):
        return (
            f"Trial(start_position={self.start_position}, rotation_deg={self.rotation_deg}, "
            f"goal_position={self.goal_position}, max_distance_from_goal={self.max_distance_from_goal}, "
            f"max_steps={self.max_steps})"
        )


class NavTrial:
    # def __init__(self, foldername) -> None:
    #     pass
    def __init__(self, bag_files=None, tasks=None):
        self.bag_files = bag_files  if bag_files  is not None else []
        self.tasks = tasks if tasks  is not None else []

    def task_start_to_msg(self, task):
        msg = Twist2DMessage()
        msg.forward = task.start_position[1]
        msg.left = -task.start_position[0]
        msg.radiansCounterClockwise = - np.deg2rad(task.start_rotation_deg_clockwise)

        return msg

    @staticmethod
    def from_folder(folder_path):
        defpath = folder_path + "def.yaml"
        with open(defpath, 'r') as f:
            data = yaml.safe_load(f)

        bag_files = data.get("bag_files", [])
        for f in bag_files:
            f = folder_path + f
        tasks_data = data.get("tasks", [])

        tasks = []
        for trial_data in tasks_data:
            task = NavTask(
                start_position=trial_data["start_position_x_z"],
                start_rotation_deg_clockwise =trial_data["start_rotation_deg_clockwise"],
                goal_position=trial_data["goal_position_x_z"],
                max_distance_from_goal=trial_data["max_distance_from_goal"],
                max_steps=trial_data["max_steps"]
            )
            tasks.append(task)

        return NavTrial(bag_files=bag_files, tasks=tasks)

    def __repr__(self):
        return f"NavTaskDefinition(bag_files={self.bag_files}, tasks={self.tasks})"
