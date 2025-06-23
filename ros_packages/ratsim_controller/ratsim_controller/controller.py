#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty
from sensor_msgs.msg import CompressedImage

class RatsimController(Node):
    def __init__(self):
        super().__init__('step_publisher_node')

        self.pub = self.create_publisher(Empty, '/step', 10)
        self.create_subscription(Empty, '/step_finished', self.step_end_callback, 10)
        self.create_subscription(CompressedImage, '/rgb/image/compressed', self.image_callback, 10)

        self.step_msg = Empty()
        self.step_count = 0
        self.all_data_received = True
        self.gametime = 0

        timer_period = 0.01  # 100 Hz
        self.timer = self.create_timer(timer_period, self.run)

    def get_game_time(self):
        return self.gametime

    def step_end_callback(self, msg):
        self.get_logger().info("STEP ENDED!")
        self.all_data_received = True

    def image_callback(self, msg):
        timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.get_logger().info(f"Received an image at step {self.step_count}")
        self.get_logger().info(f"image stamp: {timestamp}")

    def run(self):
        if self.all_data_received:
            if self.step_count > 10:
                self.all_data_received = False
            self.pub.publish(self.step_msg)
            self.step_count += 1
            self.get_logger().info(f"Published step #{self.step_count}")

def main(args=None):
    rclpy.init(args=args)
    node = RatsimController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
