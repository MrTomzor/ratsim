using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using UnityEngine.XR;
using Newtonsoft.Json; // Add Newtonsoft.Json via Unity Package Manager or .dll

public class MessageHeader
{
    public uint stepIndex;
}

public class Message
{
    public MessageHeader header { get; set; }
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

public class TcpServer : MonoBehaviour
{
    private TcpListener listener;
    private Thread serverThread;
    private StreamWriter writer;

    // Change the subscribers dictionary to support different message types per topic
    private Dictionary<string, List<Action<Message>>> subscribersByTopic = new();

    Dictionary<string, Type> messageTypeRegistry = new Dictionary<string, Type>
    {
        { "Lidar2DMessage", typeof(Lidar2DMessage) },
        { "StringMessage", typeof(StringMessage) }
    };

    void HandleRawJson(string json)
    {
        // Deserialize outer wrapper
        var wrapper = JsonConvert.DeserializeObject<Dictionary<string, object>>(json);
        string typeName = wrapper["type"].ToString();
        string topic = wrapper["topic"].ToString();
        var dataJson = wrapper["data"].ToString();

        if (messageTypeRegistry.TryGetValue(typeName, out Type msgType))
        {
            var fullJson = $"{{\"topic\":\"{topic}\",\"type\":\"{typeName}\",\"{nameof(dataJson)}\":{dataJson}}}";
            var msg = (Message)JsonConvert.DeserializeObject(dataJson, msgType);
            DispatchMessage(topic, msg);
        }
        else
        {
            Debug.LogWarning($"Unknown message type: {typeName}");
        }
    }

    void DispatchMessage(string topic, Message msg)
    {
        Debug.Log("Dispatching message to topic: " + topic);
        Debug.Log("Message type: " + msg.GetType().Name);
        Debug.Log("Message data: " + JsonConvert.SerializeObject(msg));

        foreach(var subscriber in subscribersByTopic[topic])
        {
            if (subscriber is Action<Message> action)
            {
                action(msg);
            }
        }
    }

    void TestMessageReceived()
    {
        var msg = new StringMessage { data = "Hello, World!" };
        string json = JsonConvert.SerializeObject(new
        {
            topic = "test_topic",
            type = "StringMessage",
            data = msg
        });
        HandleRawJson(json);
    }

    void StringCallbackTest(StringMessage msg)
    {
        Debug.Log("Received StringMessage: " + msg.data);
    }

    public void Subscribe<T>(string topic, Action<T> callback) where T : Message
    {

        if(subscribersByTopic.TryGetValue(topic, out var subscribers) == false)
        {
            subscribers = new List<Action<Message>>();
            subscribersByTopic[topic] = subscribers;
        }
        subscribers.Add((Message msg) =>
        {
            if (msg is not T)
            {
                Debug.LogWarning($"Received message of type {msg.GetType().Name} but expected {typeof(T).Name}");
                return;
            }
            callback((T)msg);
        });
    }

    void Start()
    {
        //TestRegisterSubscriberAndReceiveMsg();
        //Subscribe<StringMessage>("test_topic", SubCallbackTest);
        //HandleMessage("test_topic", new StringMessage { data = "Hello, World!" });

        Subscribe<StringMessage>("test_topic", StringCallbackTest);

        //TestMessageReceived();


        serverThread = new Thread(StartServer);
        serverThread.IsBackground = true;
        serverThread.Start();
    }

    void OnApplicationQuit()
    {
        listener?.Stop();
        serverThread?.Abort();
    }

    void StartServer()
    {
        listener = new TcpListener(IPAddress.Any, 9000);
        listener.Start();
        Debug.Log("TCP server started on port 9000");

        var client = listener.AcceptTcpClient();
        Debug.Log("Client connected");

        var stream = client.GetStream();
        var reader = new StreamReader(stream, Encoding.UTF8);
        writer = new StreamWriter(stream, Encoding.UTF8) { AutoFlush = true };

        while (client.Connected)
        {
            try
            {
                var line = reader.ReadLine();
                if (line == null)
                {
                    Debug.Log("Client disconnected or no data received");
                    continue;
                }
                Debug.Log("Received line");
                HandleRawJson(line);

                /*var json = JsonConvert.DeserializeObject<Dictionary<string, object>>(line);
                var topic = json["topic"].ToString();
                var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(json["data"].ToString());

                if (topicHandlers.TryGetValue(topic, out var handler))
                {
                    handler(data);
                }
                else
                {
                    Debug.LogWarning($"Unhandled topic: {topic}");
                }*/
            }
            catch (Exception e)
            {
                Debug.LogError("Error in server loop: " + e.Message);
                break;
            }
        }

        client.Close();
        listener.Stop();
    }
}
