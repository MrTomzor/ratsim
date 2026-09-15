import json
import socket
import time
from typing import Dict, List

import numpy as np
import zmq

from .message_definitions import (
    MESSAGE_TYPE_REGISTRY,
    Message,
    RawImageMessage,
    RawLidarMessage,
    StepRequestMessage,
)
from .message_envelope import MessageEnvelope

class ZmqUnityConnector:
    """ZeroMQ-based client connector for communicating with Unity ZmqUnityServer."""

    def __init__(
        self,
        host_ip: str = "0.0.0.0",
        port: int = 9000,
        verbose: bool = False,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.host_ip = host_ip
        self.port = port
        self.verbose = verbose
        self.timeout_seconds = timeout_seconds

        self.context: zmq.Context = None
        self.socket: zmq.Socket = None

        self.queued_messages: List[Message] = []
        self.queued_messages_topics: List[str] = []

        self.received_messages: List[Message] = []
        self.receive_messages_topics: List[str] = []

        self.last_frame_recv_bytes: int = 0
        self.last_frame_fps: float = 0.0
        self.last_frame_bw: float = 0.0
        self.msg_sendtime: float = 0.0

    def connect(self) -> None:
        """Initialize connection to Unity. Blocks and retries until Unity is listening."""
        if self.context is None:
            self.context = zmq.Context()

        connected = False
        while not connected:
            print("Waiting to connect to Unity...")

            # Step 1: Probe TCP reachability
            try:
                probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                probe.settimeout(1.0)
                probe.connect((self.host_ip, self.port))
                probe.close()
            except (socket.error, socket.timeout) as e:
                print(f"Could not connect: {e}. Retrying in 1 second...")
                time.sleep(1)
                continue

            # Step 2: Establish ZeroMQ connection
            if self.socket is not None:
                self.socket.close(linger=0)

            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.RCVTIMEO, 1500)
            self.socket.setsockopt(zmq.SNDTIMEO, 1500)
            if hasattr(zmq, "REQ_RELAXED"):
                self.socket.setsockopt(zmq.REQ_RELAXED, 1)
            if hasattr(zmq, "REQ_CORRELATE"):
                self.socket.setsockopt(zmq.REQ_CORRELATE, 1)

            endpoint = f"tcp://{self.host_ip}:{self.port}"
            self.socket.connect(endpoint)

            # Step 3: Verify ZeroMQ handshake
            try:
                ping_payload = json.dumps({
                    "messages": [{
                        "topic": "/sim_control/ping",
                        "type": "StringMessage",
                        "data": {"data": "ping"}
                    }]
                }) + "\n"
                self.socket.send_string(ping_payload)
                reply = self.socket.recv_string()
                if reply:
                    connected = True
                    break
            except zmq.ZMQError as e:
                print(f"ZeroMQ handshake failed: {e}. Retrying in 1 second...")
                time.sleep(1)

        # Restore normal operational timeouts
        self.socket.setsockopt(zmq.RCVTIMEO, int(self.timeout_seconds * 1000))
        self.socket.setsockopt(zmq.SNDTIMEO, int(self.timeout_seconds * 1000))
        print("connected")

    def close(self) -> None:
        """Close socket and terminate ZeroMQ context."""
        if self.socket is not None:
            self.socket.close(linger=0)
            self.socket = None
        if self.context is not None:
            self.context.term()
            self.context = None
        print("[ZmqUnityConnector] Closed.")

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
            raise ValueError(f"[ZmqUnityConnector] Unknown message type: {msg_type}")

        cls = MESSAGE_TYPE_REGISTRY[msg_type]
        msg_instance = cls(**data)
        return MessageEnvelope(topic=topic, type=msg_type, data=msg_instance)

    def pack_messages_to_json(self, messages: List[Message], topics: List[str]) -> str:
        payload = {
            "messages": [self.message_to_dict(msg, topic) for msg, topic in zip(messages, topics)]
        }
        return json.dumps(payload) + "\n"

    def publish(self, message: Message, topic: str) -> None:
        """Queue a message to be sent on the next step."""
        self.queued_messages.append(message)
        self.queued_messages_topics.append(topic)

    def send_messages_and_step(self, enable_physics_step: bool = True) -> None:
        """Publish step request and all queued messages to Unity via ZeroMQ REQ socket."""
        self.msg_sendtime = time.time()
        self.publish(StepRequestMessage(enable_physics_step), "/sim_control/do_step")

        outbound_json = self.pack_messages_to_json(self.queued_messages, self.queued_messages_topics)

        # Clear outgoing queue
        self.queued_messages.clear()
        self.queued_messages_topics.clear()

        # Send over ZeroMQ REQ socket
        try:
            self.socket.send_string(outbound_json)
        except zmq.Again:
            print("[ZmqUnityConnector] Timeout sending data to Unity. Closing connection.")
            self.close()
            raise TimeoutError("[ZmqUnityConnector] Timeout sending data to Unity.")

    def read_messages_from_unity(self) -> Dict[str, List[Message]]:
        """Receive response messages from Unity and parse into typed messages."""
        self.received_messages.clear()
        self.receive_messages_topics.clear()
        self.last_frame_recv_bytes = 0

        try:
            frames = self.socket.recv_multipart(copy=False)
        except zmq.Again:
            print("[ZmqUnityConnector] Timeout waiting for data from Unity. Closing connection.")
            self.close()
            raise TimeoutError("[ZmqUnityConnector] Timeout waiting for data from Unity.")

        if not frames:
            return {}

        self.last_frame_recv_bytes = sum(len(f) for f in frames)
        raw_str = bytes(frames[0]).decode("utf-8-sig").strip()

        if not raw_str:
            return {}

        try:
            response = json.loads(raw_str)
        except json.JSONDecodeError as e:
            print("\n=== BAD JSON FROM UNITY ===")
            print(repr(raw_str[:1000]))
            print("===========================\n")
            raise e

        for msg in response.get("messages", []):
            envelope = self.message_from_dict(msg)
            data_obj = envelope.data

            # Link binary multipart buffers to data object
            if isinstance(data_obj, RawImageMessage):
                if 0 < data_obj.binaryIndex < len(frames):
                    raw_rgb = frames[data_obj.binaryIndex]
                    if data_obj.channels == 3:
                        data_obj.image = np.frombuffer(raw_rgb, dtype=np.uint8).reshape((data_obj.height, data_obj.width, 3))
                    elif data_obj.channels == 4:
                        data_obj.image = np.frombuffer(raw_rgb, dtype=np.uint8).reshape((data_obj.height, data_obj.width, 4))
                    elif data_obj.channels == 1:
                        data_obj.image = np.frombuffer(raw_rgb, dtype=np.uint8).reshape((data_obj.height, data_obj.width))
                    else:
                        data_obj.image = np.frombuffer(raw_rgb, dtype=np.uint8)

                if 0 < data_obj.depthBinaryIndex < len(frames):
                    raw_depth = frames[data_obj.depthBinaryIndex]
                    data_obj.depth = np.frombuffer(raw_depth, dtype=np.float32).reshape((data_obj.height, data_obj.width))

            elif isinstance(data_obj, RawLidarMessage):
                if 0 < data_obj.rangesBinaryIndex < len(frames):
                    raw_ranges = frames[data_obj.rangesBinaryIndex]
                    data_obj.ranges = np.frombuffer(raw_ranges, dtype=np.float32)

                if 0 < data_obj.descriptorsBinaryIndex < len(frames):
                    raw_desc = frames[data_obj.descriptorsBinaryIndex]
                    if data_obj.descriptorDimension > 0:
                        data_obj.descriptors = np.frombuffer(raw_desc, dtype=np.float32).reshape((data_obj.numRays, data_obj.descriptorDimension))
                    else:
                        data_obj.descriptors = np.frombuffer(raw_desc, dtype=np.float32)

            if self.verbose:
                print(f"[ZmqUnityConnector] Received: {envelope.topic} ({envelope.type})")
            self.received_messages.append(data_obj)
            self.receive_messages_topics.append(envelope.topic)

        dt = time.time() - self.msg_sendtime if self.msg_sendtime > 0 else 1e-6
        self.last_frame_fps = 1.0 / dt if dt > 0 else 0.0
        self.last_frame_bw = self.last_frame_recv_bytes / dt if dt > 0 else 0.0

        return self.get_all_received_messages_and_topics_dict()

    def get_received_messages(self, topic: str) -> List[Message]:
        """Return all messages received on the specified topic during the last step."""
        messages = []
        for i, t in enumerate(self.receive_messages_topics):
            if t == topic:
                messages.append(self.received_messages[i])
        return messages

    def get_all_received_messages_and_topics_dict(self) -> Dict[str, List[Message]]:
        """Return dict mapping each topic to a list of received messages."""
        res: Dict[str, List[Message]] = {}
        for i, top in enumerate(self.receive_messages_topics):
            msg = self.received_messages[i]
            if top not in res:
                res[top] = []
            res[top].append(msg)
        return res

    def log_connection_stats(self) -> None:
        print(f"FPS: {self.last_frame_fps:.1f} | BW: {(self.last_frame_bw / 1000.0):.1f} kB/s")

