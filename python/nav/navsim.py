from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *

class NavSim():
    def __init__(self):
        self.conn = RoslikeUnityConnector(verbose=False)
        self.conn.connect()
        self.step_time = 0.02
        self.num_physics_steps = 0

        self.conn.send_messages_and_step()
        self.conn.read_messages_from_unity()

    def enable_human_control(self):
        msg = BoolMessage(data = True)
        self.conn.publish(msg, "/enable_human_control")
        self.conn.send_messages_and_step(enable_physics_step=False)
        self.conn.read_messages_from_unity()

    def step(self, action_dict = {}):
        for topic in action_dict.keys():
            for msg in action_dict[topic]:
                self.conn.publish(msg, topic)

        self.conn.send_messages_and_step()
        self.conn.read_messages_from_unity()

        obsv_dict = self.conn.get_all_received_messages_and_topics_dict()

        # Apply noise
        obsv_dict = self.apply_noise_models(obsv_dict)

        self.num_physics_steps += 1
        return obsv_dict

    def apply_noise_models(self, msgs_dict):
        # TODO 
        return msgs_dict

    pass
