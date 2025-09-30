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

    # mapname = "simple"
    # start_x = 600
    # start_z = 150
    # start_rot = -np.pi/2

    # mapname = "bigforest"
    # start_x = 500
    # start_z = 500
    # start_rot = -np.pi/2

    mapname = "temeslike"
    start_x = 200
    start_z = 200
    start_rot = 0

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
    monolith.load_map_from_pickle("/home/tom/ratsim_maps/" + mapname + ".pickle")
    print("Map loaded into monolith with " + str(len(monolith.reference_map.places)) + " places.")
    monolith.reference_map.visualize()

    refmap = monolith.reference_map

    # monolith.init_localizer_and_navigator()
    # monolith.sensory_preprocessor = VirtualPclPreprocessor(update_distance_threshold=10.0, occupied_height=5)
    # monolith.set_operation_mode('localization')


