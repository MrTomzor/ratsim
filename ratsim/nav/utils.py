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
import tempfile
import imageio.v3 as iio

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

# def decode_exr_from_base64(base64_str: str) -> np.ndarray:
#     exr_bytes = base64.b64decode(base64_str)
#     with tempfile.NamedTemporaryFile(suffix=".exr") as f:
#         f.write(exr_bytes)
#         f.flush()
#         depth_img = iio.imread(f.name)  # returns float32

#     if depth_img.ndim == 3 and depth_img.shape[2] >= 1:
#         return depth_img[:, :, 0]  # use red channel
#     return depth_img

# def decode_exr_from_base64(base64_str: str) -> np.ndarray:
#     exr_bytes = base64.b64decode(base64_str)
#     f = io.BytesIO(exr_bytes)
#     depth_img = iio.imread(f, format='exr')  # reads directly from bytes

#     # If multichannel, extract first channel (usually depth in R)
#     if depth_img.ndim == 3 and depth_img.shape[2] >= 1:
#         depth_img = depth_img[:, :, 0]

#     return depth_img
def decode_exr_from_base64(base64_str: str) -> np.ndarray:
    exr_bytes = base64.b64decode(base64_str)
    f = io.BytesIO(exr_bytes)
    depth_img = iio.imread(f)  # autodetect EXR from bytes

    if depth_img.ndim == 3 and depth_img.shape[2] >= 1:
        depth_img = depth_img[:, :, 0]  # extract first channel

    return depth_img

def convertRGBDMessageToNumpyFormat(msg: RGBDMessage, visualize: bool = True):
    print("MSG:")
    print(msg)

    # Decode RGB image
    rgb_bytes = base64.b64decode(msg.rgbImageBase64)
    rgb_image = Image.open(io.BytesIO(rgb_bytes)).convert("RGB")
    rgb_np = np.array(rgb_image)

    # Decode Depth image
    depth_bytes = base64.b64decode(msg.depthImageBase64)
    # depth_image = Image.open(io.BytesIO(depth_bytes)).convert("I")  # "I" = 32-bit integer pixels
    # depth_image = iio.imread(io.BytesIO(depth_bytes), extension=".exr") 
    depth_image = decode_exr_from_base64(msg.depthImageBase64)
    depth_np = np.array(depth_image)
    print("Min depth:", np.min(depth_np.flatten()), "Max depth:", np.max(depth_np.flatten()))

    if visualize:
        fig, axs = plt.subplots(1, 2, figsize=(12, 5))
        axs[0].imshow(rgb_np)
        axs[0].set_title("RGB Image")
        axs[0].axis("off")

        im = axs[1].imshow(depth_np, cmap='gray')
        axs[1].set_title("Depth Image")
        axs[1].axis("off")
        plt.colorbar(im, ax=axs[1], shrink=0.6)

        plt.tight_layout()
        plt.show()

    return rgb_np, depth_np
