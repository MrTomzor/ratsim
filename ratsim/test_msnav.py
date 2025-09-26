from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.utils import convertRGBDMessageToNumpyFormat
from nav.occupancy_mapping_planning import *
from nav.map_generation import *

from msnav.monolith import *

if __name__ == "__main__":
    maproot = "/home/tom/git/ratsim/unity_maps/miniscale/"
    # maproot = "/home/tom/git/ratsim/unity_maps/ultrascale/"
    # maproot = "/home/tom/git/ratsim/unity_maps/temeslike/"
    # maproot = "/home/tom/git/ratsim/unity_maps/urban/"

    mapgentemplate = MapGenTemplate(maproot, meters_per_pixel=2)
    print("MapGenTemplate created")
    # mapgentemplate.visualize()

    robotpose = np.eye(4)

    # Init monolith
    def get_uav_pose_in_odomframe_np():
        return robotpose

    monolith = Monolith(uav_pose_odomframe_function=get_uav_pose_in_odomframe_np, databases_path="/home/tom/ratsim_dbs/")
    matplotlib.use("TkAgg")
    monolith.construct_map_from_satellite_data(maproot, visualize=True)
    monolith.reference_map.save_to_pickle("/home/tom/ratsim_maps/map1.pickle")
    monolith.init_localizer_and_navigator()

    monolith.set_operation_mode('localization')

    sim = NavSim()
    
    # First step
    mapgenmsg = mapgentemplate.to_ratsim_msg()
    mapgentopic = "/mapgen"
    print("Sending mapgen message")
    last_obsv, done = sim.step({mapgentopic: [mapgenmsg]})

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

