from msnav.monolith import *
import sys

if __name__ == "__main__":
    # mapname = "mini200x200"
    # mapname = "simple"
    # mapname = "bigforest"
    mapname = "temeslike"
    # mapname = "gigascale"


    # num_places = 3000
    num_places = 1000
    desc_square_meters = 100

    if len(sys.argv) > 1:
        mapname = sys.argv[1]

    if len(sys.argv) > 2:
        num_places = int(sys.argv[2])

    maproot = "/home/tom/git/ratsim/unity_maps/" + mapname + "/"

    # automatically get map name as last directory in path

    robotpose = np.eye(4)

    # Init monolith
    def get_uav_pose_in_odomframe_np():
        return robotpose

    monolith = Monolith(uav_pose_odomframe_function=get_uav_pose_in_odomframe_np, databases_path="/home/tom/ratsim_dbs/")
    matplotlib.use("TkAgg")
    # monolith.construct_map_from_satellite_data(maproot, visualize=True)
    # monolith.construct_map_from_satellite_data(maproot, num_places = 2000)
    # monolith.construct_map_from_satellite_data(maproot, num_places = num_places, meters_per_pixel=2, description_square_w_meters = 100, place_dist=30)
    monolith.construct_map_from_satellite_data(maproot, num_places = num_places, meters_per_pixel=2, description_square_w_meters = desc_square_meters, place_dist=30)
    # monolith.reference_map.save_to_pickle("/home/tom/ratsim_maps/map1.pickle")
    monolith.reference_map.save_to_pickle("/home/tom/ratsim_maps/" + mapname + ".pickle")

    monolith.reference_map.visualize_kmeans(n_clusters=5)
    # monolith.reference_map.visualize(show_conns = False,show_hogs = True, show_entropies = False)
    # monolith.reference_map.visualize(show_conns = False,show_entropies = True)


