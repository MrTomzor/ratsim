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

public class Lidar2DMessage : Message
{
    public float[] ranges { get; set; }
    public float[] descriptors { get; set; }
    public int angleIncrementDeg { get; set; }
    public int angleStartDeg { get; set; }
    public float maxRange { get; set; }
}

public class Twist2DMessage : Message
{
    public float forward { get; set; }
    public float left { get; set; }
    public float radiansCounterClockwise { get; set; }
}