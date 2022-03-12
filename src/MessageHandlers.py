from __future__ import annotations
import socket, select, time
from typing import List, Dict, Tuple, Any, TYPE_CHECKING, Union


if TYPE_CHECKING:
    from Server.ServerEventLoops import MainServer
    from Server.TCPServer import TCPServer


class ClientMessageHandler:
    def __init__(self,
                 client_socket: socket.socket,
                 address: Tuple[str, int]):

        self.client_socket: socket.socket = client_socket
        self.address: Tuple[str, int] = address
        self.msg_len: int = 2048
        self.send_timeout: float = 1.0
        self.read_timeout: float = 1.0
        self.loop_timeout: float = 0.1

    def connect(self):
        is_connected = False
        n = 0
        while not is_connected and n < 10:
            try:
                self.client_socket.connect(self.address)
                is_connected = True
            except ConnectionResetError:
                time.sleep(0.5)  # wait for result window start
            n+=1
        if not is_connected:
            raise ConnectionResetError('')


    def read_msg(self) -> bytes:
        data = bytes(0)

        # while True:
        ready_to_read, ready_to_write, in_error = select.select(
            [self.client_socket], [], [], self.read_timeout)

        if not ready_to_read:
            raise TimeoutError('Timeout to get data')
        package: bytes = ready_to_read[0].recv(self.msg_len)

        if not package:  # if 0 bytes received
            raise ConnectionError('Connection lost. 0 bytes received')
        data += package
        try:
            if data[-8:].decode('utf-8') == 'endofmsg':
                data = data[0:-8]
                # break
        except UnicodeError:
            pass
        return data


    def send_msg(self, encoded_data: bytes) -> None:
        msg_len = len(encoded_data)
        total_sent = 0

        while total_sent < msg_len:
            ready_to_read, ready_to_write, in_error = select.select(
                [], [self.client_socket], [], self.send_timeout)
            if not ready_to_write:
                raise TimeoutError('Timeout to send message')
            sent = ready_to_write[0].send(encoded_data[total_sent:])
            if sent == 0:
                raise ConnectionError("Connection lost. 0 bytes sent")
            total_sent = total_sent + sent


class ServerMessageHandler(ClientMessageHandler):
    def __init__(self,
                 server: Union[TCPServer, MainServer],
                 client_socket: socket.socket,
                 address: Tuple[str, int]):

        super(ServerMessageHandler, self).__init__(client_socket, address)
        self.server = server

    def safe_print(self, *args, **kwargs):
        self.server.semaphore.acquire()
        print(*args, **kwargs)
        self.server.semaphore.release()
