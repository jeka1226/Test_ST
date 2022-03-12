from __future__ import annotations
import socket, select, time
from typing import List, Dict, Tuple, Any, TYPE_CHECKING, Union
from src.MessageHandlers import ClientMessageHandler
from Client.Stack import Stack, BatchProcessingMode, Input
from src.ClientRequests import commands, BaseRequest


if TYPE_CHECKING:
    from src.ClientRequests import StatusRequest, ResultRequest, InfoRequest, Task


class ClientEventLoop(ClientMessageHandler):
    """
    The class hold the connections with server

    **Object attributes:**
        *tcp_server* : is object of class TcpServer;
        *client_socket* : is socket of client;
        *client_address* : is tuple(ip: str, port: int);
        *thread* : is socket thread;
        *msg_len* : is length of message in bytes to receive;
    """
    def __init__(self,
                 client_socket: socket.socket,
                 address: Tuple[str, int],
                 result_window_sender: ClientMessageHandler,
                 is_start_result_window = True):

        super(ClientEventLoop, self).__init__(client_socket, address)
        self.request_num: int = 0
        self.is_start_result_window = is_start_result_window
        self.result_window_sender: ClientMessageHandler = result_window_sender
        self.stack: Stack = Stack(self)
        self.input: Input = Input(self)
        self.batch_processing_mode: BatchProcessingMode = BatchProcessingMode(self)


    def run(self):
        while True:
            try:
                ready_to_read, ready_to_write, in_error = select.select(
                    [self.client_socket], [self.client_socket], [], self.loop_timeout)

                if len(in_error) == 1:
                    raise ConnectionError('Socket error')

                # read data firstly if there is data to read
                if len(ready_to_read) == 1:
                    try:
                        bytes_data: bytes = self.read_msg()
                        decoded_data: list = BaseRequest.loads(bytes_data)
                        command: str = decoded_data[1]
                        response: Union[StatusRequest, ResultRequest, InfoRequest, Task] = \
                            commands[command](self, *decoded_data)
                        self.stack.handle_response(response)
                    except TimeoutError:
                        pass

                # send data if there is data to send
                if len(ready_to_write) == 1 and len(self.stack.data_to_send) >= 1:
                    try:
                        request = self.stack.data_to_send.pop()
                        self.send_msg(request.dumps())
                        self.stack.wait_for_result[request.request_identifier_on_client] = request
                    except TimeoutError:
                        pass


            except KeyboardInterrupt:
                if self.batch_processing_mode.status:
                    task: Task = self.batch_processing_mode.task
                    if task.request_identifier_on_result in self.stack.wait_for_result.keys():
                        del self.stack.wait_for_result[task.request_identifier_on_result]
                    self.batch_processing_mode.status = False
                    self.batch_processing_mode.task = None
                    self.stack.data_to_show.appendleft('Exit from batch processing mode')
                else:
                    self.client_socket.close()
                    self.input.stop_subprocess()
                    break

            except ConnectionError as ex:
                print(ex)
                self.input.stop_subprocess()
                break

            except Exception as ex:
                print(ex)
                self.input.stop_subprocess()
                break

        print('\nExit client')


