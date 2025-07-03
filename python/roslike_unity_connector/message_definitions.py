from typing import List


# Auto-generated from C#


class Message:
    pass


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
    def __init__(self, ranges: List[float] = None, descriptors: List[float] = None, angleIncrementDeg: int = None, angleStartDeg: int = None, maxRange: float = None):
        self.ranges = ranges
        self.descriptors = descriptors
        self.angleIncrementDeg = angleIncrementDeg
        self.angleStartDeg = angleStartDeg
        self.maxRange = maxRange


class Twist2DMessage(Message):
    def __init__(self, forward: float = None, left: float = None, radiansCounterClockwise: float = None):
        self.forward = forward
        self.left = left
        self.radiansCounterClockwise = radiansCounterClockwise




MESSAGE_TYPE_REGISTRY = {

    "Message": Message,

    "StepRequestMessage": StepRequestMessage,

    "StepFinishedMessage": StepFinishedMessage,

    "StringMessage": StringMessage,

    "Int32Message": Int32Message,

    "Lidar2DMessage": Lidar2DMessage,

    "Twist2DMessage": Twist2DMessage,

}