import socket
from src.MessageHandlers import ClientMessageHandler
from Client.ClientEventLoops import ClientEventLoop
import os



if __name__ == '__main__':
    os.system("title " + "Client Window (input commands)")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result_window_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = ('127.0.0.1', 12345)
    result_window_address = ('127.0.0.1', 12346)

    result_window_sender = ClientMessageHandler(result_window_socket, result_window_address)

    client = ClientEventLoop(client_socket, server_address, result_window_sender, is_start_result_window=True)

    client.connect()
    client.run()
