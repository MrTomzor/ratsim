from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.message_definitions import Twist2DMessage
import matplotlib.pyplot as plt
from nav.utils import *

import sys
import time

def plot_traj():
    save_filename = sys.argv[1]
    
    bag = MessageBag(save_filename)
    print("num steps: " + str(len(bag.steps)))

    z = []
    x = []
    pose_topic = "/rat1_pose"

    for step in bag.steps:
        if not pose_topic in step.keys():
            continue
        pose_msg = step[pose_topic][0]
        z.append(pose_msg.forward)
        x.append(-pose_msg.left)
        # print(step)
    plt.plot(x, z)
    plt.xlabel("x (unity)")
    plt.ylabel("z (unity)")
    plt.gca().set_aspect("equal")
    plt.show()

def plot_data_cont():
    save_filename = sys.argv[1]
    bag = MessageBag(save_filename)
    
    print("num steps:", len(bag.steps))
    
    z = []
    x = []
    pose_topic = "/rat1_pose"
    lidar_topic = "/lidar2d"
    
    plt.ion()  # Turn on interactive mode
    fig, ax = plt.subplots()
    line, = ax.plot([], [], 'bo-')  # Blue circles with lines
    lidar_scatter = ax.scatter([], [], c='r', s=3, label="Lidar")  # Lidar points
    ax.set_xlabel("x (unity)")
    ax.set_ylabel("z (unity)")
    ax.set_aspect("equal")
    ax.legend()
    
    for i, step in enumerate(bag.steps):
        if pose_topic not in step:
            continue
        pose_msg = step[pose_topic][0]
        z.append(pose_msg.forward)
        x.append(-pose_msg.left)
    
        # Draw lidar msg
        if lidar_topic in step:
            print("lidar msg!")
            lidar_msg = step[lidar_topic][0]
            pcl = lidar2d_to_pointcloud(lidar_msg)
            pcl_world = transform_pointcloud2d(pcl, pose_msg)
            # pcl_world = pcl

            # Plot transformed lidar points
            if pcl_world.size > 0:
                print("aa msg!")
                # Split into x and z (remember: z is forward)
                # lidar_x = pcl_world[:, 0]
                # lidar_z = pcl_world[:, 1]
                lidar_x = -pcl_world[:, 1]
                lidar_z = pcl_world[:, 0]
                lidar_scatter.set_offsets(np.c_[lidar_x, lidar_z])

        # Update plot data
        line.set_xdata(x)
        line.set_ydata(z)
    
        # ax.relim()
        # ax.autoscale_view()

        ax.set_xlim(-30, 30)  # x-axis range
        ax.set_ylim(-30, 30)  # z-axis range
    
        plt.draw()
        plt.pause(0.001)  # Allow GUI events to be processed
    
        # Print the current step data
        print(f"Step {i}: x = {x[-1]:.3f}, z = {z[-1]:.3f}")
    
        time.sleep(0.02)  # Sleep for 100 ms between steps

# Keep plot open after loop finishes
plt.ioff()
plt.show()

if __name__ == "__main__":
    plot_data_cont()

