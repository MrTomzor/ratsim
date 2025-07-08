from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.noise_models import *

def transform_pointcloud2d(points: np.ndarray, pose: Twist2DMessage) -> np.ndarray:
    if points.size == 0:
        return points  # Nothing to transform

    # Get pose values with defaults
    dx = pose.forward if pose.forward is not None else 0.0
    dy = pose.left if pose.left is not None else 0.0
    theta = pose.radiansCounterClockwise if pose.radiansCounterClockwise is not None else 0.0

    # Rotation matrix
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    rotation_matrix = np.array([
        [cos_theta, -sin_theta],
        [sin_theta,  cos_theta]
    ])

    # Apply rotation and then translation
    rotated = points @ rotation_matrix.T
    translated = rotated + np.array([dx, dy])

    return translated

def lidar2d_to_pointcloud(lidar_msg: Lidar2DMessage) -> np.ndarray:
    if not lidar_msg.ranges or lidar_msg.angleIncrementDeg is None or lidar_msg.angleStartDeg is None:
        return np.empty((0, 2))  # Return empty array if input is invalid

    ranges = np.array(lidar_msg.ranges)
    angle_start = np.deg2rad(lidar_msg.angleStartDeg)
    angle_increment = np.deg2rad(lidar_msg.angleIncrementDeg)

    angles = angle_start + np.arange(len(ranges)) * angle_increment

    # Filter out invalid ranges (e.g. None or greater than maxRange)
    # valid_mask = np.isfinite(ranges)
    valid_mask = ranges > 0
    if lidar_msg.maxRange is not None:
        valid_mask &= (ranges <= lidar_msg.maxRange)

    valid_ranges = ranges[valid_mask]
    valid_angles = angles[valid_mask]

    valid_angles = -valid_angles

    forward = valid_ranges * np.cos(valid_angles)
    left = valid_ranges * np.sin(valid_angles)

    return np.stack((forward, left), axis=-1)  # Shape: (N, 2)
