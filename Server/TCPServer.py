from __future__ import annotations

import select
import socket
from threading import Semaphore


class TCPServer:
    def __init__(self, event_loop: type):
        self.event_loop: type = event_loop
        self.ip: str = None
        self.port: int = None
        self.server_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.semaphore = Semaphore(1)


    def safe_print(self, *args, **kwargs):
        self.semaphore.acquire()
        print(*args, **kwargs)
        self.semaphore.release()


    def run(self, ip: str, port: int):
        self.ip: str = ip
        self.port: int = port
        try:
            self.server_socket.bind((self.ip, self.port))
        except OSError as ex:
            self.safe_print(f"Can't bind address {self.ip}:{self.port}, OSError:", ex)
            return

        self.server_socket.listen(10)

        try:
            while True:
                # Wait for connection. Timeout is needed for interruption
                ready_to_read, ready_to_write, in_error = select.select(
                    [self.server_socket], [], [], 0.25
                )
                if not ready_to_read:
                    continue
                else:
                    client_socket, receiver_address = self.server_socket.accept()
                    self.safe_print('connected client:', receiver_address)
                    client_socket.setblocking(0)
                    client_handler = self.event_loop(self, client_socket, receiver_address)
                    client_handler.thread.start()

        except KeyboardInterrupt:
            return

        finally:
            self.safe_print('Exit server')
