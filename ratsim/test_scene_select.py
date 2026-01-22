from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
import sys

if __name__ == "__main__":
    # Read scene name from arguments
    scene_name = sys.argv[1] if len(sys.argv) > 1 else "BoxArena"

    # Create connector instance and connect
    conn = RoslikeUnityConnector()
    conn.connect()
    # conn.test_send_and_receive()

    # Send scene select message
    print(f"Selecting scene: {scene_name}")
    msg = StringMessage(data = scene_name)
    conn.publish(msg, "/sim_control/scene_select")
    conn.send_messages_and_step(enable_physics_step=False)
    conn.read_messages_from_unity()

