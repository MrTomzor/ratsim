"""Unit tests for OccupancyMapObservation (pure numpy, no Unity needed).

    python tests/test_occupancy_map_obs.py   (or python -m pytest ...)
"""
from types import SimpleNamespace

import math

import numpy as np

from ratsim.task_tracker.occupancy_map_obs import OccupancyMapObservation


def pose(x, y, yaw=0.0):
    return SimpleNamespace(x=x, y=y, z=0.0, qx=0.0, qy=0.0,
                           qz=math.sin(yaw / 2), qw=math.cos(yaw / 2))


def lidar(ranges, start_deg=0, inc_deg=10, max_range=20.0, descriptors=None):
    # Unity convention: angle 0 = forward, positive = to the right.
    return SimpleNamespace(ranges=list(ranges), descriptors=descriptors,
                           angleStartDeg=start_deg, angleIncrementDeg=inc_deg,
                           maxRange=max_range)


def occupied_pixels(img):
    return {tuple(p) for p in np.argwhere(img[:, :, 1] > 0)}


def test_shape_and_dtype():
    m = OccupancyMapObservation(200.0, 200.0, size=128, supersample=2)
    img = m.render()
    assert img.shape == (128, 128, 3) and img.dtype == np.uint8
    assert m.tracker.grid.shape == (256, 256)
    assert not img.any()  # nothing known, no agent yet


def test_agent_marker_orientation():
    # Image up = ROS +x, image left = ROS +y (Unity top-down view).
    m = OccupancyMapObservation(200.0, 200.0, size=128, agent_marker_radius=0)
    m.update(pose(80.0, 0.0), None)
    (r, c), = np.argwhere(m.render()[:, :, 2] == 255)
    assert r < 20 and abs(c - 64) <= 1
    m.update(pose(0.0, 80.0), None)
    (r, c), = np.argwhere(m.render()[:, :, 2] == 255)
    assert c < 20 and abs(r - 64) <= 1


def test_forward_hit_is_occupied_ahead_and_free_between():
    m = OccupancyMapObservation(200.0, 200.0, size=100, supersample=1)  # 2 m/px
    m.update(pose(0.0, 0.0, yaw=0.0), lidar([10.0]))
    img = m.render()
    (r, c), = occupied_pixels(img)
    # 10 m ahead (ROS +x = up) of the centre pixel, 5 px at 2 m/px.
    assert abs(r - (50 - 5)) <= 1 and abs(c - 50) <= 1
    assert img[r + 2, c, 0] == 255  # free on the way


def test_right_ray_lands_on_the_right():
    # Unity +90 deg = agent's right = ROS -y = image right.
    m = OccupancyMapObservation(200.0, 200.0, size=100, supersample=1)
    m.update(pose(0.0, 0.0), lidar([10.0], start_deg=90))
    (r, c), = occupied_pixels(m.render())
    assert c > 50 and abs(r - 50) <= 1


def test_reward_hits_are_not_obstacles():
    m = OccupancyMapObservation(200.0, 200.0, size=100, supersample=1)
    # two rays: forward hits a reward object (class 0), right hits a wall (class 1)
    desc = [1.0, 0.0,   0.0, 1.0]
    m.update(pose(0.0, 0.0), lidar([10.0, 10.0], start_deg=0, inc_deg=90, descriptors=desc))
    occ = occupied_pixels(m.render())
    assert len(occ) == 1 and next(iter(occ))[1] > 50
    # filter disabled -> both rays leave an obstacle
    m2 = OccupancyMapObservation(200.0, 200.0, size=100, supersample=1, reward_descriptor_index=-1)
    m2.update(pose(0.0, 0.0), lidar([10.0, 10.0], start_deg=0, inc_deg=90, descriptors=desc))
    assert len(occupied_pixels(m2.render())) == 2


def test_fractions_survive_downsampling():
    m = OccupancyMapObservation(200.0, 200.0, size=100, supersample=4)
    m.update(pose(0.0, 0.0), lidar([3.0]))
    img = m.render()
    # the occupied pixel is only partly occupied (1 of 16 fine cells)
    assert 0 < img[:, :, 1].max() < 255


def test_non_square_world_uses_longer_side():
    m = OccupancyMapObservation(300.0, 62.0, size=128)
    assert m.side == 300.0 and m.render().shape == (128, 128, 3)
    assert math.isclose(m.meters_per_pixel, 300.0 / 128)


def test_reset_clears():
    m = OccupancyMapObservation(200.0, 200.0, size=64)
    m.update(pose(0.0, 0.0), lidar([5.0]))
    assert m.render().any()
    m.reset()
    assert not m.render().any()


if __name__ == "__main__":
    # No pytest in the project venvs: `python tests/test_occupancy_map_obs.py`.
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"ok  {name}")
    print(f"{len(tests)} passed")
