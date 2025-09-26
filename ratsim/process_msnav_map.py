from msnav.monolith import *

if __name__ == "__main__":
    # maproot = "/home/tom/git/ratsim/unity_maps/miniscale/"
    # maproot = "/home/tom/git/ratsim/unity_maps/ultrascale/"
    maproot = "/home/tom/git/ratsim/unity_maps/temeslike/"
    # maproot = "/home/tom/git/ratsim/unity_maps/urban/"

    robotpose = np.eye(4)

    # Init monolith
    def get_uav_pose_in_odomframe_np():
        return robotpose

    monolith = Monolith(uav_pose_odomframe_function=get_uav_pose_in_odomframe_np, databases_path="/home/tom/ratsim_dbs/")
    matplotlib.use("TkAgg")
    # monolith.construct_map_from_satellite_data(maproot, visualize=True)
    monolith.construct_map_from_satellite_data(maproot, visualize=True, num_places = 1000)
    monolith.reference_map.visualize_kmeans(n_clusters=2)

    # monolith.reference_map.save_to_pickle("/home/tom/ratsim_maps/map1.pickle")

