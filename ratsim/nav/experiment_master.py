from nav.navsim import NavSim
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from roslike_unity_connector.bag import *
from nav.navbenchmark import *
from nav.reactive_controller import *

class ExperimentMaster:
    def __init__(self, benchmark : NavBenchmark, model = None):
        self.benchmark = benchmark
        if not model is None:
            self.set_model(model)

    def set_model(self, model):
        self.model = model

    def create_baseline_model(self, model_name):
        if model_name == "reactive":
            return ReactiveController(2, 4, 1, 0.5, dist_threshold1=3, dist_threshold2=5, ignore_colored=True) 

    def step_model(self, sim_msgs):
        return self.model.step(sim_msgs)

    def indicate_episode_end(self, sim_msgs):
        # TODO
        pass

    def set_model_goal(self, bag_idx, bag_step):
        # TODO
        pass

    def run(self):
        bench = self.benchmark
        print("Num tasks: " + str(len(bench.tasks)))

        tasks_goal_bag_idxs = []
        tasks_goal_bag_steps = []

        # TODO

        for bag_fname in bench.bag_files:
            abs_path = bench.datasets_root + bag_fname
            bag = MessageBag(abs_path)
            print("loaded bag: " + abs_path)
            goal_pose = None

            # TODO - play data and also save goal pose (based on all bag idxs and steps)

        sim = NavSim()

        for ti in range(len(bench.tasks)):

            task = bench.tasks[ti]

            print("Starting navtask with index " + str(ti) + ", max_steps: " + str(task.max_steps))

            saveloc = "./tmp/navbench_result" + str(ti) + ".pickle"
            navbag = MessageBag()

            # Teleport to start
            start_pose_msg = bench.task_start_to_msg(task)
            actions = {"/rat1_teleport" : [start_pose_msg]}
            last_obsv, done = sim.step(actions)
            navbag.add_step_msgs(last_obsv)

            for i in range(task.max_steps):    
                twistmsg = self.model.step(last_obsv)
                last_obsv, done = sim.step({"/cmd_vel": [twistmsg]})
                navbag.add_step_msgs(last_obsv)

                if done:
                    break

                # sim.conn.log_connection_stats()

            # Save bag
            print("Saving nav result to " + saveloc)
            navbag.save_to_file(saveloc)


