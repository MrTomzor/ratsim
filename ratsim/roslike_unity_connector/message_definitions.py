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


class Float32Message(Message):
    def __init__(self, data: float = None):
        self.data = data


class BoolMessage(Message):
    def __init__(self, data: bool = None):
        self.data = data


class Lidar2DMessage(Message):
    def __init__(self, ranges: List[float] = None, descriptors: List[float] = None, angleIncrementDeg: int = None, angleStartDeg: int = None, maxRange: float = None):
        self.ranges = ranges
        self.descriptors = descriptors
        self.angleIncrementDeg = angleIncrementDeg
        self.angleStartDeg = angleStartDeg
        self.maxRange = maxRange


class VisualPointTrackerMessage(Message):
    def __init__(self, trackedPointsEgocentricFLU: List[float] = None, trackedPointDescriptors: List[float] = None, scaleFactor: float = None):
        self.trackedPointsEgocentricFLU = trackedPointsEgocentricFLU
        self.trackedPointDescriptors = trackedPointDescriptors
        self.scaleFactor = scaleFactor


class Twist2DMessage(Message):
    def __init__(self, forward: float = None, left: float = None, radiansCounterClockwise: float = None):
        self.forward = forward
        self.left = left
        self.radiansCounterClockwise = radiansCounterClockwise


class RGBDMessage(Message):
    def __init__(self, rgbImageBase64: str = None, depthImageBase64: str = None, minDepth: float = None, maxDepth: float = None):
        self.rgbImageBase64 = rgbImageBase64
        self.depthImageBase64 = depthImageBase64
        self.minDepth = minDepth
        self.maxDepth = maxDepth


class CameraIntrinsicsMessage(Message):
    def __init__(self, imageWidth: int = None, imageHeight: int = None, fx: float = None, fy: float = None, cx: float = None, cy: float = None, nearClip: float = None, farClip: float = None, verticalFOV: float = None):
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy
        self.nearClip = nearClip
        self.farClip = farClip
        self.verticalFOV = verticalFOV




MESSAGE_TYPE_REGISTRY = {

    "Message": Message,

    "StepRequestMessage": StepRequestMessage,

    "StepFinishedMessage": StepFinishedMessage,

    "StringMessage": StringMessage,

    "Int32Message": Int32Message,

    "Float32Message": Float32Message,

    "BoolMessage": BoolMessage,

    "Lidar2DMessage": Lidar2DMessage,

    "VisualPointTrackerMessage": VisualPointTrackerMessage,

    "Twist2DMessage": Twist2DMessage,

    "RGBDMessage": RGBDMessage,

    "CameraIntrinsicsMessage": CameraIntrinsicsMessage,

}