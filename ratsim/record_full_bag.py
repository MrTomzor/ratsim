from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.noise_models import *

import sys

if __name__ == "__main__":
    sim = NavSim()
    in_bag_filename = sys.argv[1]
    out_bag_filename = in_bag_filename.replace(".pickle","") + "_full.pickle"
    if len(sys.argv) >= 3:
        out_bag_filename = sys.argv[2]
    bag = MessageBag(in_bag_filename)

    # Add noise models
    # sim.add_noise_model("/lidar2d", LidarGaussianNoiseInverseDist(0.001))
    # sim.add_noise_model("/rat1_odom", Odom2DGaussianNoise(0.1, 0.1, 0.1, 1, 0, 0))

    # First step
    sim_start_time = time.time()
    last_obsv = sim.step()
    
    # Teleporting and sensing
    bag2 = MessageBag()

    pose_topic = "/rat1_pose"

    index = 0
    steps_total = len(bag.steps)
    print_period = 50

    for step in bag.steps:
        if not pose_topic in step.keys():
            continue
        pose_msg = step[pose_topic][0]

        actions = {"/rat1_teleport" : [pose_msg]}
        obsv, term = sim.step(actions)
        bag2.add_step_msgs(obsv)
        if term:
            break

        if index % print_period == 0:
            print("Step " + str(index) + "/" + str(steps_total))
            sim.conn.log_connection_stats()
        index += 1

    print("traj replayed, saving full bag")
    print("num steps: " + str(len(bag2.steps)))
    bag2.save_to_file(out_bag_filename)
    print("saved to file: " + out_bag_filename)

    # Print total time and seconds per steps
    sim_end_time = time.time()
    print("Total time: " + str(sim_end_time - sim_start_time) + " seconds")
    print("Seconds per step: " + str((sim_end_time - sim_start_time) / len(bag2.steps)))

