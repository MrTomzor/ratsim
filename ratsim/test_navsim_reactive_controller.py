from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.utils import convertRGBDMessageToNumpyFormat

if __name__ == "__main__":
    sim = NavSim()
    
    # First step
    last_obsv, done = sim.step()
    rgbd_topic = "/rgbd"

    reactive_controller = ReactiveController(2, 4, 1, 0.5, dist_threshold1=3, dist_threshold2=5, ignore_colored=True) 

    while True:
        # lidarmsg = conn.get_received_messages("/lidar2d")[0]
        # twistmsg = reactive_controller.compute_forward_vel_and_angular_vel_for_lidar_msg(lidarmsg)
        twistmsg = reactive_controller.step(last_obsv)
        last_obsv, done = sim.step({"/cmd_vel": [twistmsg]})

        if rgbd_topic in last_obsv:
            rgbdmsg = last_obsv[rgbd_topic][0]
            # convertRGBDMessageToNumpyFormat(rgbdmsg, visualize=False)
        lidarmsg = last_obsv["/lidar2d"]

        print("Publishing twist message:", twistmsg.forward, twistmsg.left, twistmsg.radiansCounterClockwise)
        sim.conn.log_connection_stats()

