from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *

import sys

if __name__ == "__main__":
    sim = NavSim()
    save_filename = sys.argv[1]
    
    # First step
    last_obsv = sim.step()
    sim.enable_human_control()

    filter_topics = ["/rat1_pose", "/rat1_velocity"]
    
    bag = MessageBag()
    while True:
        # lidarmsg = conn.get_received_messages("/lidar2d")[0]
        # twistmsg = reactive_controller.compute_forward_vel_and_angular_vel_for_lidar_msg(lidarmsg)
        # twistmsg = reactive_controller.step(last_obsv)
        last_obsv, was_timeout = sim.step()
        if was_timeout:
            break

        bag.add_step_msgs(last_obsv, filter_topics)
        sim.conn.log_connection_stats()

    print("loop ended, saving traj")
    print("num steps: " + str(len(bag.steps)))
    bag.save_to_file(save_filename)
    print("saved")

