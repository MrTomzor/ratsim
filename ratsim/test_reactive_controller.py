from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *
from nav.reactive_controller import *

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
        # conn.publish(TwistMessage(linear_x=1, linear_y=0, linear_z=0, angular_x=0, angular_y=0, angular_z=0), "/cmd_vel")
        print("Publishing twist message:", twistmsg.linear_x, twistmsg.linear_y, twistmsg.angular_z)
        conn.publish(twistmsg, "/cmd_vel")
        conn.send_messages_and_step()
        conn.read_messages_from_unity()
        conn.log_connection_stats()

