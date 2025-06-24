using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using System;
//using Unity.Robotics.ROSTCPConnector.
using RosMessageTypes.Std;
//using RosMessageTypes.Sensor;
/* using Unity.VisualScripting; */

public class Screamer : MonoBehaviour
{
  public String topicName;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        ROSConnection.GetOrCreateInstance().RegisterPublisher<EmptyMsg>(topicName);
    }

    // Update is called once per frame
    void Update()
    {
      Debug.Log("AAA");
     ROSConnection.GetOrCreateInstance().Publish(topicName, new EmptyMsg());

    }
}
