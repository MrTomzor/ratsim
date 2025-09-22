from ratsim.roslike_unity_connector.connector import *
from ratsim.roslike_unity_connector.message_definitions import *
from ratsim.nav.utils import *
import numpy as np
# TODO - fix relative imports


class OccupancyMapperSliding2D:
    def __init__(self, resolution = 1, map_cells_width = 100):
        # Works in a 2D world, x=right, y=up. 
        # But transforms from Unity coords (x=-left(=-x in Unity) , y = forward (=z in Unity))
        self.map = np.zeros((map_cells_width, map_cells_width), dtype=np.float32)
        self.resolution = resolution
        self.map_center_odomframe = None
        self.map_cells_width = map_cells_width

        pass

    def try_shifting_map(self, newpos):# # #{
        # dx = new_pos[0] - self.map_center_odomframee[0]
        # dy = new_pos[1] - self.map_center_odomframee[1]

        # dx = delta_pos[0]
        # dy = delta_pos[1]
        dx = -(newpos[0] - self.map_center_odomframe[0])
        dy = -(newpos[1] - self.map_center_odomframe[1])

        shift_x = int(dx / self.resolution)
        shift_y = int(dy / self.resolution)

        if shift_x != 0 or shift_y != 0:
            print(f"Shifting map by ({shift_x}, {shift_y}) cells")

            # Shift map contents
            self.map = np.roll(self.map, shift_x, axis=1)  # x → columns
            self.map = np.roll(self.map, shift_y, axis=0)  # y → rows

            # Clear newly revealed cells after rolling
            if shift_x > 0:
                self.map[:, :shift_x] = 0
            elif shift_x < 0:
                self.map[:, shift_x:] = 0

            if shift_y > 0:
                self.map[:shift_y, :] = 0
            elif shift_y < 0:
                self.map[shift_y:, :] = 0


            # new_map = np.zeros_like(self.map)

            # # Compute overlapping region in old and new maps
            # src_x_start = max(0, shift_x)
            # src_x_end   = self.map_cells_width + min(0, shift_x)
            # dst_x_start = max(0, -shift_x)
            # dst_x_end   = self.map_cells_width - max(0, shift_x)

            # src_y_start = max(0, shift_y)
            # src_y_end   = self.map_cells_width + min(0, shift_y)
            # dst_y_start = max(0, -shift_y)
            # dst_y_end   = self.map_cells_width - max(0, shift_y)

            # # Copy overlapping region
            # new_map[dst_y_start:dst_y_end, dst_x_start:dst_x_end] = \
            #     self.map[src_y_start:src_y_end, src_x_start:src_x_end]

            # self.map = new_map

            # self.map_center_odomframe = newpos
            self.map_center_odomframe += np.array([ -shift_x * self.resolution, -shift_y * self.resolution])
# # #}

    def process_lidar_data(self, points_xy_odomframe, pos_odomframe):# # #{
        if not self.map_center_odomframe is None:
            self.try_shifting_map(newpos=pos_odomframe)
        else:
            self.map_center_odomframe = np.array(pos_odomframe)

        self.map = self.map * 0.99

        # Map is centered on current position
        # points are in odom origin

        # Transalte points to map frame (now 0 = map center)
        # points_xy_mapframe = points_xy_odomframe - np.array(pos_odomframe)

        # points_xy_mapframe = points_xy_odomframe - np.array(pos_odomframe)
        points_xy_mapframe = points_xy_odomframe - np.array(self.map_center_odomframe)

        # Convert to map cells
        half_width = (self.map.shape[0] / 2) * self.resolution
        points_xy_mapcells = ((points_xy_mapframe + half_width) / self.resolution).astype(np.int32)
        
        # Handle all points
        for pt in points_xy_mapcells:
            map_x = pt[0] 
            map_y = pt[1] 

            # Set cell to occupied if in bounds
            if 0 <= map_x < self.map.shape[1] and 0 <= map_y < self.map.shape[0]:
                self.map[map_y, map_x] = 1.0

            # Cast ray from origin to point and set cells to free
            #TODO 
            # ray_points = bresenham2d(0, 0, pt[0], pt[1])
# # #}

    def process_ratsim_msgs(self, lidar_msg: Lidar2DMessage, pose_msg :Twist2DMessage):# # #{
        map_y = pose_msg.forward
        map_x = -pose_msg.left


        pcl = lidar2d_to_pointcloud(lidar_msg)
        pcl_world = transform_pointcloud2d(pcl, pose_msg)

        if pcl_world.size > 0:
            # Split into x and z (remember: z is forward)
            lidar_x = -pcl_world[:, 1]
            # lidar_z = pcl_world[:, 0]
            lidar_y = pcl_world[:, 0]
            lidar_xy = np.stack((lidar_x, lidar_y), axis=-1)

            self.process_lidar_data(lidar_xy, (map_x, map_y))
# # #}

    def visualize_map_dynamic(self):# # #{
        import matplotlib.pyplot as plt
        plt.ion()
        if not hasattr(self, 'fig'):
            self.fig, self.ax = plt.subplots()
        img = self.ax.imshow(self.map, cmap='gray', vmin=0, vmax=1)
        plt.show()

        # Compute map center
        center_x = self.map.shape[1] // 2
        center_y = self.map.shape[0] // 2
        
        # Add red center marker (use scatter so it stays above the image)
        if not hasattr(self, 'center_marker'):
            self.center_marker = self.ax.scatter(center_x, self.map.shape[0] - center_y - 1,
                                         c='red', s=30, marker='x')

        # while True:
        # Flip map upside down for visualization
        vismap = np.flipud(self.map)

        img.set_data(vismap)
        plt.pause(0.001)# # #}
