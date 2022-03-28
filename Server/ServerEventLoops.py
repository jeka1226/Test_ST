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
    The class handle the request from client on the server. One thread - one user.
    """

    def __init__(self, server: MainServer, client_socket: socket.socket, address: Tuple[str, int]):
        """
        :param server: server
        :param client_socket: created socket descriptor
        :param address: tuple([ip: str, port: int])
        """
        super(UserEventLoop, self).__init__(server, client_socket, address)
        self.worker: Worker = server.worker  # worker, which do requested tasks
        self.thread: Thread = Thread(target=self.run, daemon=False)  # thread, which run the event loop
        self.data_to_send: deque = deque()  # queue to send data from server to client


    # the decorator provides removing connection from server
    @ServerMessageHandler.remove_connection_decorator
    def run(self):
        """
        client event loop
        """
        while self.is_active:  # while server is alive or client is connected - event loop is alive
            # checking if there is something to read or to write in socket
            ready_to_read, ready_to_write, in_error = select.select(
                [self.client_socket], [self.client_socket], [], self.loop_timeout)

            # if socket in the error, stop event loop
            if len(in_error) == 1:
                return

            # if there is data to read, read firstly
            if len(ready_to_read) == 1:
                try:
                    bytes_data: bytes = self.read_msg()  # get bytes data from server
                    decoded_data: list = BaseRequest.loads(bytes_data)  # convert bytes to list
                    command: str = decoded_data[1]  # get command
                    request: Union[ServerTask, ServerInfoRequest, ServerResultRequest, ServerStatusRequest] = \
                        commands[command](self, *decoded_data)  # create request object
                except TimeoutError:  # if TimeoutError occurred, clear request and continue
                    request = None
                except UnicodeError as ex:  # if UnicodeError occurred, inform user and clear request
                    self.safe_print(ex)
                    request = None
                except ConnectionError as ex:  # if ConnectionError occurred, inform user and stop event loop
                    self.safe_print(ex)
                    return
                except Exception as ex:   # if another error occurred, inform user and stop event loop
                    self.safe_print(ex)
                    return

                if request is not None:  # if there is request, run it
                    request.run()

            # if there is data to send, send it
            if len(ready_to_write) == 1 and len(self.data_to_send) >= 1:
                try:
                    response: Union[ServerTask, ServerInfoRequest, ServerResultRequest, ServerStatusRequest] = \
                        self.data_to_send.pop()
                    self.send_msg(response.dumps())
                except TimeoutError:  # ignore TimeoutError
                    pass
                except ConnectionError as ex:  # if ConnectionError occurred, inform user and stop event loop
                    self.safe_print(ex)
                    return
                except Exception as ex:  # if another error occurred, inform user and stop event loop
                    self.safe_print(ex)
                    return



class ResultWindowEventLoop(ServerMessageHandler):
    """
    The class handle the request from client on the server of result window. One thread - one user.
    """
    def __init__(self,
                 server: TCPServer,
                 client_socket: socket.socket,
                 address: Tuple[str, int]):
        """
        :param server: server
        :param client_socket: created socket descriptor
        :param address: tuple([ip: str, port: int])
        """
        super(ResultWindowEventLoop, self).__init__(server, client_socket, address)
        self.thread: Thread = Thread(target=self.run, daemon=False)  # thread, which run the event loop

    @ServerMessageHandler.remove_connection_decorator
    def run(self):
        """
        client event loop
        """
        while self.is_active:  # while server is alive or client is connected - event loop is alive
            # checking if there is something to read
            ready_to_read, ready_to_write, in_error = select.select(
                [self.client_socket], [], [], self.loop_timeout)

            if len(in_error) == 1:  # if socket in the error, stop event loop
                return

            # read and print data
            if len(ready_to_read) == 1:
                try:
                    bytes_data: bytes = self.read_msg()  # get bytes data from server
                    data = loads(bytes_data.decode('utf-8'))
                    data_to_print = data[0]  # get str from bytes
                    control_data = data[1]  # get control from bytes
                    if data_to_print:
                        self.safe_print(data_to_print)  # show data in terminal
                    if control_data == 'shutdown':
                        self.client_socket.close()
                        self.server.is_active = False
                        return
                except TimeoutError:  # ignore TimeoutError
                    pass
                except UnicodeError as ex:  # if ConnectionError occurred, inform user
                    self.safe_print(ex)
                except ConnectionError as ex:  # if ConnectionError occurred, inform user and stop event loop
                    self.safe_print(ex)
                    return
                except Exception as ex:  # if another error occurred, inform user and stop event loop
                    self.safe_print(ex)
                    return



class MainServer(TCPServer):
    """
    The class MainServer accept the connections from clients and put it in new thread.
    Also the class contain Worker in the attributes
    """
    def __init__(self, handler: type):
        """
        :param handler: class of client event loop
        """
        super(MainServer, self).__init__(handler)
        self.worker: Worker = None

    def set_worker(self, worker: Worker):
        """
        set worker object in the attribute
        :param worker: worker object, which handle a tasks from all clients
        """
        self.worker = worker

    def deactivate_threads(self):
        """
        deactivate client threads and worker thread
        """
        super(MainServer, self).deactivate_threads()
        self.worker.is_active = False

    def stop_server(self):
        """
        wait before client threads and worker thread will stop
        """
        super(MainServer, self).stop_server()
        try:
            self.worker.thread.join()
        except RuntimeError:
            pass

    def run(self, ip: str, port: int):
        """
        run client thread
        """
        self.worker.start()
        super(MainServer, self).run(ip, port)
