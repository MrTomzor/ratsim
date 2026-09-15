from typing import List


class Message:
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


class FloatArrayMessage(Message):
    def __init__(self, data: List[float] = None):
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


class PoseMessage(Message):
    def __init__(self, x: float = None, y: float = None, z: float = None, qx: float = None, qy: float = None, qz: float = None, qw: float = None):
        self.x = x
        self.y = y
        self.z = z
        self.qx = qx
        self.qy = qy
        self.qz = qz
        self.qw = qw


class TwistMessage(Message):
    def __init__(self, linear_x: float = None, linear_y: float = None, linear_z: float = None, angular_x: float = None, angular_y: float = None, angular_z: float = None):
        self.linear_x = linear_x
        self.linear_y = linear_y
        self.linear_z = linear_z
        self.angular_x = angular_x
        self.angular_y = angular_y
        self.angular_z = angular_z


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


class MapGenTemplate2D(Message):
    def __init__(self, width: int = None, height: int = None, meters_per_pixel: float = None, obstacles: List[int] = None, spawnMask: List[int] = None, poiMask: List[int] = None, forbiddenMask: List[int] = None, growableMask: List[int] = None):
        self.width = width
        self.height = height
        self.meters_per_pixel = meters_per_pixel
        self.obstacles = obstacles
        self.spawnMask = spawnMask
        self.poiMask = poiMask
        self.forbiddenMask = forbiddenMask
        self.growableMask = growableMask


class Lidar3DMessage(Message):
    def __init__(self, ranges: List[float] = None, descriptors: List[float] = None, numRaysHorizontal: int = None, numRaysVertical: int = None, horizontalFovStart: float = None, horizontalFovEnd: float = None, verticalFovStart: float = None, verticalFovEnd: float = None, maxRange: float = None):
        self.ranges = ranges
        self.descriptors = descriptors
        self.numRaysHorizontal = numRaysHorizontal
        self.numRaysVertical = numRaysVertical
        self.horizontalFovStart = horizontalFovStart
        self.horizontalFovEnd = horizontalFovEnd
        self.verticalFovStart = verticalFovStart
        self.verticalFovEnd = verticalFovEnd
        self.maxRange = maxRange


class RawImageMessage(Message):
    def __init__(
        self,
        width: int = 0,
        height: int = 0,
        format: str = "RGB24",
        channels: int = 3,
        minDepth: float = 0.0,
        maxDepth: float = 100.0,
        binaryIndex: int = -1,
        depthBinaryIndex: int = -1,
    ):
        self.width = width
        self.height = height
        self.format = format
        self.channels = channels
        self.minDepth = minDepth
        self.maxDepth = maxDepth
        self.binaryIndex = binaryIndex
        self.depthBinaryIndex = depthBinaryIndex
        self.image = None
        self.depth = None


class RawLidarMessage(Message):
    def __init__(
        self,
        numRays: int = 0,
        descriptorDimension: int = 0,
        horizontalFovStart: float = 0.0,
        horizontalFovEnd: float = 0.0,
        verticalFovStart: float = 0.0,
        verticalFovEnd: float = 0.0,
        maxRange: float = 100.0,
        rangesBinaryIndex: int = -1,
        descriptorsBinaryIndex: int = -1,
    ):
        self.numRays = numRays
        self.descriptorDimension = descriptorDimension
        self.horizontalFovStart = horizontalFovStart
        self.horizontalFovEnd = horizontalFovEnd
        self.verticalFovStart = verticalFovStart
        self.verticalFovEnd = verticalFovEnd
        self.maxRange = maxRange
        self.rangesBinaryIndex = rangesBinaryIndex
        self.descriptorsBinaryIndex = descriptorsBinaryIndex
        self.ranges = None
        self.descriptors = None


MESSAGE_TYPE_REGISTRY = {
    "Message": Message,
    "StepRequestMessage": StepRequestMessage,
    "StepFinishedMessage": StepFinishedMessage,
    "StringMessage": StringMessage,
    "Int32Message": Int32Message,
    "Float32Message": Float32Message,
    "BoolMessage": BoolMessage,
    "FloatArrayMessage": FloatArrayMessage,
    "Lidar2DMessage": Lidar2DMessage,
    "VisualPointTrackerMessage": VisualPointTrackerMessage,
    "PoseMessage": PoseMessage,
    "TwistMessage": TwistMessage,
    "RGBDMessage": RGBDMessage,
    "CameraIntrinsicsMessage": CameraIntrinsicsMessage,
    "MapGenTemplate2D": MapGenTemplate2D,
    "Lidar3DMessage": Lidar3DMessage,
    "RawImageMessage": RawImageMessage,
    "RawLidarMessage": RawLidarMessage,
}

