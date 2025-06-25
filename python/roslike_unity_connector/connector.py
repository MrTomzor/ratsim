import socket
import json
import time
# import roslike_unity_connector.message_definitions
from . import message_definitions


class RoslikeUnityConnector:
    def __init__(self, host_ip = '127.0.0.1', port = 9000) -> None:
        self.host_ip = host_ip
        self.port = port
        pass

    def test_send_and_receive(self):
        messages = [
            {
                "topic": "/sim_control/do_step",
                "type": "StepRequestMessage",
                "data": {
                    "physicsEnabled": True
                }
            },
            # {
            #     "topic": "misc/number",
            #     "type": "Int32Message",
            #     "data": {
            #         "data": 42
            #     }
            # }
        ]
    
        request = json.dumps({ "messages": messages }) + "\n"
    
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            print("Connecting to Unity...")
            sock.connect((self.host_ip, self.port))
    
            while True:
                sendtime = time.time()
                # print("Sending messages...")
                sock.sendall(request.encode("utf-8"))
    
                # Receive reply
                buffer = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    if b"\n" in buffer:
                        break
    
                response = json.loads(buffer.decode("utf-8-sig").strip())
    
                for msg in response["messages"]:
                    print(f"[{msg['topic']}] ({msg['type']}) -> {msg['data']}")
                dt = time.time() - sendtime
                fps = 1 / dt
                strlen = len(buffer)
                for msg in response["messages"]:
                    strlen += len(msg)
                print("MSG BYTES: " + str(strlen))
                bw = strlen / dt
                print("FPS: " + str(fps) + " BW: " + str(bw))
                # time.sleep(0.0001)

if __name__ == "__main__":
    conn = RoslikeUnityConnector()
    conn.test_send_and_receive()
