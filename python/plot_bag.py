from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.message_definitions import Twist2DMessage
import matplotlib.pyplot as plt

import sys

if __name__ == "__main__":
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

