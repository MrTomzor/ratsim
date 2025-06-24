using UnityEngine;

using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using System;
//using Unity.Robotics.ROSTCPConnector.
using RosMessageTypes.Std;

public class StringScreamer : MonoBehaviour
{
  public String topicName = "talk";
  public String content = "pes";
  public int intContent = 42;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        /* ROSConnection.GetOrCreateInstance().RegisterPublisher<StringMsg>(topicName); */
        ROSConnection.GetOrCreateInstance().RegisterPublisher<Int32Msg>(topicName);
    }

    // Update is called once per frame
    void Update()
    {
      Debug.Log("AAA");
     /* ROSConnection.GetOrCreateInstance().Publish(topicName, new StringMsg(content)); */
     ROSConnection.GetOrCreateInstance().Publish(topicName, new Int32Msg(intContent));

    }
}
