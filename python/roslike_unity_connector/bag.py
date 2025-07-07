import pickle

class MessageBag():
    def __init__(self, filename = None) -> None:
        self.steps = []

        if filename:
            with open(filename, 'rb') as handle:
                self.steps = pickle.load(handle)

    def get_all_msgs(self, step_id):
        pass

    def add_step_msgs(self, topics_and_msgs_dict):
        self.steps.append(topics_and_msgs_dict)

    def save_to_file(self, filepath):
        with open(filepath, 'wb') as handle:
            pickle.dump(self.steps, handle, protocol=pickle.HIGHEST_PROTOCOL)

