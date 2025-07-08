from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *

class NavSim():
    def __init__(self, dont_connect = False):
        self.step_time = 0.1
        self.num_physics_steps = 0
        self.noise_models = {}

        if not dont_connect:
            self.conn = RoslikeUnityConnector(verbose=False)
            self.conn.connect()
            self.conn.send_messages_and_step()
            self.conn.read_messages_from_unity()

    def enable_human_control(self):
        msg = BoolMessage(data = True)
        self.conn.publish(msg, "/enable_human_control")
        self.conn.send_messages_and_step(enable_physics_step=False)
        self.conn.read_messages_from_unity()

    def step(self, action_dict = {}):
        sim_ended = False

        for topic in action_dict.keys():
            for msg in action_dict[topic]:
                self.conn.publish(msg, topic)

        self.conn.send_messages_and_step()
        was_timeout = self.conn.read_messages_from_unity()

        obsv_dict = self.conn.get_all_received_messages_and_topics_dict()

        # Apply noise
        obsv_dict = self.apply_noise_models(obsv_dict)

        self.num_physics_steps += 1

        return obsv_dict, was_timeout

    def add_noise_model(self, topic, model):
        self.noise_models[topic] = model

    def apply_noise_models(self, msgs_dict):
        for topic in msgs_dict.keys():
            if topic in self.noise_models.keys():
                for i in range(len(msgs_dict[topic])):
                    msgs_dict[topic][i] = self.noise_models[topic].apply_noise(msgs_dict[topic][i])

        return msgs_dict

    pass
