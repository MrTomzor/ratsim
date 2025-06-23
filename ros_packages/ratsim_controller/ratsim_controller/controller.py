#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty, Int8
from sensor_msgs.msg import CompressedImage
import time
from std_srvs.srv import Trigger

class RatsimController(Node):
    def __init__(self):
        super().__init__('ratsim_controller')

        # self.screampub = self.create_subscription(Empty, '/aaa', self.scream_cb, 10)
        self.pub = self.create_publisher(Int8, '/step', 10)
        self.stepsub = self.create_subscription(Int8, '/step_finished', self.step_end_callback, 10)
        self.compsub = self.create_subscription(CompressedImage, '/rgb/image/compressed', self.image_callback, 10)
        self.stepsub
        self.compsub

        self.srv_client = self.create_client(Trigger, '/step_srv')
        while not self.srv_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = Trigger.Request()


        # self.step_msg = Empty()
        self.step_msg = Int8()
        self.step_count = 0
        self.all_data_received = True
        self.gametime = 0

        timer_period = 0.01  # 100 Hz
        # self.timer = self.create_timer(timer_period, self.run)
        self.send_time = time.time()

    # def scream_cb(self, msg):
    #     print("PES")
    #     self.get_logger().info("PESS!")

    def get_game_time(self):
        return self.gametime

    def step_end_callback(self, msg):
        # self.get_logger().info("STEP ENDED! " + str(int(msg.data)) + " TIME: " + str(time.time() - self.send_time))
        self.get_logger().info("STEP ENDED! " + str(int(msg.data)) + " FPS: " + str(1 / (time.time() - self.send_time)))
        self.all_data_received = True

    def image_callback(self, msg):
        timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.get_logger().info(f"Received an image at step {self.step_count}")
        self.get_logger().info(f"image stamp: {timestamp}")

    def send_request(self ):
        # self.req.a = a
        # self.req.b = b
        self.future = self.srv_client.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()

    def run(self):
        self.get_logger().info("stepin")

        self.send_time = time.time()
        self.send_request();
        
        # self.future = self.srv_client.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        self.get_logger().info("STEP ENDED! FPS: " + str(1 / (time.time() - self.send_time)))

        self.get_logger().info("stepdone")


        # if self.all_data_received:
        #     if self.step_count > -1:
        #         self.all_data_received = False
        #     self.pub.publish(self.step_msg)
        #     self.send_time = time.time()
        #     self.step_count += 1
        #     self.get_logger().info(f"beep - Published step #{self.step_count}")

def main(args=None):
    rclpy.init(args=args)
    node = RatsimController()

    # rclpy.spin(node)
    while True:
        node.run()

    # try:
    #     rclpy.spin(node)
    # except KeyboardInterrupt:
    #     pass
    # finally:
    #     node.destroy_node()
    #     rclpy.shutdown()

if __name__ == '__main__':
    main()
