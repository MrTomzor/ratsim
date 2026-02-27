from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *

if __name__ == "__main__":
    conn = RoslikeUnityConnector()
    conn.connect()

    while True:
        conn.publish(TwistMessage(linear_x=1, linear_y=0, linear_z=0, angular_x=0, angular_y=0, angular_z=0), "/cmd_vel")
        conn.send_messages_and_step()
        conn.read_messages_from_unity()
        conn.log_connection_stats()

