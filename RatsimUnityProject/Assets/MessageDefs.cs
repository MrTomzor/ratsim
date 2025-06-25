using UnityEngine;

public class Message
{
    //public MessageHeader header { get; set; }
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
    public int[] classes { get; set; }
    public float angleIncrement { get; set; }
    public float angleStart { get; set; }
}
