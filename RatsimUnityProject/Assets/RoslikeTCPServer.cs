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


public class RoslikeTCPServer : MonoBehaviour
{
    static RoslikeTCPServer instance;
    public static RoslikeTCPServer GetInstance()
    {
        return instance;
    }

    private TcpListener listener;
    private Thread serverThread;
    private StreamWriter writer;

    // Change the subscribers dictionary to support different message types per topic
    private Dictionary<string, List<Action<Message>>> subscribersByTopic = new();
    private List<Tuple<string, Message>> receivedMessages = new List<Tuple<string, Message>>();

    List<Tuple<string, Message>> DeserializeMessages(Newtonsoft.Json.Linq.JArray rawMsgs)
    {
        var messages = new List<Tuple<string, Message>>();
        foreach (var rawMsg in rawMsgs)
        {
            // Deserialize outer wrapper
            var wrapper = JsonConvert.DeserializeObject<Dictionary<string, object>>(rawMsg.ToString());
            string typeName = wrapper["type"].ToString();
            string topic = wrapper["topic"].ToString();
            var dataJson = wrapper["data"].ToString();

            //if (messageTypeRegistry.TryGetValue(typeName, out Type msgType))
            Type msgType = MessageRegistry.GetMessageType(typeName);
            if (msgType != null)
            {
                var fullJson = $"{{\"topic\":\"{topic}\",\"type\":\"{typeName}\",\"{nameof(dataJson)}\":{dataJson}}}";
                var msg = (Message)JsonConvert.DeserializeObject(dataJson, msgType);

                messages.Add(new Tuple<string, Message>(topic, msg));
            }
            else
            {
                Debug.LogWarning($"Unknown message type: {typeName}");
            }
        }
        return messages;
    }

    void DispatchReceivedMessage(string topic, Message msg)
    {
        //Debug.Log("Dispatching message to topic: " + topic);
        //Debug.Log("Message type: " + msg.GetType().Name);
        //Debug.Log("Message data: " + JsonConvert.SerializeObject(msg));

        foreach (var subscriber in subscribersByTopic[topic])
        {
            if (subscriber is Action<Message> action)
            {
                action(msg);
            }
        }
    }

    public void Subscribe<T>(string topic, Action<T> callback) where T : Message
    {

        if (subscribersByTopic.TryGetValue(topic, out var subscribers) == false)
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

    void StepRequestCallback(StepRequestMessage msg)
    {
        if (msg.physicsEnabled != physicsEnabled)
        {
            Debug.LogWarning($"Received StepMessage with physicsEnabled={msg.physicsEnabled}, switching!");
        }
        physicsEnabled = msg.physicsEnabled;
    }

    void Start()
    {
        if (instance != null)
        {
            Debug.LogWarning("Multiple instances of TcpServer detected, destroying this one.");
            Destroy(this);
            return;
        }
        instance = this;
        
        

        Physics.simulationMode = SimulationMode.Script;
        Application.targetFrameRate = 10000;
        serverThread = new Thread(MainLoop);
        serverThread.IsBackground = true;
        serverThread.Start();

    }


    public volatile bool stepRequested = false;
    public bool physicsEnabled = true;
    public uint stepIndex { get; private set; } = 0;
    public uint physicsStepIndex { get; private set; } = 0;


    public GameObject trackObject;
    int trackpos = 0;

    void Update()
    {
        if (stepRequested)
        {
            // Handle Subscriber calbacks
            foreach (var msg in receivedMessages)
            {
                DispatchReceivedMessage(msg.Item1, msg.Item2);
            }

            // Step Unity physics
            if (physicsEnabled)
            {
                physicsStepIndex++;
                Physics.Simulate(0.02f);
            }
            trackpos = (int)trackObject.transform.position.y;
            stepRequested = false;
            Debug.Log("Physics step requested and executed");

            // Handle Publishers
        }
    }

    void MainLoop()
    {
        listener = new TcpListener(IPAddress.Any, 9000);
        listener.Start();
        Debug.Log("TCP server started on port 9000");

        var client = listener.AcceptTcpClient();
        Debug.Log("Client connected");

        var stream = client.GetStream();
        var reader = new StreamReader(stream, Encoding.UTF8);
        writer = new StreamWriter(stream, Encoding.UTF8) { AutoFlush = true };

        // Setup core subscribers
        Subscribe<StepRequestMessage>("/sim_control/do_step", StepRequestCallback);

        while (client.Connected)
        {
            try
            {
                // Read incoming messages
                var line = reader.ReadLine();
                if (line == null) continue;

                var wrapper = JsonConvert.DeserializeObject<Dictionary<string, object>>(line);
                var rawMsgs = wrapper["messages"] as Newtonsoft.Json.Linq.JArray;

                // Deserialize messages
                receivedMessages = DeserializeMessages(rawMsgs);

                // Call Unity Update to handle Subs and Pubs in main thread
                stepIndex++;
                stepRequested = true;
                while (stepRequested)
                {
                    // Wait for the step to be processed by Update func calls
                }

                // Reply with at least one message
                var replyMessages = new List<object>
                {
                    new MessageEnvelope (
                        topic: "/sim_control/step_finished",
                        type: "StepFinishedMessage",
                        data: new StepFinishedMessage {
                            success = true
                        }
                    )
                };

                // TODO - add all output messages from publishers (and thus call sensor readings)

                string replyJson = JsonConvert.SerializeObject(new { messages = replyMessages }) + "\n";
                writer.Write(replyJson);
                //Debug.Log("Sent reply");
            }
            catch (Exception e)
            {
                Debug.LogError("Server loop error: " + e.Message);
                break;
            }
        }

        client.Close();
        listener.Stop();
    }
    
    void OnApplicationQuit()
    {
        listener?.Stop();
        serverThread?.Abort();
    }

}
