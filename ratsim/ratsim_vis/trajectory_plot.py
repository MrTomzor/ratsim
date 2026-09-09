"""Draw agent trajectories on a top-down view of a world.

Trajectories are the arrays ``TaskTracker.get_trajectory()`` produces (ROS
frame). The plot is drawn in Unity's top-down frame so it matches the scene
view and the exploration-grid image: image right = Unity +X = ROS −y, image up
= Unity +Z = ROS +x. World bounds (``world_bounds/width`` along Unity X,
``world_bounds/height`` along Unity Z) are centred on the origin.

Two background modes:

* none (blank slate) — axes are in metres, limited to the world bounds;
* an image with a camera matrix — a rendered snapshot from Unity
  (``WorldSnapshot.cs``, fetched by ``ratsim.world_snapshot``; the saved
  ``.json`` sidecar carries the matrix). ``view_proj`` is the camera's 4x4
  view-projection matrix (row-major, Unity convention, clip = VP · [x y z 1])
  and the trajectory is projected into pixel space with
  :func:`project_to_pixels`. Orthographic top-down, tilted orthographic
  (isometric) and perspective cameras all go through the same path.

Usage::

    fig, ax = plt.subplots()
    plot_trajectories(ax, [{"xyz": t["xyz"], "steps": t["steps"],
                            "pickup_steps": t["pickup_steps"], "label": "ppo"}],
                      world_bounds=(120, 120))
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


# ─────────────────────────────────────────────
#  Frames
# ─────────────────────────────────────────────

def ros_to_unity(xyz: np.ndarray) -> np.ndarray:
    """(N,3) ROS (x fwd, y left, z up) → (N,3) Unity (x right, y up, z fwd)."""
    xyz = np.asarray(xyz, dtype=np.float64).reshape(-1, 3)
    return np.stack([-xyz[:, 1], xyz[:, 2], xyz[:, 0]], axis=1)


def ros_to_unity_xz(xyz: np.ndarray) -> np.ndarray:
    """(N,3) ROS → (N,2) Unity top-down coordinates (X right, Z up)."""
    u = ros_to_unity(xyz)
    return u[:, [0, 2]]


def project_to_pixels(xyz_ros: np.ndarray, view_proj: np.ndarray,
                      width: int, height: int) -> np.ndarray:
    """Project ROS-frame points through a Unity view-projection matrix.

    Returns (N,2) pixel coordinates with (0,0) at the image's top-left, i.e.
    directly usable on an ``imshow`` of the rendered image. Points behind the
    camera get NaN so they break the line rather than wrap around.
    """
    vp = np.asarray(view_proj, dtype=np.float64).reshape(4, 4)
    u = ros_to_unity(xyz_ros)
    hom = np.concatenate([u, np.ones((len(u), 1))], axis=1)
    clip = hom @ vp.T
    w = clip[:, 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        ndc = clip[:, :2] / w[:, None]
    px = (ndc[:, 0] * 0.5 + 0.5) * width
    py = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * height
    out = np.stack([px, py], axis=1)
    out[w <= 0] = np.nan
    return out


# ─────────────────────────────────────────────
#  Plotting
# ─────────────────────────────────────────────

def default_colors(n: int) -> list:
    import matplotlib.pyplot as plt
    cmap = plt.colormaps.get_cmap("tab10")
    return [cmap(i % 10) for i in range(n)]


def plot_trajectories(
    ax,
    trajs: Sequence[dict],
    world_bounds: Optional[tuple] = None,
    background: Optional[np.ndarray] = None,
    view_proj: Optional[np.ndarray] = None,
    colour_by_time: bool = False,
    subsample: int = 1,
    show_pickups: bool = True,
    show_start_end: bool = True,
    linewidth: float = 1.2,
    alpha: float = 0.9,
    legend: bool = False,
    title: Optional[str] = None,
) -> None:
    """Draw every trajectory in ``trajs`` on ``ax``.

    Each entry: ``{"xyz": (N,3) ROS, "steps": (N,), "pickup_steps": (K,),
    "label": str (optional), "color": any matplotlib colour (optional)}``.

    ``world_bounds=(width, height)`` in metres sets the axes limits (blank
    slate). With ``background`` (H,W,3 image) and ``view_proj`` the axes are
    in pixels and the image is drawn underneath.
    """
    from matplotlib.collections import LineCollection

    use_pixels = background is not None and view_proj is not None
    if background is not None:
        ax.imshow(background, zorder=0)
        h, w = background.shape[:2]
    elif world_bounds is not None:
        wb_w, wb_h = float(world_bounds[0]), float(world_bounds[1])
        ax.set_xlim(-wb_w / 2, wb_w / 2)
        ax.set_ylim(-wb_h / 2, wb_h / 2)
        ax.add_patch(_bounds_patch(wb_w, wb_h))

    colors = default_colors(len(trajs))
    for i, t in enumerate(trajs):
        xyz = np.asarray(t["xyz"], dtype=np.float64).reshape(-1, 3)
        if len(xyz) == 0:
            continue
        steps = np.asarray(t.get("steps", np.arange(len(xyz))))
        sub = max(1, int(subsample))
        keep = np.arange(len(xyz))[::sub]
        if keep[-1] != len(xyz) - 1:
            keep = np.append(keep, len(xyz) - 1)
        xyz_k, steps_k = xyz[keep], steps[keep]

        if use_pixels:
            pts = project_to_pixels(xyz_k, view_proj, w, h)
        else:
            pts = ros_to_unity_xz(xyz_k)

        color = t.get("color", colors[i])
        label = t.get("label", None)

        if colour_by_time and len(pts) > 1:
            segs = np.stack([pts[:-1], pts[1:]], axis=1)
            lc = LineCollection(segs, cmap="viridis", linewidths=linewidth, alpha=alpha, zorder=2)
            lc.set_array(np.linspace(0, 1, len(segs)))
            ax.add_collection(lc)
            if label:
                ax.plot([], [], color="k", lw=linewidth, label=label)
        else:
            ax.plot(pts[:, 0], pts[:, 1], color=color, lw=linewidth, alpha=alpha,
                    label=label, zorder=2)

        if show_start_end:
            ax.plot(pts[0, 0], pts[0, 1], marker="o", ms=5, color=color,
                    mec="k", mew=0.6, zorder=4)
            ax.plot(pts[-1, 0], pts[-1, 1], marker="s", ms=5, color=color,
                    mec="k", mew=0.6, zorder=4)

        if show_pickups:
            pk = np.asarray(t.get("pickup_steps", []), dtype=np.int64)
            if pk.size:
                idx = np.searchsorted(steps, pk).clip(0, len(xyz) - 1)
                p_xyz = xyz[idx]
                p_pts = (project_to_pixels(p_xyz, view_proj, w, h) if use_pixels
                         else ros_to_unity_xz(p_xyz))
                ax.plot(p_pts[:, 0], p_pts[:, 1], linestyle="none", marker="*",
                        ms=8, color=color, mec="k", mew=0.5, zorder=5)

    if use_pixels:
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        ax.set_aspect("equal")
        ax.set_xlabel("x (Unity, m)")
        ax.set_ylabel("z (Unity, m)")
    if title:
        ax.set_title(title)
    if legend:
        ax.legend(loc="upper right", fontsize="small")


def _bounds_patch(width: float, height: float):
    from matplotlib.patches import Rectangle
    return Rectangle((-width / 2, -height / 2), width, height, fill=False,
                     ec="0.5", lw=0.8, ls="--", zorder=1)
