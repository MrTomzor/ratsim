from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *

if __name__ == "__main__":
    sim = NavSim()
    
    # First step
    last_obsv = sim.step()
    sim.enable_human_control()

    while True:
        # lidarmsg = conn.get_received_messages("/lidar2d")[0]
        # twistmsg = reactive_controller.compute_forward_vel_and_angular_vel_for_lidar_msg(lidarmsg)
        # twistmsg = reactive_controller.step(last_obsv)
        last_obsv = sim.step()
        sim.conn.log_connection_stats()

