from roslike_unity_connector.bag import MessageBag
from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *
from nav.noise_models import *
import io
import base64
import numpy as np
from PIL import Image
import io
import matplotlib.pyplot as plt
# import cv2

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

def getLidarValidMask(ranges: np.ndarray, max_range: float) -> np.ndarray:
    valid_mask = ranges > 0
    if max_range is not None:
        valid_mask &= (ranges <= max_range)
    return valid_mask

def visual_tracker_msg_to_pointcloud3d(msg: VisualPointTrackerMessage):
    if not msg.trackedPointsEgocentricFLU: 
        return np.empty((0, 3))  # Return empty array if input is invalid
    num_pts = int(len(msg.trackedPointsEgocentricFLU) / 3)
    points = np.array(msg.trackedPointsEgocentricFLU).reshape((num_pts, 3))
    descriptor_dimension = int(len(msg.trackedPointDescriptors) / num_pts )
    descriptors = np.array(msg.trackedPointDescriptors).reshape((num_pts, descriptor_dimension))

    return points, descriptors  # Shape: (N, 3), (N, D)

def lidar2d_to_pointcloud(lidar_msg: Lidar2DMessage) -> np.ndarray:
    if not lidar_msg.ranges or lidar_msg.angleIncrementDeg is None or lidar_msg.angleStartDeg is None:
        return np.empty((0, 2))  # Return empty array if input is invalid

    ranges = np.array(lidar_msg.ranges)
    angle_start = np.deg2rad(lidar_msg.angleStartDeg)
    angle_increment = np.deg2rad(lidar_msg.angleIncrementDeg)

    angles = angle_start + np.arange(len(ranges)) * angle_increment

    # Filter out invalid ranges (e.g. None or greater than maxRange)
    # valid_mask = np.isfinite(ranges)
    valid_mask = getLidarValidMask(ranges, lidar_msg.maxRange)

    valid_ranges = ranges[valid_mask]
    valid_angles = angles[valid_mask]

    # Flip angles to match Unity's coordinate system
    valid_angles = -valid_angles

    forward = valid_ranges * np.cos(valid_angles)
    left = valid_ranges * np.sin(valid_angles)

    return np.stack((forward, left), axis=-1)  # Shape: (N, 2)

def has_depth(msg: RGBDMessage) -> bool:
    """True iff the message carries a depth image (sensor was configured with captureDepth=true)."""
    return bool(getattr(msg, "depthImageBase64", None))


def convertRGBDMessageToNumpyFormat(msg: RGBDMessage, visualize: bool = True):
    print("MSG:")
    print(msg)

    # Decode RGB image
    rgb_bytes = base64.b64decode(msg.rgbImageBase64)
    rgb_image = Image.open(io.BytesIO(rgb_bytes)).convert("RGB")
    rgb_np = np.array(rgb_image)

    depth_np = None
    if has_depth(msg):
        # Decode 8-bit depth encoded in the alpha channel
        print("MSg reported min and max depth:", msg.minDepth, msg.maxDepth)
        depth_bytes = base64.b64decode(msg.depthImageBase64)
        depth_image = Image.open(io.BytesIO(depth_bytes)).convert("RGBA")
        alpha = np.array(depth_image)[:, :, 3].astype(np.float32) / 255.0
        depth_np = msg.minDepth + (msg.maxDepth - msg.minDepth) * alpha
        print("Decoded Depth Range:", np.min(depth_np), np.max(depth_np))
    else:
        print("RGB-only message (no depth).")

    if visualize:
        if depth_np is not None:
            fig, axs = plt.subplots(1, 2, figsize=(12, 5))
            axs[0].imshow(rgb_np)
            axs[0].set_title("RGB Image")
            axs[0].axis("off")

            im = axs[1].imshow(depth_np, cmap='gray')
            axs[1].set_title("Depth Image (meters)")
            axs[1].axis("off")
            plt.colorbar(im, ax=axs[1], shrink=0.6)
        else:
            fig, ax = plt.subplots(1, 1, figsize=(6, 5))
            ax.imshow(rgb_np)
            ax.set_title("RGB Image (no depth)")
            ax.axis("off")

        plt.tight_layout()
        plt.show()

    return rgb_np, depth_np
