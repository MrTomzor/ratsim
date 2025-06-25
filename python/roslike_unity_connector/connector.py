import socket
import json
import time
# from . import message_definitions
from .message_definitions import *
from .message_envelope import *


class RoslikeUnityConnector:
    def __init__(self, host_ip = '127.0.0.1', port = 9000) -> None:
        self.host_ip = host_ip
        self.port = port
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


    def test_send_and_receive(self):
        # messages = [
        #     {
        #         "topic": "/sim_control/do_step",
        #         "type": "StepRequestMessage",
        #         "data": {
        #             "physicsEnabled": True
        #         }
        #     },
        # ]
        # request = json.dumps({ "messages": messages }) + "\n"

        messages_to_send = [StepRequestMessage(True)]
        outbound_json = self.pack_messages_to_json(messages_to_send, ["/sim_control/do_step"]) 
    
    
        while True:
            sendtime = time.time()
            # print("Sending messages...")
            self.sock.sendall(outbound_json.encode("utf-8"))
    
            # Receive reply
            buffer = b""
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                if b"\n" in buffer:
                    break
    
            response = json.loads(buffer.decode("utf-8-sig").strip())
    
            for msg in response["messages"]:
                # print(f"[{msg['topic']}] ({msg['type']}) -> {msg['data']}")
                envelope = self.message_from_dict(msg)
                print(f"[{envelope.topic}] ({envelope.type}) -> {envelope.data.__dict__}")

            dt = time.time() - sendtime
            fps = 1 / dt
            strlen = len(buffer)
            for msg in response["messages"]:
                strlen += len(msg)
            print("MSG BYTES: " + str(strlen))
            bw = strlen / dt
            print("FPS: " + str(fps) + " BW: " + str(bw))
            # time.sleep(0.0001)
