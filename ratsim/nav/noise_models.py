from re import M
from ratsim.roslike_unity_connector.message_definitions import *
import numpy as np
from ratsim.nav.utils import visual_tracker_msg_to_pointcloud3d
import copy

class NoiseModel:
    def __init__(self) -> None:
        self.msg_type = None
        pass

    def apply_noise(self, msg, do_deepcopy=False):
        return msg

class LidarGaussianNoiseInverseDist(NoiseModel):
    def __init__(self, sigma_inv_distances) -> None:
        super().__init__()
        self.sigma_inv_distances = sigma_inv_distances

    def apply_noise(self, msg: Lidar2DMessage, do_deepcopy = False):
        ranges = np.array(msg.ranges)

        # Avoid division by zero (or inf), mask out zero or inf values temporarily
        valid = ranges > 0.0
        inv_ranges = np.zeros_like(ranges)
        inv_ranges[valid] = 1.0 / ranges[valid]

        # Apply Gaussian noise in inverse distance domain
        noise = np.random.normal(loc=0.0, scale=self.sigma_inv_distances, size=ranges.shape)
        inv_ranges_noisy = inv_ranges + noise

        # Convert back to distances, handling division by zero or negative values
        noisy_ranges = np.zeros_like(ranges)
        # Only keep positive inverse distances
        valid_noisy = inv_ranges_noisy > 0.0
        noisy_ranges[valid_noisy] = 1.0 / inv_ranges_noisy[valid_noisy]

        # Optionally, you might want to clamp to max lidar range or set invalids to a default
        # For example: noisy_ranges[~valid_noisy] = float('inf') or max_range

        out_msg = copy.deepcopy(msg) if do_deepcopy else msg

        out_msg.ranges = noisy_ranges.tolist()
        return out_msg

class VisualTrackerNoiseGaussianInverseDist(NoiseModel):
    def __init__(self, sigma_inv_distances) -> None:
        super().__init__()
        self.sigma_inv_distances = sigma_inv_distances

    def apply_noise(self, msg: VisualPointTrackerMessage, do_deepcopy = False):
        # msg pts array is 1D
        pts, _ = visual_tracker_msg_to_pointcloud3d(msg)
        ranges = np.linalg.norm(pts, axis=1)
        dirs = pts / ranges[:, np.newaxis]  # Normalize to get direction vectors

        # Avoid division by zero (or inf), mask out zero or inf values temporarily
        valid = ranges > 0.0
        inv_ranges = np.zeros_like(ranges)
        inv_ranges[valid] = 1.0 / ranges[valid]

        # Apply Gaussian noise in inverse distance domain
        noise = np.random.normal(loc=0.0, scale=self.sigma_inv_distances, size=ranges.shape)
        inv_ranges_noisy = inv_ranges + noise

        # Convert back to distances, handling division by zero or negative values
        noisy_ranges = np.zeros_like(ranges)
        # Only keep positive inverse distances
        valid_noisy = inv_ranges_noisy > 0.0
        noisy_ranges[valid_noisy] = 1.0 / inv_ranges_noisy[valid_noisy]

        # Optionally, you might want to clamp to max lidar range or set invalids to a default
        # For example: noisy_ranges[~valid_noisy] = float('inf') or max_range

        out_msg = copy.deepcopy(msg) if do_deepcopy else msg
        out_pts = dirs * noisy_ranges[:, np.newaxis]  # Reconstruct points from noisy ranges and directions
        out_msg.trackedPointsEgocentricFLU = out_pts.flatten().tolist()  # Flatten to 1D list

        return out_msg


class Odom2DGaussianNoiseCumulativeAbsolute(NoiseModel):
    def __init__(self, sigma_forward, sigma_left, sigma_radians, bias1, bias2, bias3) -> None:
        super().__init__()
        self.sigma_forward = sigma_forward
        self.sigma_left = sigma_left 
        self.sigma_radians = sigma_radians 

        self.bias_forward = bias1
        self.bias_left = bias2
        self.bias_radians = bias3

        # self.cum_error = Twist2DMessage(0, 0, 0)
        self.noised_pose = Twist2DMessage(0, 0, 0)
        self.last_pose_msg = None

    def apply_noise(self, msg: Twist2DMessage, do_deepcopy = False):
        # TODO - have the noise sigmas be RELATIVE to the current rotation
        if self.last_pose_msg is None:
            self.last_pose_msg = copy.deepcopy(msg)
            self.noised_pose = copy.deepcopy(msg)
            out_msg = copy.deepcopy(msg) if do_deepcopy else msg
            print("FIrst msg:")
            print(f"forward: {out_msg.forward}, left: {out_msg.left}, radiansCounterClockwise: {out_msg.radiansCounterClockwise}")
            return out_msg

        delta_forward_world = msg.forward - self.last_pose_msg.forward if self.last_pose_msg else 0
        delta_left_world = msg.left - self.last_pose_msg.left if self.last_pose_msg else 0
        delta_rotation = msg.radiansCounterClockwise - self.last_pose_msg.radiansCounterClockwise if self.last_pose_msg else 0

        # Convert deltas to local frame using the last pose's rotation
        cos_theta = np.cos(self.last_pose_msg.radiansCounterClockwise)
        sin_theta = np.sin(self.last_pose_msg.radiansCounterClockwise)

        # These are like the "unnoised wheel measurements" in the local frame
        delta_forward_local = (cos_theta * delta_forward_world + sin_theta * delta_left_world)
        delta_left_local = (-sin_theta * delta_forward_world + cos_theta * delta_left_world)
        if delta_forward_local != 0 or delta_left_local != 0 or delta_rotation != 0:
            print(f"delta_forward_local: {delta_forward_local}, delta_left_local: {delta_left_local}, delta_rotation: {delta_rotation}")
        else:
            print("No change in pose, skipping noise application.")

        # save the last pose message
        self.last_pose_msg = copy.deepcopy(msg)

        # Modify the rotation to be within [-pi, pi]
        delta_rotation = (delta_rotation + np.pi) % (2 * np.pi) - np.pi

        # Apply Gaussian noise and bias, only if the values are non-zero
        fwd_noise_local = np.random.normal(0, self.sigma_forward) + self.bias_forward if delta_forward_local != 0 else 0
        left_noise_local = np.random.normal(0, self.sigma_left) + self.bias_left if delta_left_local != 0 else 0
        rot_noise_local = np.random.normal(0, self.sigma_radians) + self.bias_radians if delta_rotation != 0 else 0

        noised_delta_forward = delta_forward_local + fwd_noise_local
        noised_delta_left = delta_left_local + left_noise_local
        noised_delta_rotation = delta_rotation + rot_noise_local

        corrupted_cos_theta = np.cos(-self.noised_pose.radiansCounterClockwise)
        corrupted_sin_theta = np.sin(-self.noised_pose.radiansCounterClockwise)

        noised_delta_forward_world = (corrupted_cos_theta * noised_delta_forward + corrupted_sin_theta * noised_delta_left)
        noised_delta_left_world = (-corrupted_sin_theta * noised_delta_forward + corrupted_cos_theta * noised_delta_left)

        self.noised_pose.forward += noised_delta_forward_world
        self.noised_pose.left += noised_delta_left_world
        self.noised_pose.radiansCounterClockwise = self.noised_pose.radiansCounterClockwise + noised_delta_rotation        # self.noised_pose.radiansCounterClockwise = (self.noised_pose.radiansCounterClockwise + noised_delta_rotation + np.pi) % (2 * np.pi) - np.pi

        # new_noised_pose.forward = self.noised_pose.forward + delta_forward_local + fwd_noise
        



        # self.cum_error.forward += fwd_noise
        # self.cum_error.left += left_noise
        # self.cum_error.radiansCounterClockwise += rot_noise


        out_msg = copy.deepcopy(msg) if do_deepcopy else msg

        # out_msg.forward = msg.forward + self.cum_error.forward
        # out_msg.left = msg.left + self.cum_error.left
        # out_msg.radiansCounterClockwise = msg.radiansCounterClockwise + self.cum_error.radiansCounterClockwise

        out_msg.forward = self.noised_pose.forward
        out_msg.left = self.noised_pose.left
        out_msg.radiansCounterClockwise = self.noised_pose.radiansCounterClockwise

        return out_msg


class Odom2DGaussianNoise(NoiseModel):
    def __init__(self, sigma_forward, sigma_left, sigma_radians, bias1, bias2, bias3) -> None:
        super().__init__()
        self.sigma_forward = sigma_forward
        self.sigma_left = sigma_left 
        self.sigma_radians = sigma_radians 

        self.bias_forward = bias1
        self.bias_left = bias2
        self.bias_radians = bias3

    def apply_noise(self, msg: Twist2DMessage, do_deepcopy = False):
        forward = msg.forward
        left = msg.left
        rotation = msg.radiansCounterClockwise

        # Apply Gaussian noise and bias
        noisy_forward = forward + np.random.normal(0, self.sigma_forward) + self.bias_forward
        noisy_left = left + np.random.normal(0, self.sigma_left) + self.bias_left
        noisy_rotation = rotation + np.random.normal(0, self.sigma_radians) + self.bias_radians

        # Update message
        out_msg = copy.deepcopy(msg) if do_deepcopy else msg
        out_msg.forward = noisy_forward
        out_msg.left = noisy_left
        out_msg.radiansCounterClockwise = noisy_rotation

        return msg
