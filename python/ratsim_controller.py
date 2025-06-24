import socket
import json
import time

HOST = '127.0.0.1'
PORT = 9000


class TcpRoslikeConnector:
    def __init__(self) -> None:
        pass

    def send_and_receive_messages(self):
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
            sock.connect((HOST, PORT))
    
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

conn = TcpRoslikeConnector()
conn.send_and_receive_messages()
