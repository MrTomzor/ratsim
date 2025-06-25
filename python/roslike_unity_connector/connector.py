import socket
import json
import time
# from . import message_definitions
from .message_definitions import *
from .message_envelope import *


class RoslikeUnityConnector:
    def __init__(self, host_ip = '127.0.0.1', port = 9000, verbose = True) -> None:
        self.host_ip = host_ip
        self.port = port
        self.verbose = verbose
        self.sock = None

        self.queued_messages = []
        self.queued_messages_topics = []

        self.received_messages = []
        self.receive_messages_topics = []
        pass

    def connect(self):
        print("Connecting to Unity...")
        self.sock =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host_ip, self.port))
        print("connected")

    def message_to_dict(self, message: Message, topic: str) -> dict:
        return {
            "topic": topic,
            "type": message.__class__.__name__,
            "data": message.__dict__,
        }
    
    def message_from_dict(self, envelope_dict: dict) -> MessageEnvelope:
        topic = envelope_dict["topic"]
        msg_type = envelope_dict["type"]
        data = envelope_dict["data"]
    
        if msg_type not in MESSAGE_TYPE_REGISTRY:
            raise ValueError(f"Unknown message type: {msg_type}")
    
        cls = MESSAGE_TYPE_REGISTRY[msg_type]
        msg_instance = cls(**data)
    
        return MessageEnvelope(topic=topic, type=msg_type, data=msg_instance)
    
    def pack_messages_to_json(self, messages: List[Message], topics: List[str]) -> str:
        payload = {
            "messages": [self.message_to_dict(msg, topic) for msg, topic in zip(messages, topics)]
        }
        return json.dumps(payload) + "\n"

    def queue_message_to_send(self, message: Message, topic: str):
        self.queued_messages.append(message)
        self.queued_messages_topics.append(topic)

    def send_queued_messages_and_step(self, enable_physics_step: bool = True):
        
        # Always send a step request message
        self.msg_sendtime = time.time()
        self.queue_message_to_send(StepRequestMessage(enable_physics_step), "/sim_control/do_step")
        
        # Pack and send the queued messages
        outbound_json = self.pack_messages_to_json(self.queued_messages, self.queued_messages_topics)
        self.sock.sendall(outbound_json.encode("utf-8"))

        if self.verbose:
            print(f"Sent {len(self.queued_messages)} messages to Unity.")

        # Clear the queued messages
        self.queued_messages.clear()
        self.queued_messages_topics.clear()

    def read_messages_from_unity(self):
        # Clear the received messages
        self.received_messages.clear()
        self.receive_messages_topics.clear()

        # Read JSON msgs
        buffer = b""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            buffer += chunk
            if b"\n" in buffer:
                break

        response = json.loads(buffer.decode("utf-8-sig").strip())

        # Convert each message in the response to a MessageEnvelope
        for msg in response["messages"]:
            envelope = self.message_from_dict(msg)
            if self.verbose:
                print(f"Received message: {envelope.topic} ({envelope.type})")
                if isinstance(envelope.data, Message):
                    print(f"Data: {envelope.data.__dict__}")
            

            # Store the received message and its topic
            self.received_messages.append(envelope.data)
            self.receive_messages_topics.append(envelope.topic)

        # Calculate FPS and bandwidth
        dt = time.time() - self.msg_sendtime
        
        strlen = len(buffer) # assuming one byte per character
        for msg in response["messages"]:
            strlen += len(msg)

        self.last_frame_fps = 1 / dt
        self.last_frame_bw = strlen / dt

    def get_received_messages(self, topic: str):
        # Return list of all messages received on the specified topic
        messages = []
        for i, t in enumerate(self.receive_messages_topics):
            if t == topic:
                messages.append(self.received_messages[i])
        return messages
    
    def log_connection_stats(self):
        print("FPS: " + str(self.last_frame_fps) + " BW: " + str(self.last_frame_bw / 1000.0) + " kB/s")

    def test_send_and_receive(self):

        while True:
            # Send no msgs (just a step request)
            print("Sending messages...")
            self.send_queued_messages_and_step()
    
            # Receive reply
            print("Receiving messages...")
            self.read_messages_from_unity()

            self.log_connection_stats()
            # time.sleep(0.0001)
