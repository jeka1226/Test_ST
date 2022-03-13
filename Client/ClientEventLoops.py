from __future__ import annotations

import select
import socket
from typing import Tuple, TYPE_CHECKING, Union
from functools import wraps

from Client.Queues import Queue, BatchProcessingMode, InputOutput
from src.ClientRequests import commands, BaseRequest
from src.MessageHandlers import ClientMessageHandler

if TYPE_CHECKING:
    from src.ClientRequests import StatusRequest, ResultRequest, InfoRequest, Task


class ClientEventLoop(ClientMessageHandler):
    """
    The class contains event loops for client.
    There is 4 threads inside of input_output attribute:
        main thread - send requests and receives the results from server
        send_thread - sends results to result window
        result_window - provides connection to subprocess of result window (it open and close this window)
        input_thread - provides continuous input by user. This thread is daemon = True because it can't to
            be stopped when wait stdin

    """
    def __init__(self,
                 client_socket: socket.socket,
                 address: Tuple[str, int],
                 result_window_sender: ClientMessageHandler,
                 is_start_result_window: bool = True):
        """
        :param client_socket: created socket descriptor
        :param address: tuple([ip: str, port: int])
        :param result_window_sender: message sender to the result window
        :param is_start_result_window: is start result window (user defined)
        """
        super(ClientEventLoop, self).__init__(client_socket, address)
        self.request_num: int = 0  # counter of requests on client
        self.is_start_result_window = is_start_result_window  # is start result window (user defined)
        self.result_window_sender: ClientMessageHandler = result_window_sender  # message sender to the result window
        self.queue: Queue = Queue(self)  # queue: requests to send, waiting for response and, results for show
        self.input_output: InputOutput = InputOutput(self)  # input/output threads here
        self.batch_processing_mode: BatchProcessingMode = BatchProcessingMode(self)  # batch processing mode info


    def connect(self, *args, **kwargs):
        """
        Stop all threads, except input_thread. Because input_thread is daemon = True
        """
        try:
            super(ClientEventLoop, self).connect(*args, **kwargs)  # inherited connect method try to connect
        except KeyboardInterrupt:  # if keyboard interrupt the threads stop
            self.stop_threads()
            print('\nExit client')  # inform user


    def stop_threads(self):
        """
        Stop all threads, except input_thread. Because input_thread is daemon = True
        """
        self.input_output.threads_is_active = False  # deactivate threads
        self.input_output.send_thread.join()  # wait for send_thread finished
        self.input_output.stop_subprocess()  # send kill result window
        self.input_output.result_window.join()  # wait for result_window thread finished


    def run_decorator(fun: callable):
        """
        It is decorator for event loop. When user want to shutdown server, the decorator provides stop all threads.
        """
        @wraps(fun)
        def wrapper(self: ClientEventLoop, *args, **kwargs):
            if self.is_connected:
                fun(self, *args, **kwargs)  # run decorated function
                self.stop_threads()
                print('\nExit client')  # inform user
        return wrapper


    @run_decorator
    def run(self):
        """
        IT is event loop in main_thread. It send requests and receives the results from server
        """

        while True:
            try:  # catch the exceptions in event loop
                # checking if there is something to read or to write in socket
                ready_to_read, ready_to_write, in_error = select.select(
                    [self.client_socket], [self.client_socket], [], self.loop_timeout)

                # if socket in the error, raise exception and stop event loop
                if len(in_error) == 1:
                    raise ConnectionError('Socket error')

                # read data firstly if there is data to read
                if len(ready_to_read) == 1:
                    try:
                        bytes_data: bytes = self.read_msg()  # get bytes data from server
                        decoded_data: list = BaseRequest.loads(bytes_data)  # convert bytes to list
                        command: str = decoded_data[1]  # get command type
                        response: Union[StatusRequest, ResultRequest, InfoRequest, Task] = \
                            commands[command](self, *decoded_data)  # create request object
                    except TimeoutError:  # clear response if TimeoutError
                        response = None
                    except UnicodeError:  # clear response if UnicodeError
                        response = None

                    if response is not None:
                        self.queue.handle_response(response)  # send request object in response handler

                # send data if there is data to send
                if len(ready_to_write) == 1 and len(self.queue.data_to_send) >= 1:
                    try:
                        request = self.queue.data_to_send.pop()  # pop request from queue
                        self.send_msg(request.dumps())  # dump request to bytes and send to server bytes data
                        # move request to waiting container (dict)
                        self.queue.wait_for_result[request.request_identifier_on_client] = request
                    except TimeoutError:  # ignore timeout error
                        pass


            except KeyboardInterrupt:  # if keyboard interrupted
                if self.batch_processing_mode.status:  # if in batch processing mode, then exit from this mode
                    task: Task = self.batch_processing_mode.task
                    # remove request which wait for result from waiting container
                    if task.request_identifier_on_result in self.queue.wait_for_result.keys():
                        del self.queue.wait_for_result[task.request_identifier_on_result]
                    self.batch_processing_mode.status = False
                    self.batch_processing_mode.task = None
                    # inform user about exit from batch processing mode
                    self.queue.data_to_show.appendleft('Exit from batch processing mode')
                else:
                    self.client_socket.close()  # if not in batch processing mode, then close connection by socket
                    return

            except ConnectionError as ex:  # if ConnectionError occurred, then exit from client
                print(ex)
                return

            except Exception as ex:   # if another exception occurred, then exit from client
                print(ex)
                return

    run_decorator = staticmethod(run_decorator)  # convert stop_threads method to static
