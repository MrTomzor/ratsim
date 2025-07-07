from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *

import sys

if __name__ == "__main__":
    sim = NavSim()
    in_bag_filename = sys.argv[1]
    out_bag_filename = sys.argv[2]
    bag = MessageBag(in_bag_filename)

    # First step
    last_obsv = sim.step()
    sim.enable_human_control()
    
    # Teleporting and sensing
    bag2 = MessageBag()

    pose_topic = "/rat1_pose"
    for step in bag.steps:
        if not pose_topic in step.keys():
            continue
        pose_msg = step[pose_topic][0]

        actions = {"/rat1_teleport" : [pose_msg]}
        obsv, term = sim.step(actions)
        bag2.add_step_msgs(obsv)
        if term:
            break

    print("traj replayed, saving full bag")
    print("num steps: " + str(len(bag2.steps)))
    bag2.save_to_file(out_bag_filename)
    print("saved")

