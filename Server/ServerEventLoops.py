from __future__ import annotations

import select
import socket
from collections import deque
from threading import Thread
from typing import Tuple, TYPE_CHECKING, Union
from json import loads

from Server.TCPServer import TCPServer
from src.ClientRequests import BaseRequest
from src.MessageHandlers import ServerMessageHandler
from src.ServerRequest import ServerTask, ServerInfoRequest, ServerResultRequest, ServerStatusRequest, commands

if TYPE_CHECKING:
    from Server.Worker import Worker


class UserEventLoop(ServerMessageHandler):
    """
    The class handle the request from client

    **Object attributes:**
        *tcp_server* : is object of class TcpServer;
        *client_socket* : is socket of client;
        *client_address* : is tuple(ip: str, port: int);
        *thread* : is socket thread;
        *msg_len* : is length of message in bytes to receive;
    """


    def __init__(self, server: MainServer, client_socket: socket.socket, address: Tuple[str, int]):
        super(UserEventLoop, self).__init__(server, client_socket, address)
        self.worker: Worker = server.worker
        self.thread: Thread = Thread(target=self.run, daemon=True)
        self.data_to_send: deque = deque()
        self.request_num = 0


    def run(self):
        while True:
            ready_to_read, ready_to_write, in_error = select.select(
                [self.client_socket], [self.client_socket], [], self.loop_timeout)

            if len(in_error) == 1:
                return

            # if there is data to read, read firstly
            if len(ready_to_read) == 1:
                try:
                    bytes_data: bytes = self.read_msg()
                    decoded_data: list = BaseRequest.loads(bytes_data)
                    command: str = decoded_data[1]
                    request: Union[ServerTask, ServerInfoRequest, ServerResultRequest, ServerStatusRequest] = \
                        commands[command](self, *decoded_data)
                    self.safe_print('received_data:', str(request))
                except TimeoutError as ex:
                    self.safe_print(ex)
                    request = None
                except ConnectionError as ex:
                    self.safe_print(ex)
                    return
                except UnicodeError as ex:
                    self.safe_print(ex)
                    return
                except Exception as ex:
                    self.safe_print(ex)
                    return


                if request is not None:
                    request.run()


            # if there is data to send, send it
            if len(ready_to_write) == 1 and len(self.data_to_send) >= 1:
                try:
                    response: Union[ServerTask, ServerInfoRequest, ServerResultRequest, ServerStatusRequest] = \
                        self.data_to_send.pop()
                    self.safe_print(response.show_result())
                    self.send_msg(response.dumps())
                except TimeoutError as ex:
                    self.safe_print(ex)
                    continue
                except ConnectionError as ex:
                    self.safe_print(ex)
                    return
                except Exception as ex:
                    self.safe_print(ex)
                    return



class ResultWindowEventLoop(ServerMessageHandler):
    def __init__(self,
                 server: TCPServer,
                 client_socket: socket.socket,
                 address: Tuple[str, int]):

        super(ResultWindowEventLoop, self).__init__(server, client_socket, address)
        self.thread: Thread = Thread(target=self.run, daemon=True)

    def run(self):
        while True:
            ready_to_read, ready_to_write, in_error = select.select(
                [self.client_socket], [], [], self.loop_timeout)

            if len(in_error) == 1:
                return

            # read and print data
            if len(ready_to_read) == 1:
                try:
                    bytes_data: bytes = self.read_msg()
                    data_to_print = loads(bytes_data.decode('utf-8'))[0]
                    self.safe_print(data_to_print)
                except TimeoutError as ex:
                    self.safe_print(ex)
                except ConnectionError as ex:
                    self.safe_print(ex)
                    return
                except UnicodeError as ex:
                    self.safe_print(ex)
                    return
                except Exception as ex:
                    self.safe_print(ex)
                    return



class MainServer(TCPServer):
    """
    The class TCPServer accept the connections from clients and put it in new thread

    **Object attributes:**
        *handler* : is class of client handle;
        *worker* : is object of class Worker;
        *ip* : is server ip;
        *port* : is server port;
        *server_socket* : is socket of server;
    """
    def __init__(self, handler: type):
        super(MainServer, self).__init__(handler)
        self._worker: Worker = None

    @property
    def worker(self):
        return self._worker
    @worker.setter
    def worker(self, value: Worker):
        self._worker: Worker = value

    def run(self, ip: str, port: int):
        super(MainServer, self).run(ip, port)
