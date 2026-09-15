from .message_definitions import Message


class MessageEnvelope:
    def __init__(self, topic: str = "", type: str = "", data: Message = None):
        self.topic = topic
        self.type = type
        self.data = data

