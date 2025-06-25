from roslike_unity_connector.connector import *
from roslike_unity_connector.message_definitions import *

if __name__ == "__main__":
    conn = RoslikeUnityConnector()
    conn.test_send_and_receive()
