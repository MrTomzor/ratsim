from typing import List


# Auto-generated from C#


class Message:
    pass


class MessageEnvelope(Message):
    def __init__(self, topic: str = None, type: str = None, data: Message = None):
        self.topic = topic
        self.type = type
        self.data = data


class Message(Message):
    pass


class StepRequestMessage(Message):
    def __init__(self, physicsEnabled: bool = None):
        self.physicsEnabled = physicsEnabled


class StepFinishedMessage(Message):
    def __init__(self, success: bool = None):
        self.success = success


class StringMessage(Message):
    def __init__(self, data: str = None):
        self.data = data


class Int32Message(Message):
    def __init__(self, data: int = None):
        self.data = data


class Lidar2DMessage(Message):
    def __init__(self, ranges: List[float] = None, classes: List[int] = None, angleIncrement: float = None, angleStart: float = None):
        self.ranges = ranges
        self.classes = classes
        self.angleIncrement = angleIncrement
        self.angleStart = angleStart
