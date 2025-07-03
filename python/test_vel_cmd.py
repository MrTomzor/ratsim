from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *

if __name__ == "__main__":
    conn = RoslikeUnityConnector()
    conn.connect()

    while True:
        conn.publish(Twist2DMessage(1, 0, 0), "/cmd_vel")
        conn.send_messages_and_step()
        conn.read_messages_from_unity()
        conn.log_connection_stats()

