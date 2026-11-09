"""Sensed occupancy map as an RL observation ("perfect-SLAM oracle").

The agent's own lidar scans, integrated with its ground-truth pose into a 2D
occupancy grid — the same information the frontier-exploration baseline
builds its map from — rendered as a fixed-size, world-aligned uint8 image:

  channel 0  free fraction      (0..255) of the fine cells under each pixel
  channel 1  occupied fraction  (0..255)
  channel 2  agent marker       (255 on the agent's pixel(s), else 0)

Unknown = neither free nor occupied (both channels low). Fractions rather than
"any occupied fine cell → occupied" so that downsampling cannot close a
corridor narrower than two output pixels.

Geometry: the canvas is square, side = the world's longer extent, centred on
the world origin like ExplorationTracker; a non-square world leaves the
outside strips unknown. Internally the grid is ``size * supersample`` cells per
side and block-averaged down to ``size``. Orientation matches
``ExplorationTracker.to_rgb_image`` / Unity's top-down view (image up = ROS +x,
image left = ROS +y), so a debug PNG of the observation can be compared
directly with a world snapshot.

Collectable reward objects are not written into the grid as obstacles: a ray
whose hit carries the reward semantic class clears the cells along it but
leaves its endpoint untouched — otherwise every cube would remain a permanent
obstacle after pickup (the grid never clears OCCUPIED cells). Other dynamic
objects (rubble, walkers) are NOT handled; this map is only meant for static
worlds.
"""

import numpy as np

from ratsim.task_tracker.exploration_tracker import (
    FREE,
    OCCUPIED,
    ExplorationTracker,
    lidar_angles_ros,
)
from ratsim.transforms import yaw_from_quat


class OccupancyMapObservation:
    N_CHANNELS = 3

    def __init__(
        self,
        world_width: float,
        world_height: float,
        size: int = 128,
        supersample: int = 2,
        reward_descriptor_index: int = 0,
        agent_marker_radius: int = 1,
    ):
        if size < 1 or supersample < 1:
            raise ValueError(f"size and supersample must be >= 1, got {size}, {supersample}")
        self.size = int(size)
        self.supersample = int(supersample)
        # -1 disables the reward-object filter.
        self.reward_descriptor_index = int(reward_descriptor_index)
        self.agent_marker_radius = int(agent_marker_radius)

        self.side = float(max(world_width, world_height))
        fine = self.size * self.supersample
        resolution = self.side / fine
        tracker = ExplorationTracker(self.side, self.side, resolution=resolution)
        if tracker.cells_x != fine:
            # ceil(side / (side / fine)) can land one above `fine` in floating
            # point; nudge the cell size up so the grid is exactly fine x fine.
            tracker = ExplorationTracker(self.side, self.side, resolution=resolution * (1 + 1e-9))
        assert tracker.cells_x == fine and tracker.cells_y == fine, (tracker.cells_x, tracker.cells_y)
        self.tracker = tracker
        self.agent_xy = None

    @property
    def shape(self) -> "tuple[int, int, int]":
        return (self.size, self.size, self.N_CHANNELS)

    @property
    def meters_per_pixel(self) -> float:
        return self.side / self.size

    def reset(self):
        self.tracker.reset()
        self.agent_xy = None

    def update(self, pose_msg, lidar_msg):
        """Integrate one step. ``pose_msg`` is the ground-truth PoseMessage
        (ROS frame), ``lidar_msg`` the Lidar2DMessage. Either may be None, in
        which case the map is left unchanged (the agent marker too, if the pose
        is missing)."""
        if pose_msg is None:
            return
        self.agent_xy = (pose_msg.x, pose_msg.y)
        if lidar_msg is None:
            return
        yaw = yaw_from_quat(pose_msg.qx, pose_msg.qy, pose_msg.qz, pose_msg.qw)
        angle_start, angle_inc = lidar_angles_ros(lidar_msg)
        self.tracker.update_from_lidar(
            agent_x=pose_msg.x,
            agent_y=pose_msg.y,
            agent_yaw=yaw,
            ranges=lidar_msg.ranges,
            angle_start_rad=angle_start,
            angle_increment_rad=angle_inc,
            max_range=lidar_msg.maxRange,
            no_occupy=self._reward_hits(lidar_msg),
        )

    def _reward_hits(self, lidar_msg):
        """Bool per ray: did it hit a reward object? None if unknowable."""
        idx = self.reward_descriptor_index
        desc = lidar_msg.descriptors
        n_rays = len(lidar_msg.ranges)
        if idx < 0 or not desc or n_rays == 0:
            return None
        # Ray-major layout: descriptors[ray * dim + class] (SemanticLidarSensor).
        dim = len(desc) // n_rays
        if idx >= dim:
            return None
        return np.asarray(desc, dtype=np.float32).reshape(n_rays, dim)[:, idx] > 0.5

    def render(self) -> np.ndarray:
        """(size, size, 3) uint8 observation."""
        g = self.tracker.grid  # (rows = ROS y, cols = ROS x)
        s, k = self.size, self.supersample
        img = np.zeros((s, s, self.N_CHANNELS), dtype=np.uint8)
        # Integer block sums, scaled to 0..255 with rounding (k*k fine cells/px).
        kk = k * k
        for ch, value in ((0, FREE), (1, OCCUPIED)):
            mask = (g == value).view(np.uint8)
            # Sum of the k*k strided sub-grids; ~5x faster than a reshape+sum
            # over axes (1, 3) on these sizes.
            count = np.zeros((s, s), dtype=np.uint16)
            for di in range(k):
                for dj in range(k):
                    count += mask[di::k, dj::k]
            img[..., ch] = (count.astype(np.uint32) * 255 + kk // 2) // kk
        if self.agent_xy is not None:
            col, row = self.tracker.world_to_cell(*self.agent_xy)
            col, row = col // k, row // k
            if 0 <= col < s and 0 <= row < s:
                r = self.agent_marker_radius
                img[max(row - r, 0):row + r + 1, max(col - r, 0):col + r + 1, 2] = 255
        # Same transform as ExplorationTracker.to_rgb_image: axis 0 = ROS x
        # flipped (high x at the top), axis 1 = ROS y flipped (high y on the left).
        return np.ascontiguousarray(img.transpose(1, 0, 2)[::-1, ::-1])
