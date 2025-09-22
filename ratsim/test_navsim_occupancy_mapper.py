from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.utils import convertRGBDMessageToNumpyFormat
from nav.occupancy_mapping_planning import *

if __name__ == "__main__":
    sim = NavSim()
    
    # First step
    last_obsv, done = sim.step()
    # rgbd_topic = "/rgbd"
    lidar_topic = "/lidar2d"
    pose_topic = "/rat1_pose"

    mapper = OccupancyMapperSliding2D(resolution=1, map_cells_width=100)
    reactive_controller = ReactiveController(2, 4, 1, 0.5, dist_threshold1=3, dist_threshold2=5, ignore_colored=True) 

    step_count = 0

    while True:
        # lidarmsg = conn.get_received_messages("/lidar2d")[0]
        # twistmsg = reactive_controller.compute_forward_vel_and_angular_vel_for_lidar_msg(lidarmsg)
        twistmsg = reactive_controller.step(last_obsv)
        last_obsv, done = sim.step({"/cmd_vel": [twistmsg]})

        if lidar_topic in last_obsv and pose_topic in last_obsv:
            mapper.process_ratsim_msgs(last_obsv[lidar_topic][0], last_obsv[pose_topic][0])

            if step_count % 20 == 0:
                # mapper.process_ratsim_msgs(last_obsv[lidar_topic][0], last_obsv[pose_topic][0])
                mapper.visualize_map_dynamic()

        print("Publishing twist message:", twistmsg.forward, twistmsg.left, twistmsg.radiansCounterClockwise)
        sim.conn.log_connection_stats()

        step_count += 1

