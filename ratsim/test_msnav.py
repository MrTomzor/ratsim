from nav import navsim
from nav.navsim import NavSim
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.utils import convertRGBDMessageToNumpyFormat
from nav.occupancy_mapping_planning import *
from nav.map_generation import *

from msnav.monolith import *


def rotation_matrix_from_rot_around_z(theta):# # #{
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0],
                     [s, c, 0],
                     [0, 0, 1]])
# # #}

class VirtualPclPreprocessor:# # #{
    def __init__(self, update_distance_threshold=1.0, occupied_height = 5):
        self.last_pop_pose = None
        self.last_input_pose = None
        self.ready_to_pop = False
        self.update_distance_threshold = update_distance_threshold
        self.occupied_height = occupied_height
        self.last_occupancy_map = None
        self.last_occupancy_map_odom_center = None
        pass

    def update_occupancy_map_and_center(self, occupancy_map, map_center_odomframe):
        self.last_occupancy_map = occupancy_map
        self.last_occupancy_map_odom_center = map_center_odomframe

    def update_uav_pose_odomframe(self, robotpose):
        self.last_input_pose = robotpose

        # Update the flag for computing pcl data
        if self.last_pop_pose is not None:
            # Calculate translation and rotation between the last pose and the current pose
            translation = np.linalg.norm(robotpose[:3, 3] - self.last_pop_pose[:3, 3])
            # rotation = np.linalg.norm(uav_pose_matrix_np[:3, :3] - self.last_pcl_update_pose_matrix[:3, :3])

            if translation > self.update_distance_threshold:
                # Raise the flag, but dont save the pose yet
                self.ready_to_pop = True

                print("Moved enough! - " + str(translation))
        else:
            self.last_pop_pose = robotpose
        pass

    def pop_current_odomframe_submap_with_pose_matrix_if_new(self):
        if self.ready_to_pop:
            self.ready_to_pop = False
            self.last_pop_pose = self.last_input_pose
            # Return the last pose for which the pcl was computed
            return 42, self.last_pop_pose
        else:
            return None

        pass

    def compute_noncanopy_heightmap(self, submap_odomframe_pcl_np, meters_per_pixel):
        # This is a hack, discard the submap data, use occupancy
        hmap = copy.deepcopy(self.last_occupancy_map)
        hmap[hmap < 0.9] = 0
        hmap[hmap >= 0.9] = self.occupied_height
        return hmap, self.last_occupancy_map_odom_center
# # #}

if __name__ == "__main__":

    # VISU SETTINGS
    visualization_mode = "interactive"
    # visualization_mode = "save"
    # visualization_mode = "none"

    if visualization_mode == "interactive":
        matplotlib.use("TkAgg")
    if visualization_mode == "save" or visualization_mode == "none":
        matplotlib.use("Agg")
    

    # MAP LOADING SETTINGS
    # mapname = "mini200x200"
    # start_x = 100
    # start_z = 100
    # start_rot = -np.pi/2

    # mapname = "simple"
    # start_x = 400
    # start_z = 200
    # start_rot = np.pi/2

    mapname = "simple"
    start_x = 600
    start_z = 150
    start_rot = -np.pi/2

    # mapname = "bigforest"
    # start_x = 500
    # start_z = 500
    # start_rot = -np.pi/2

    # mapname = "temeslike"
    # start_x = 200
    # start_z = 200
    # start_rot = 0

    # mapname = "simple"

    maproot = "/home/tom/git/ratsim/unity_maps/" + mapname + "/"
    mapgentemplate = MapGenTemplate(maproot, meters_per_pixel=2)
    print("MapGenTemplate created")
    # mapgentemplate.visualize()

    robotpose = np.eye(4)

    # Init monolith
    def get_uav_pose_in_odomframe_np():
        return robotpose

    monolith = Monolith(uav_pose_odomframe_function=get_uav_pose_in_odomframe_np, databases_path="/home/tom/ratsim_dbs/")
    # monolith.construct_map_from_satellite_data(maproot, visualize=True)
    # monolith.reference_map.save_to_pickle("/home/tom/ratsim_maps/map1.pickle")
    # monolith.reference_map.load_from_pickle("/home/tom/ratsim_maps/map1.pickle")
    # monolith.load_map_from_pickle("/home/tom/ratsim_maps/map1.pickle")
    monolith.load_map_from_pickle("/home/tom/ratsim_maps/" + mapname + ".pickle")
    # monolith.reference_map.visualize()
    monolith.init_localizer_and_navigator()
    monolith.sensory_preprocessor = VirtualPclPreprocessor(update_distance_threshold=10.0, occupied_height=5)

    monolith.set_operation_mode('localization')

    sim = NavSim()
    
    # First step - load map and teleport to start
    mapgenmsg = mapgentemplate.to_ratsim_msg()
    mapgentopic = "/mapgen"
    teleport_topic = "/rat1_teleport"
    print("Sending mapgen message")
    start_pose_msg = Twist2DMessage()
    start_pose_msg.forward = start_z
    start_pose_msg.left = -start_x
    start_pose_msg.radiansCounterClockwise = start_rot
    last_obsv, done = sim.step({mapgentopic: [mapgenmsg], teleport_topic : [start_pose_msg]})

    # rgbd_topic = "/rgbd"
    lidar_topic = "/lidar2d"
    pose_topic = "/rat1_pose"

    mapper = OccupancyMapperSliding2D(resolution=2, map_cells_width=40)
    # vel1 = 2
    # vel2 = 4
    # angvel1 = 1
    # angvel2 = 0.5
    vel1 = 6
    vel2 = 12
    angvel1 = 2
    angvel2 = 1
    reactive_controller = ReactiveController(vel1, vel2, angvel1, angvel2, dist_threshold1=3, dist_threshold2=5, ignore_colored=True) 


    step_count = 0
    plt.ion()  # turn on interactive mode


    while True:
        # lidarmsg = conn.get_received_messages("/lidar2d")[0]
        # twistmsg = reactive_controller.compute_forward_vel_and_angular_vel_for_lidar_msg(lidarmsg)
        twistmsg = reactive_controller.step(last_obsv)
        last_obsv, done = sim.step({"/cmd_vel": [twistmsg]})

        if lidar_topic in last_obsv and pose_topic in last_obsv:
            # Update robot pose
            pose_twistmsg = last_obsv[pose_topic][0]
            robotpose = np.eye(4)
            robotpose[1, 3] = pose_twistmsg.forward
            robotpose[0, 3] = -pose_twistmsg.left
            robotpose[0:3, 0:3] = rotation_matrix_from_rot_around_z(pose_twistmsg.radiansCounterClockwise)

            # Update local mapper
            mapper.process_ratsim_msgs(last_obsv[lidar_topic][0], last_obsv[pose_topic][0])
            monolith.sensory_preprocessor.update_occupancy_map_and_center(mapper.map, mapper.map_center_odomframe)

            # Update monolith
            monolith.sensory_preprocessor.update_uav_pose_odomframe(robotpose)
            if monolith.sensory_preprocessor.ready_to_pop:

                mapper.visualize_map_dynamic()
                print("MOVED ENOUGH FOR PCL UPDATE")
                monolith.mainloop_iter()

                # Save imgs if requested
                if visualization_mode == "save":
                    names_n_imgs = monolith.get_vis_imgs()
                    for name, img in names_n_imgs:
                        # Save image to file
                        savedir = "/home/tom/testvis/"
                        # add img name and step count to filename
                        filename = savedir + name + "_" + str(step_count) + ".png"
                        plt.imsave(filename, img)

        print("Publishing twist message:", twistmsg.forward, twistmsg.left, twistmsg.radiansCounterClockwise)
        sim.conn.log_connection_stats()

        step_count += 1

