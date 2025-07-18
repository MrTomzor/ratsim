from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.noise_models import *

import sys

if __name__ == "__main__":
    sim = NavSim(dont_connect=True)
    in_bag_filename = sys.argv[1]

    out_bag_filename = in_bag_filename.replace(".pickle","") + "_noised.pickle"
    if len(sys.argv) >= 3:
        out_bag_filename = sys.argv[2]
    bag = MessageBag(in_bag_filename)
    bag2 = MessageBag()

    # Add noise models
    # sim.add_noise_model("/lidar2d", LidarGaussianNoiseInverseDist(0.001))
    sim.add_noise_model("/lidar2d", LidarGaussianNoiseInverseDist(0.0003))
    # sim.add_noise_model("/rat1_odom", Odom2DGaussianNoise(0.1, 0.1, 0.1, 1, 0, 0))
    # sim.add_noise_model("/rat1_pose", Odom2DGaussianNoiseCumulativeAbsolute(0.3, 0.5, 1, 0, 0, 0), new_topic="/rat1_pose_noised")
    sim.add_noise_model("/rat1_pose", Odom2DGaussianNoiseCumulativeAbsolute(1, 1, 1, 1, 0, 0), new_topic="/rat1_pose_noised")

    pose_topic = "/rat1_pose"
    for step in bag.steps:
        step2 = sim.apply_noise_models(step)
        bag2.add_step_msgs(step2)

    print("traj replayed and noised, saving full bag to file: " + out_bag_filename)
    print("num steps: " + str(len(bag2.steps)))
    bag2.save_to_file(out_bag_filename)
    print("saved")

