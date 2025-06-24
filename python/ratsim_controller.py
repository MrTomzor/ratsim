import socket
import json

# Define the message structure
message = {
    "topic": "test_topic",
    "type": "StringMessage",
    "data": {
        "header": {
            "stepIndex": 1
        },
        "data": "Hello from Python!"
    }
}

message2 = {
    "topic": "test_topic",
    "type": "StringMessage",
    "data": {
        "header": {
            "stepIndex": 1
        },
        "data": "PES!"
    }
}

# Serialize to JSON and append newline (required for Unity's line-based reader)
json_str = json.dumps(message) + "\n"
json_str2 = json.dumps(message2) + "\n"

# Connect to Unity server
HOST = '127.0.0.1'  # Use your Unity host IP here if running externally
PORT = 9000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print("Connecting to Unity...")
    s.connect((HOST, PORT))
    print("Connected. Sending message...")
    s.sendall(json_str.encode('utf-8'))
    s.sendall(json_str2.encode('utf-8'))
    print("Message sent. Closing connection.")

