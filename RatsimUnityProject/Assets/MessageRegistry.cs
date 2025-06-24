using UnityEngine;
using System.Collections.Generic;

public class MessageRegistry
{
    public static MessageRegistry Instance { get; } = new MessageRegistry();

    private MessageRegistry() { }

    public void RegisterMessageType(string typeName, System.Type type)
    {
        if (!messageTypeRegistry.ContainsKey(typeName))
        {
            messageTypeRegistry[typeName] = type;
        }
    }

    public static System.Type GetMessageType(string typeName)
    {
        return Instance.messageTypeRegistry.TryGetValue(typeName, out var type) ? type : null;
    }

    private Dictionary<string, System.Type> messageTypeRegistry = new Dictionary<string, System.Type>
    {
        { "Lidar2DMessage", typeof(Lidar2DMessage) },
        { "StringMessage", typeof(StringMessage) },
        { "Int32Message", typeof(Int32Message) },
        { "StepRequestMessage", typeof(StepRequestMessage) },
        { "StepFinishedMessage", typeof(StepFinishedMessage) }
    };
}
