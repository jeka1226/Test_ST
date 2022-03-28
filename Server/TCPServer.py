from __future__ import annotations

import select
import socket
from threading import Semaphore
from typing import List, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from Server.ServerEventLoops import UserEventLoop, ResultWindowEventLoop


class TCPServer:
    """
    TCP Server always wait the connection from the client in main thread.
    If there is request for connection, server accept it.
    Server put the connection to a new thread and start it.
    All connections saves in attribute *threads*.
    """
    def __init__(self, event_loop: type):
        """
        :param event_loop: class of client event loop
        """
        self.event_loop: type = event_loop  # class of client event loop
        self.ip: str = None  # server ip
        self.port: int = None  # server port
        self.server_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # server socket
        self.semaphore: Semaphore = Semaphore(1)  # semaphore for stdout
        self.sockets: List[Union[UserEventLoop, ResultWindowEventLoop], ...] = list()  # list of connections
        self.listen = 10  # maximum connections
        self.is_active = True

    def deactivate_threads(self):
        """
        deactivate all client event loops
        """
        for i in self.sockets:
            i.is_active = False

    def stop_server(self):
        """
        wait for event loops stopped
        """
        self.is_active = False
        self.deactivate_threads()
        for i in self.sockets:
            try:
                i.thread.join()  # wait for event loop stopped
            except RuntimeError:  # catch RuntimeError and continue if thread not started
                continue


    def safe_print(self, *args, **kwargs):
        """
        single thread access to print
        """
        self.semaphore.acquire()  # block access
        print(*args, **kwargs)
        self.semaphore.release()  # unblock access


    def run(self, ip: str, port: int):
        """
        Main event loop of server
        :param ip: server ip
        :param port: server port
        """
        self.ip: str = ip  # assignment ip
        self.port: int = port  # assignment port
        try:
            self.server_socket.bind((self.ip, self.port))  # server bind address
        except OSError as ex:
            self.safe_print(f"Server can't bind address {self.ip}:{self.port}, OSError:", ex)
            self.stop_server()  # stop all threads and server
            return

        self.server_socket.listen(self.listen)  # set limit of connections

        try:
            while self.is_active:
                # Wait for connection. Timeout 0.25s is needed for interruption
                ready_to_read, ready_to_write, in_error = select.select(
                    [self.server_socket], [], [], 0.25
                )
                if not ready_to_read:  # if no request for connections, continue to wait
                    continue
                else:  # if there is request for connections, accept it
                    client_socket, receiver_address = self.server_socket.accept()  # get socket descriptor and address
                    # self.safe_print('Connected client:', receiver_address)
                    client_socket.setblocking(0)  # set blocking False
                    client_handler = self.event_loop(self, client_socket, receiver_address)  # create event loop
                    self.sockets.append(client_handler)  # append client event loop in list
                    client_handler.thread.start()  # start client event loop

            self.stop_server()  # stop all threads and server

        except KeyboardInterrupt:  # if user press ctrl+C
            self.stop_server()  # stop all threads and server

        finally:
            self.safe_print('Exit server')  # inform user
