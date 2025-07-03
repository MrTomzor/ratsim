using System.Threading;
using UnityEngine;

public class PositionSensor : MonoBehaviour
{
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        RoslikeTCPServer conn = RoslikeTCPServer.GetInstance();
        conn.RegisterTimerDiscrete(PublishPosition, 1);
    }

    void PublishPosition(TimerEvent timerEvent = null)
    {
        var position = transform.position;
        var rotation = transform.rotation.eulerAngles;

        // Create a message with the position and rotation data
        StringMessage msg = new StringMessage
        {
            data = $"Position: {position}, Rotation: {rotation}"
        };

        // Publish the message to the "/position" topic

        RoslikeTCPServer.GetInstance().Publish("/position", msg);
    }
}
