from nav.navsim import NavSim
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from roslike_unity_connector.bag import *
from nav.reactive_controller import *
from nav.navbenchmark import *

if __name__ == "__main__":
    trialfolder = "./trials/blackenv1_trial1/"
    trial = NavBenchmark.from_folder(trialfolder)
    print("Num tasks: " + str(len(trial.tasks)))

    for bag_fname in trial.bag_files:
        abs_path = trialfolder + bag_fname
        bag = MessageBag(abs_path)
        print("loaded bag: " + abs_path)

        # TODO - process bag with model

    sim = NavSim()


    # TODO - init model
    reactive_controller = ReactiveController(2, 4, 1, 0.5, dist_threshold1=3, dist_threshold2=5, ignore_colored=True) 
    task_bags = []

    for ti in range(len(trial.tasks)):

        task = trial.tasks[ti]

        print("Starting navtask with index " + str(ti) + ", max_steps: " + str(task.max_steps))

        saveloc = "./tmp/navtrial_result" + str(ti) + ".pickle"
        navbag = MessageBag()

        # Teleport to start
        start_pose_msg = trial.task_start_to_msg(task)
        actions = {"/rat1_teleport" : [start_pose_msg]}
        last_obsv, done = sim.step(actions)
        navbag.add_step_msgs(last_obsv)

        for i in range(task.max_steps):    
            twistmsg = reactive_controller.step(last_obsv)
            last_obsv, done = sim.step({"/cmd_vel": [twistmsg]})
            navbag.add_step_msgs(last_obsv)

            # print("Publishing twist message:", twistmsg.linear_x, twistmsg.linear_y, twistmsg.angular_z)
            # sim.conn.log_connection_stats()

        # Save bag
        print("Saving nav result to " + saveloc)
        navbag.save_to_file(saveloc)

