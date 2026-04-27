"""
Step the simulator as fast as possible and report FPS.

Usage:
    python -m ratsim.fps_test
    python -m ratsim.fps_test --world hilly_forest --agent sphereagent_rgbd
    python -m ratsim.fps_test --agent sphereagent_rgbd --visualize-rgbd

With --visualize-rgbd, pops a non-blocking window showing the latest RGB+depth
frame published by any RGBD sensor in the sim. Prints an error and exits if no
RGBD data is observed within a short grace period.
"""

import argparse
import base64
import io
import time

import numpy as np

from ratsim.roslike_unity_connector.connector import RoslikeUnityConnector
from ratsim.roslike_unity_connector.message_definitions import (
    BoolMessage,
    RGBDMessage,
    StringMessage,
)
from ratsim.config_blender import blend_presets, to_entries_json


class RGBDViewer:
    """Non-blocking matplotlib viewer for the latest RGBD frame.

    Shaped after ExplorationViewer: tries to switch to an interactive backend
    if the current one is headless, disables itself cleanly if no display is
    available or the user closes the window.
    """

    def __init__(self, title: str = "RGBD", draw_every: int = 1):
        self.enabled = True
        self.draw_every = max(1, int(draw_every))
        self._tick = 0
        self._fig = None
        self._rgb_im = None
        self._depth_im = None
        self._title_text = title

        try:
            import matplotlib
            NON_INTERACTIVE = {
                "agg", "pdf", "ps", "svg", "template", "cairo", "pgf",
                "module://matplotlib_inline.backend_inline",
            }

            cur_backend = matplotlib.get_backend().lower()
            if cur_backend in NON_INTERACTIVE:
                for backend in ("TkAgg", "Qt5Agg", "QtAgg"):
                    try:
                        matplotlib.use(backend, force=True)
                        break
                    except Exception:
                        continue
            import matplotlib.pyplot as plt

            backend = matplotlib.get_backend()
            if backend.lower() in NON_INTERACTIVE:
                print(
                    f"[RGBDViewer] non-interactive backend '{backend}' — "
                    f"no window will appear. Install python3-tk or a Qt binding "
                    f"to enable the live viewer, or run on a machine with a display."
                )
                self.enabled = False
                return

            plt.ion()
            self._plt = plt
            # Lazy-create the figure on first update so we know whether the
            # frame has depth (2 axes) or RGB-only (1 axis).
            self._fig = None
            self._ax_rgb = None
            self._ax_depth = None

            self._on_close_cb = None
            print(f"[RGBDViewer] active with backend={backend}")
        except Exception as exc:
            print(f"[RGBDViewer] disabled: {exc}")
            self.enabled = False

    def _ensure_figure(self, have_depth: bool):
        if self._fig is not None:
            return
        ncols = 2 if have_depth else 1
        figsize = (10, 5) if have_depth else (6, 5)
        fig, axes = self._plt.subplots(1, ncols, figsize=figsize, num=self._title_text)
        if ncols == 1:
            self._ax_rgb = axes
            self._ax_depth = None
        else:
            self._ax_rgb, self._ax_depth = axes
        self._ax_rgb.set_title("RGB")
        self._ax_rgb.set_xticks([])
        self._ax_rgb.set_yticks([])
        if self._ax_depth is not None:
            self._ax_depth.set_title("Depth")
            self._ax_depth.set_xticks([])
            self._ax_depth.set_yticks([])
        fig.tight_layout()

        def _on_close(event):
            if self.enabled:
                print("[RGBDViewer] window closed — disabling.")
            self.enabled = False
        fig.canvas.mpl_connect("close_event", _on_close)

        self._fig = fig
        self._plt.show(block=False)
        self._plt.pause(0.05)

    def update(self, rgb_np: np.ndarray, depth_np, min_depth: float, max_depth: float):
        """depth_np may be None for RGB-only frames."""
        if not self.enabled:
            return
        self._tick += 1
        if self._tick % self.draw_every != 0:
            return
        try:
            self._ensure_figure(have_depth=depth_np is not None)
            if self._rgb_im is None:
                self._rgb_im = self._ax_rgb.imshow(rgb_np, interpolation="nearest")
            else:
                self._rgb_im.set_data(rgb_np)

            if depth_np is not None and self._ax_depth is not None:
                if self._depth_im is None:
                    self._depth_im = self._ax_depth.imshow(
                        depth_np, cmap="gray", vmin=min_depth, vmax=max_depth,
                        interpolation="nearest",
                    )
                else:
                    self._depth_im.set_data(depth_np)
                    self._depth_im.set_clim(vmin=min_depth, vmax=max_depth)
                self._ax_depth.set_title(f"Depth [{min_depth:.2f}, {max_depth:.2f}] m")

            self._fig.canvas.draw_idle()
            self._plt.pause(0.001)
        except Exception as exc:
            print(f"[RGBDViewer] draw failed, disabling: {exc}")
            self.enabled = False

    def close(self):
        if self._fig is None:
            return
        try:
            self._plt.close(self._fig)
        except Exception:
            pass


def _decode_rgbd(msg: RGBDMessage):
    """Returns (rgb_np, depth_np or None). depth is None when the sensor was
    configured with captureDepth=false (depthImageBase64 empty)."""
    from PIL import Image
    rgb_bytes = base64.b64decode(msg.rgbImageBase64)
    rgb_np = np.array(Image.open(io.BytesIO(rgb_bytes)).convert("RGB"))
    if not msg.depthImageBase64:
        return rgb_np, None
    depth_bytes = base64.b64decode(msg.depthImageBase64)
    depth_rgba = np.array(Image.open(io.BytesIO(depth_bytes)).convert("RGBA"))
    alpha = depth_rgba[:, :, 3].astype(np.float32) / 255.0
    depth_np = msg.minDepth + (msg.maxDepth - msg.minDepth) * alpha
    return rgb_np, depth_np


def _find_rgbd(msgs: dict):
    """Return (topic, latest RGBDMessage) or (None, None) if none present."""
    for topic, msg_list in msgs.items():
        if not msg_list:
            continue
        last = msg_list[-1]
        if isinstance(last, RGBDMessage):
            return topic, last
    return None, None


def run_fps_test(
    conn: RoslikeUnityConnector,
    world_config: dict,
    agent_config: dict,
    seed: int | None = None,
    max_steps: int = 0,
    report_every: int = 100,
    visualize_rgbd: bool = False,
    rgbd_grace_steps: int = 50,
) -> dict:
    """Step the sim as fast as possible and measure FPS.

    Runs one long episode. Stops on max_steps (if > 0) or KeyboardInterrupt.
    If visualize_rgbd is True, requires at least one RGBDMessage within the
    first rgbd_grace_steps steps; otherwise raises RuntimeError.
    """
    cfg = dict(world_config)
    if seed is not None:
        cfg["seed"] = seed

    conn.publish(StringMessage(data=to_entries_json(cfg)), "/sim_control/world_config")
    conn.publish(BoolMessage(data=True), "/sim_control/reset_episode")
    conn.send_messages_and_step(enable_physics_step=True)
    conn.read_messages_from_unity()
    conn.process_worldgen_status()

    viewer = RGBDViewer() if visualize_rgbd else None
    saw_rgbd = False
    rgbd_topic = None

    step_count = 0
    window_start = time.perf_counter()
    window_steps = 0
    window_bytes = 0
    run_start = time.perf_counter()
    total_bytes = 0
    peak_step_bytes = 0

    print(f"FPS test running. Max steps: {max_steps if max_steps > 0 else 'unlimited'}. "
          f"Press Ctrl+C to stop.")

    try:
        while True:
            conn.send_messages_and_step(enable_physics_step=True)
            msgs = conn.read_messages_from_unity()
            step_count += 1
            window_steps += 1
            step_bytes = getattr(conn, "last_frame_recv_bytes", 0)
            window_bytes += step_bytes
            total_bytes += step_bytes
            if step_bytes > peak_step_bytes:
                peak_step_bytes = step_bytes

            if visualize_rgbd:
                topic, rgbd = _find_rgbd(msgs)
                if rgbd is not None:
                    if not saw_rgbd:
                        rgbd_topic = topic
                        saw_rgbd = True
                        print(f"[fps_test] found RGBD data on topic '{topic}'")
                    try:
                        rgb_np, depth_np = _decode_rgbd(rgbd)
                        if viewer is not None:
                            viewer.update(rgb_np, depth_np, rgbd.minDepth, rgbd.maxDepth)
                    except Exception as exc:
                        print(f"[fps_test] failed to decode RGBD frame: {exc}")
                elif not saw_rgbd and step_count >= rgbd_grace_steps:
                    raise RuntimeError(
                        f"--visualize-rgbd requested but no RGBDMessage received "
                        f"after {rgbd_grace_steps} steps. Does the selected agent "
                        f"preset include an 'rgbd' sensor?"
                    )

            if step_count % report_every == 0:
                now = time.perf_counter()
                window_dt = now - window_start
                window_fps = window_steps / window_dt if window_dt > 0 else 0.0
                total_dt = now - run_start
                mean_fps = step_count / total_dt if total_dt > 0 else 0.0
                window_mb_per_step = (window_bytes / window_steps) / 1e6 if window_steps else 0.0
                window_mb_per_s = (window_bytes / window_dt) / 1e6 if window_dt > 0 else 0.0
                print(f"step {step_count}: last {window_steps} steps @ {window_fps:.1f} FPS "
                      f"(mean {mean_fps:.1f} FPS) | "
                      f"recv {window_mb_per_step:.3f} MB/step "
                      f"({window_mb_per_s:.2f} MB/s, peak {peak_step_bytes/1e6:.3f} MB/step)")
                window_start = now
                window_steps = 0
                window_bytes = 0

            if max_steps > 0 and step_count >= max_steps:
                break
    except KeyboardInterrupt:
        print("\n[fps_test] interrupted by user.")
    finally:
        if viewer is not None:
            viewer.close()

    total_dt = time.perf_counter() - run_start
    mean_fps = step_count / total_dt if total_dt > 0 else 0.0
    mean_mb_per_step = (total_bytes / step_count) / 1e6 if step_count else 0.0
    mean_mb_per_s = (total_bytes / total_dt) / 1e6 if total_dt > 0 else 0.0
    return {
        "steps": step_count,
        "wall_seconds": total_dt,
        "mean_fps": mean_fps,
        "total_recv_bytes": total_bytes,
        "mean_recv_mb_per_step": mean_mb_per_step,
        "mean_recv_mb_per_s": mean_mb_per_s,
        "peak_recv_bytes_per_step": peak_step_bytes,
        "rgbd_topic": rgbd_topic,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Step the sim as fast as possible and measure FPS."
    )
    parser.add_argument("--world", default="default")
    parser.add_argument("--agent", default="sphereagent_2d_lidar")
    parser.add_argument("--task", default="default",
                        help="Task preset (loaded for parity with human_control_test; "
                             "not used by the FPS loop itself).")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-steps", type=int, default=0,
                        help="Stop after N steps. 0 = run until Ctrl+C.")
    parser.add_argument("--report-every", type=int, default=100,
                        help="Print a rolling FPS line every N steps.")
    parser.add_argument("--visualize-rgbd", action="store_true",
                        help="Show RGB+depth in a non-blocking window. Errors if no RGBD data.")
    args = parser.parse_args()

    world_config = blend_presets("world", [args.world])
    agent_config = blend_presets("agents", [args.agent])
    _task_config = blend_presets("task", [args.task])  # noqa: F841  (validated, unused)

    conn = RoslikeUnityConnector(verbose=False)
    conn.connect()

    conn.publish(StringMessage(data="Wildfire"), "/sim_control/scene_select")
    conn.send_messages_and_step(enable_physics_step=False)
    conn.read_messages_from_unity()

    conn.publish(StringMessage(data=to_entries_json(agent_config)), "/sim_control/agent_config")
    conn.send_messages_and_step(enable_physics_step=False)
    conn.read_messages_from_unity()

    print(f"World: {args.world}, Agent: {args.agent}, Task: {args.task}, "
          f"visualize_rgbd={args.visualize_rgbd}")

    result = run_fps_test(
        conn,
        world_config,
        agent_config,
        seed=args.seed,
        max_steps=args.max_steps,
        report_every=args.report_every,
        visualize_rgbd=args.visualize_rgbd,
    )
    print(f"\n=== FPS test done ===")
    print(f"steps:            {result['steps']}")
    print(f"wall seconds:     {result['wall_seconds']:.2f}")
    print(f"mean FPS:         {result['mean_fps']:.2f}")
    print(f"recv total:       {result['total_recv_bytes']/1e6:.2f} MB")
    print(f"recv mean/step:   {result['mean_recv_mb_per_step']:.3f} MB")
    print(f"recv mean/sec:    {result['mean_recv_mb_per_s']:.2f} MB/s")
    print(f"recv peak/step:   {result['peak_recv_bytes_per_step']/1e6:.3f} MB")
    if args.visualize_rgbd:
        print(f"rgbd topic:       {result['rgbd_topic']}")


if __name__ == "__main__":
    main()
