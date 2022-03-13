import os
import socket

from Client.ClientEventLoops import ClientEventLoop
from src.MessageHandlers import ClientMessageHandler

if __name__ == '__main__':
    os.system("title " + "Client Window (input commands)")  # set windows title as "Client Window (input commands)"

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket for server
    result_window_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create socket for result window

    server_address = ('127.0.0.1', 12345)  # INPUT SERVER ADDRESS
    result_window_address = ('127.0.0.1', 12346)  # INPUT RESULT WINDOW ADDRESS

    # create sender of messages to result window
    result_window_sender = ClientMessageHandler(result_window_socket, result_window_address)
    # create client
    client = ClientEventLoop(client_socket, server_address, result_window_sender, is_start_result_window=True)
    # try to connect to server as many times as needed
    client.connect(n_max=None)
    # start main event loop after connection with server
    client.run()
