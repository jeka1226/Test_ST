from __future__ import annotations

import select
import socket
import time
from functools import wraps
from typing import Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from Server.ServerEventLoops import MainServer, UserEventLoop, ResultWindowEventLoop
    from Server.TCPServer import TCPServer


class DataTransfer:
    """
    class gives methods for send and receive bytes data using socket
    """
    def __init__(self,
                 client_socket: socket.socket,
                 address: Tuple[str, int]):
        """
        :param client_socket: created socket descriptor
        :param address: tuple([ip: str, port: int])
        """
        self.client_socket: socket.socket = client_socket  # created socket descriptor
        self.address: Tuple[str, int] = address  # tuple([ip: str, port: int])
        self.msg_len: int = 2048  # maximum len of one package
        self.send_timeout: float = 5.0  # timeout to send message
        self.read_timeout: float = 5.0  # timeout to receive message
        self.loop_timeout: float = 0.1  # event loop timeout


    def read_msg(self) -> bytes:
        """
        function is used to read data from socket
        :return data: received bytes
        """
        data = bytes(0)  # create empty bytes container
        while True:
            ready_to_read, ready_to_write, in_error = select.select(
                [self.client_socket], [], [], self.read_timeout)  # wait before socket will be ready to read

            if not ready_to_read:  # if no socket, raise timeout
                raise TimeoutError(f'Timeout to get data from {self.address}')
            package: bytes = ready_to_read[0].recv(self.msg_len)

            if not package:  # if 0 bytes received, raise ConnectionError
                raise ConnectionError(f'Connection lost with {self.address}. 0 bytes received')

            data += package  # add received data
            try:  # check for the special characters "endofmsg" meaning end of message
                if data[-8:].decode('utf-8') == 'endofmsg':
                    data = data[0:-8]  # remove special characters from message
                    break  # exit from loop
            except UnicodeError:  # if UnicodeError, it is not end of message
                pass  # continue loop
        return data


    def send_msg(self, encoded_data: bytes) -> None:
        """
        function is used to send data
        :param encoded_data: bytes data to send
        """
        msg_len = len(encoded_data)  # len of message
        total_sent = 0  # counter of sent data

        while total_sent < msg_len:  # while not all bytes sent
            ready_to_read, ready_to_write, in_error = select.select(
                [], [self.client_socket], [], self.send_timeout)  # wait before socket will be ready to send
            if not ready_to_write:  # if no socket, raise timeout
                raise TimeoutError(f'Timeout to send message to {self.address}')
            sent = ready_to_write[0].send(encoded_data[total_sent:])  # sent bytes
            if sent == 0:  # if sent 0 raise ConnectionError
                raise ConnectionError(f"Connection lost with {self.address}. 0 bytes sent")
            total_sent = total_sent + sent  # update counter


class ClientMessageHandler(DataTransfer):
    """
    class gives methods for client connection
    """
    def __init__(self,
                 client_socket: socket.socket,
                 address: Tuple[str, int]):
        """
        :param client_socket: created socket descriptor
        :param address: tuple([ip: str, port: int])
        """
        super(ClientMessageHandler, self).__init__(client_socket, address)
        self.is_connected = False  # is successfully connected

    def connect(self, n_max=10):
        """
        connect to server
        :param n_max:  max count of tries to connect. If n_max = None then n_max is infinite
        """
        n = 0  # current connection try count
        if n_max is None:
            _n_max = n + 1  # private max count is always more then current connection try count
        else:
            _n_max = n_max  # private max count is equal n_max

        while not self.is_connected and n < _n_max:  # while connection is not successful and not achieved n_max
            try:  # try to connect
                self.client_socket.connect(self.address)
                self.is_connected = True  # connection is successful
            except ConnectionError as ex:  # if ConnectionError
                if n >= _n_max:  # if current connection try count more then private max count raise connection error
                    raise ConnectionError(f"Can't connect to {self.address}. Connection error: {str(ex)}")
                time.sleep(1)  # wait for server and try again

            n += 1  # update count
            if n_max is None:
                _n_max = n + 1  # update private max count if n_max is None


class ServerMessageHandler(DataTransfer):
    """
    class gives methods for remove connection from server and safe print any data
    """
    def __init__(self,
                 server: Union[TCPServer, MainServer],
                 client_socket: socket.socket,
                 address: Tuple[str, int]):
        """
        :param server: server
        :param client_socket: created socket descriptor
        :param address: tuple([ip: str, port: int])
        """
        super(ServerMessageHandler, self).__init__(client_socket, address)
        self.server = server  # server
        self.is_active = True  # is active thread


    def remove_connection_decorator(fun: callable) -> callable:
        """
        the function is the decorator of client event loop
        :param fun: event loop of client connection
        :return: wrapped function, that remove event loop class from server
        """
        @wraps(fun)
        def wrapper(self: Union[UserEventLoop, ResultWindowEventLoop], *args, **kwargs):
            fun(self, *args, **kwargs)  # call decorated function
            self.server.sockets.remove(self)  # remove event loop class from server
        return wrapper


    def safe_print(self, *args, **kwargs):
        """
        single thread access to print
        """
        self.server.semaphore.acquire()  # block access
        print(*args, **kwargs)
        self.server.semaphore.release()  # unblock access

    remove_connection_decorator = staticmethod(remove_connection_decorator)  # wrap in staticmethod
