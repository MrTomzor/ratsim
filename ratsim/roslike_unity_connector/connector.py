import socket
import json
import time
# from . import message_definitions
from .message_definitions import *
from .message_envelope import *
import select
import selectors


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

        self.timeout_seconds = 5

        self.send_buffer = b""

        pass

    def connect(self):
        print("Waiting to connect to Unity...")
        self.sock =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.sock.setblocking(0)
        while True:
            try:
                # Attempt to create a socket and connect
                self.sock.connect((self.host_ip, self.port))
                break
            except socket.error as e:
                print(f"Could not connect: {e}. Retrying in 1 second...")
                time.sleep(1)
        

        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_WRITE | selectors.EVENT_READ)
        
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

    def publish(self, message: Message, topic: str):
        self.queued_messages.append(message)
        self.queued_messages_topics.append(topic)

    def queue_message(self, msg: str):
        msg_bytes = (msg + "\n").encode("utf-8")
        self.send_buffer += msg_bytes
    
    def flush_send(self):
        try:
            if self.send_buffer:
                # print("Flushing send buffer of size: " + str(len(self.send_buffer)))
                sent = self.sock.send(self.send_buffer)
                # print("Sent bytes: " + str(sent))
                self.send_buffer = self.send_buffer[sent:]
        except BlockingIOError:
            # Socket not ready, try again later
            pass


    def send_messages_and_step(self, enable_physics_step: bool = True):
        
        # Always send a step request message
        self.msg_sendtime = time.time()
        self.publish(StepRequestMessage(enable_physics_step), "/sim_control/do_step")
        
        # Pack and send the queued messages
        outbound_json = self.pack_messages_to_json(self.queued_messages, self.queued_messages_topics)
        # outbound_json += "\n"  # Ensure newline termination
        out_str = outbound_json.encode('utf-8')
        self.send_buffer += out_str
        msglen = len(out_str)
        bigmsg = msglen > 10000
        if bigmsg:
            print(f"Sending big msg - {msglen} bytes to Unity.")
        # print("Outbound JSON size: " + str(len(out_str)))
        # self.sock.sendall(out_str)

        while self.send_buffer:
            events = self.selector.select(timeout=1)
            for key, mask in events:
                if mask & selectors.EVENT_WRITE:
                    self.flush_send()
        if bigmsg:
            print("All data sent.")
        
        # Clear the queued messages
        self.queued_messages.clear()
        self.queued_messages_topics.clear()

    def read_messages_from_unity(self):
        # Clear the received messages
        self.received_messages.clear()
        self.receive_messages_topics.clear()

        # Read JSON msgs
        # buffer = b""
        # while True:
        #     chunk = self.sock.recv(4096)
        #     if not chunk:
        #         break
        #     buffer += chunk
        #     if b"\n" in buffer:
        #         break

        readstart = time.time()

        was_timeout = False
        buffer = b""
        while True:
            # Use selector.select() instead of select.select
            events = self.selector.select(timeout=self.timeout_seconds)
            if not events:
                # Timeout occurred
                was_timeout = True
                break
        
            for key, mask in events:
                if mask & selectors.EVENT_READ:
                    chunk = key.fileobj.recv(4096)
                    if not chunk:
                        # Remote closed the socket
                        was_timeout = True
                        break
                    buffer += chunk
                    if b"\n" in buffer:
                        break
            else:
                # Continue while loop if inner break not triggered
                continue
            # Inner break triggered
            break

        # while True:
        #     chunk = None
        #     ready = select.select([self.sock], [], [], self.timeout_seconds)
        #     if ready[0]:
        #         chunk = self.sock.recv(4096)
        #     else:
        #         was_timeout = True
        #         break
        #     buffer += chunk
        #     if b"\n" in buffer:
        #         break

        if was_timeout:
            print("Timeout waiting for data from Unity.")
            return 1

        readend = time.time()
        

        response = json.loads(buffer.decode("utf-8-sig").strip())

        jsonend = time.time()

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

        envelopeend = time.time()

        # Calculate FPS and bandwidth
        dt = time.time() - self.msg_sendtime
        
        strlen = len(buffer) # assuming one byte per character
        for msg in response["messages"]:
            strlen += len(msg)

        self.last_frame_fps = 1 / dt
        self.last_frame_bw = strlen / dt

        # if True:
        #     print(f"[Timing] Socket read:      {(readend - readstart):.4f} s")
        #     print(f"[Timing] JSON parse:       {(jsonend - readend):.4f} s")
        #     print(f"[Timing] Envelope parsing: {(envelopeend - jsonend):.4f} s")
        #     print(f"[Timing] Total read:       {(envelopeend - readstart):.4f} s")
        #     print("BUFFERLEN: " + str(strlen))

        return 0

    def get_received_messages(self, topic: str):
        # Return list of all messages received on the specified topic
        messages = []
        for i, t in enumerate(self.receive_messages_topics):
            if t == topic:
                messages.append(self.received_messages[i])
        return messages

    def get_all_received_messages_and_topics_dict(self):
        # Return list of all messages received on the specified topic
        res = {}
        for i, top in enumerate(self.receive_messages_topics):
            msg = self.received_messages[i]
            if not top in res.keys():
                res[top] = []
            res[top].append(msg)
        return res
    
    def log_connection_stats(self):
        print("FPS: " + str(self.last_frame_fps) + " BW: " + str(self.last_frame_bw / 1000.0) + " kB/s")

    def test_send_and_receive(self):

        while True:
            # Send no msgs (just a step request)
            print("Sending messages...")
            self.send_messages_and_step()
    
            # Receive reply
            print("Receiving messages...")
            self.read_messages_from_unity()

            self.log_connection_stats()
            # time.sleep(0.0001)
