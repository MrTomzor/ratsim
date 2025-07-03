from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
import numpy as np
# TODO - fix relative imports

class ReactiveController:
    def __init__(self, vel1, vel2, angvel1, angvel2, dist_threshold1 = 5, dist_threshold2 = 30, ignore_colored = False):
        self.vel1 = vel1
        self.vel2 = vel2
        self.angvel1 = angvel1
        self.angvel2 = angvel2
        self.dist_threshold1 = dist_threshold1
        self.dist_threshold2 = dist_threshold2
        self.ignore_colored = ignore_colored
        pass

    def compute_forward_vel_and_angular_vel_for_lidar_msg(self, lidar_msg):
        left_min_dist, front_min_dist, right_min_dist = self.compute_sector_dists(lidar_msg)
        secdists = np.array([left_min_dist, front_min_dist, right_min_dist])

        any_in_dist2 = np.any(secdists < self.dist_threshold2)
        any_in_dist1 = np.any(secdists < self.dist_threshold1)

        res = Twist2DMessage(0, 0, 0)

        if not any_in_dist2:
            res.forward = self.vel2
            res.radiansCounterClockwise = 0
        else:
            if not any_in_dist1: 
                turn_angrate = 0
                if left_min_dist < self.dist_threshold2:
                    turn_angrate -= self.angvel2
                if right_min_dist < self.dist_threshold2:
                    turn_angrate += self.angvel2
                if front_min_dist < self.dist_threshold1:
                    res.forward = self.vel1
                else:
                    res.forward = self.vel2

                res.radiansCounterClockwise = turn_angrate
            else:
                turn_angrate = 0
                if left_min_dist < self.dist_threshold1:
                    turn_angrate -= self.angvel1
                if right_min_dist < self.dist_threshold1:
                    turn_angrate += self.angvel1
                if front_min_dist < self.dist_threshold1:
                    res.forward = 0
                else:
                    res.forward = self.vel1

                if res.forward == 0 and turn_angrate == 0:
                    turn_angrate = self.angvel1

                res.radiansCounterClockwise = turn_angrate
        return res

    def compute_sector_dists(self, lidar_msg: Lidar2DMessage, front_sector_width_deg = 60):
        left_min_dist = np.inf
        right_min_dist = np.inf
        front_min_dist = np.inf

        num_rays = len(lidar_msg.ranges)
        num_dims = (int)(len(lidar_msg.descriptors) / len(lidar_msg.ranges))

        descs = np.array(lidar_msg.descriptors).reshape((num_rays, num_dims))


        for i in range(num_rays):
            angle = lidar_msg.angleStartDeg + i * lidar_msg.angleIncrementDeg
            angle = -angle  # because Unity Y rotation is clockwise, but we want counter-clockwise

            distance = lidar_msg.ranges[i]
            if distance < 0:
                continue

            if self.ignore_colored:
                desc = descs[i]
                if np.linalg.norm(desc) > 0.1:
                    continue

            if -front_sector_width_deg / 2 <= angle <= front_sector_width_deg / 2:
                if front_min_dist is None or distance < front_min_dist:
                    front_min_dist = distance
            elif -180 <= angle < -180 + front_sector_width_deg / 2 or 180 - front_sector_width_deg / 2 < angle <= 180:
                if left_min_dist is None or distance < left_min_dist:
                    left_min_dist = distance
            elif -180 + front_sector_width_deg / 2 < angle < 180 - front_sector_width_deg / 2:
                if right_min_dist is None or distance < right_min_dist:
                    right_min_dist = distance

        return left_min_dist, front_min_dist, right_min_dist

