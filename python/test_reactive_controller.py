from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from classic_nav.reactive_controller import *

if __name__ == "__main__":
    conn = RoslikeUnityConnector()
    conn.connect()
    
    # First step
    conn.send_messages_and_step()
    conn.read_messages_from_unity()

    reactive_controller = ReactiveController(2, 4, 1, 0.5, dist_threshold1=3, dist_threshold2=5, ignore_colored=True) 

    while True:
        lidarmsg = conn.get_received_messages("/lidar2d")[0]
        twistmsg = reactive_controller.compute_forward_vel_and_angular_vel_for_lidar_msg(lidarmsg)
        # conn.publish(Twist2DMessage(1, 0, 0), "/cmd_vel")
        print("Publishing twist message:", twistmsg.forward, twistmsg.left, twistmsg.radiansCounterClockwise)
        conn.publish(twistmsg, "/cmd_vel")
        conn.send_messages_and_step()
        conn.read_messages_from_unity()
        conn.log_connection_stats()

