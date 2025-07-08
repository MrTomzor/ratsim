from roslike_unity_connector.message_definitions import *
import numpy as np
import copy

class NoiseModel:
    def __init__(self) -> None:
        self.msg_type = None
        pass

    def apply_noise(self, msg ):
        return msg

class LidarGaussianNoiseInverseDist(NoiseModel):
    def __init__(self, sigma_inv_distances) -> None:
        super().__init__()
        self.sigma_inv_distances = sigma_inv_distances

    def apply_noise(self, msg: Lidar2DMessage):
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

        msg.ranges = noisy_ranges.tolist()
        return msg


class Odom2DGaussianNoise(NoiseModel):
    def __init__(self, sigma_forward, sigma_left, sigma_radians, bias1, bias2, bias3) -> None:
        super().__init__()
        self.sigma_forward = sigma_forward
        self.sigma_left = sigma_left 
        self.sigma_radians = sigma_radians 

        self.bias_forward = bias1
        self.bias_left = bias2
        self.bias_radians = bias3

    def apply_noise(self, msg: Twist2DMessage):
        forward = msg.forward
        left = msg.left
        rotation = msg.radiansCounterClockwise

        # Apply Gaussian noise and bias
        noisy_forward = forward + np.random.normal(0, self.sigma_forward) + self.bias_forward
        noisy_left = left + np.random.normal(0, self.sigma_left) + self.bias_left
        noisy_rotation = rotation + np.random.normal(0, self.sigma_radians) + self.bias_radians

        # Update message
        msg.forward = noisy_forward
        msg.left = noisy_left
        msg.radiansCounterClockwise = noisy_rotation

        return msg
