"""
Test connection between Python and Unity using ZeroMQ.

Usage:
    python -m ratsim.ZMQ_connector.test_zmq_connection
"""

import time
from .connector import ZmqUnityConnector


def test_zmq_connection(steps: int = 100):
    conn = ZmqUnityConnector(host_ip="127.0.0.1", port=9000, verbose=False)
    conn.connect()

    print(f"[test_zmq_connection] Running {steps} steps...")
    start_time = time.time()

    for i in range(steps):
        conn.send_messages_and_step(enable_physics_step=True)
        msgs = conn.read_messages_from_unity()

        step_finished = conn.get_received_messages("/sim_control/step_finished")
        if not step_finished:
            print(f"[Warning] Step {i}: No /sim_control/step_finished received!")

        if (i + 1) % 20 == 0 or i == steps - 1:
            print(f"Step {i + 1}/{steps} - Last FPS: {conn.last_frame_fps:.1f} - Bytes: {conn.last_frame_recv_bytes}")

    elapsed = time.time() - start_time
    fps = steps / elapsed if elapsed > 0 else 0
    print(f"\n[test_zmq_connection] Finished {steps} steps in {elapsed:.2f}s ({fps:.1f} FPS)")
    conn.close()


if __name__ == "__main__":
    test_zmq_connection()

