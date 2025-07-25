using UnityEngine;

public class Message
{

}

public class StepRequestMessage : Message
{
    public bool physicsEnabled { get; set; }
}

public class StepFinishedMessage : Message
{
    public bool success { get; set; }
}

public class StringMessage : Message
{
    public string data { get; set; }
}

public class Int32Message : Message
{
    public int data { get; set; }
}

public class Float32Message : Message
{
    public float data { get; set; }
}

public class BoolMessage : Message
{
    public bool data { get; set; }
}

public class Lidar2DMessage : Message
{
    public float[] ranges { get; set; }
    public float[] descriptors { get; set; }
    public int angleIncrementDeg { get; set; }
    public int angleStartDeg { get; set; }
    public float maxRange { get; set; }
}

public class VisualPointTrackerMessage : Message
{
    public float[] trackedPointsEgocentricFLU { get; set; }
    public float[] trackedPointDescriptors { get; set; }
    public float scaleFactor { get; set; }
}

public class Twist2DMessage : Message
{
    public float forward { get; set; }
    public float left { get; set; }
    public float radiansCounterClockwise { get; set; }
}

public class RGBDMessage : Message
{
    public string rgbImageBase64 { get; set; }
    public string depthImageBase64 { get; set; }
    public float minDepth { get; set; }
    public float maxDepth { get; set; }
}

public class CameraIntrinsicsMessage : Message
{
    public int imageWidth { get; set; }
    public int imageHeight { get; set; }
    
    public float fx { get; set; }  // focal length in pixels (x-axis)
    public float fy { get; set; }  // focal length in pixels (y-axis)
    public float cx { get; set; }  // principal point x
    public float cy { get; set; }  // principal point y

    public float nearClip { get; set; }
    public float farClip { get; set; }
    public float verticalFOV { get; set; }
}