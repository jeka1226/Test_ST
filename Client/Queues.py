from __future__ import annotations

import platform
import time
from collections import deque
from json import dumps
from subprocess import Popen, DEVNULL
import sys
from threading import Thread
from typing import Dict, TYPE_CHECKING, Union, Deque

from src.ClientRequests import StatusRequest, ResultRequest, Task, InfoRequest, create_request
from src.Exceptions import BatchProcessingModeCommandError

if TYPE_CHECKING:
    from Client.ClientEventLoops import ClientEventLoop


class InputOutput:
    """
    Class contains three threads to control input and output
    """
    def __init__(self, event_handler: ClientEventLoop):
        """
        :param event_handler: client event loop
        """
        self.event_handler: ClientEventLoop = event_handler  # parent event loop
        self.data_to_show: deque = self.event_handler.queue.data_to_show  # queue with data to send to result window
        # function that creates request from user input
        self.create_request: callable = self.event_handler.queue.create_request

        self.threads_is_active = True  # flag: is all threads active
        # thread, which get user input and create requests
        self.input_thread: Thread = Thread(target=self.threading_input, daemon=True)
        # thread, which get send results to result window
        self.send_thread: Thread = Thread(target=self.send_results, daemon=False)
        # thread, which control subprocess with result window
        self.result_window: Thread = Thread(target=self.start_subprocess, daemon=False)
        self.result_window_subprocess: Popen = None  # Popen Constructor

        if self.event_handler.is_start_result_window:  # is result window needed, run subprocess in separate thread
            self.result_window.start()
            time.sleep(0.5)
        self.event_handler.result_window_sender.connect()  # connect to the result window
        self.input_thread.start()  # start thread
        self.send_thread.start()  # start thread


    def start_subprocess(self):
        """
        Creating the subprocess with result window
        """
        if platform.system() == 'Windows':
            self.result_window_subprocess = Popen(['start', '/wait', sys.executable, 'ResultWindow.py'],
                                                  shell=True, stderr=DEVNULL, stdout=DEVNULL)
        if platform.system() == 'Linux':
            self.result_window_subprocess = Popen(['gnome-terminal', '--wait', '--', sys.executable, 'sub.py'],
                                                  shell=False, stdout=DEVNULL, stderr=DEVNULL)


    def threading_input(self):
        """
        Read the input from the user
        """
        while self.threads_is_active:
            user_input: str = input('INPUT COMMAND:')
            if self.threads_is_active:
                self.event_handler.queue.create_request(user_input)  # create request


    def send_results(self):
        """
        send result to the result window
        """
        while self.threads_is_active:
            if len(self.data_to_show) > 0:
                data_to_send: list = self.data_to_show.pop()  # pop data from data_to_show queue
                data_to_send: str = dumps(data_to_send) + 'endofmsg'  # add end message part
                try:
                    self.event_handler.result_window_sender.send_msg(data_to_send.encode('utf-8'))  # send message
                except TimeoutError:  # ignore TimeoutError
                    pass
                except Exception as ex:  # catch exception and show to user
                    print(ex)
                    return


class BatchProcessingMode:
    """
    class contains status of batch processing mode and created task
    """
    def __init__(self, event_handler: ClientEventLoop):
        self.event_handler: ClientEventLoop = event_handler  # parent event loop
        self.status: bool = False  # batch processing mode status
        self.task: Task = None  # batch processing mode task


class Queue:
    """
    class the queues for sending requests, waiting response and showing results
    """
    def __init__(self, event_handler: ClientEventLoop):
        """
        :param event_handler: client event loop
        """
        self.event_handler: ClientEventLoop = event_handler  # parent event loop
        self.data_to_send: Deque = deque()  # request to send queue
        self.wait_for_result: Dict = dict()  # request to wait dict
        self.data_to_show: Deque = deque()  # response to show queue

    def create_request(self, user_input: str):
        """
        create request according to the user input
        :param user_input: user input
        """
        try:
            request: Union[StatusRequest, ResultRequest, Task, InfoRequest] = \
                create_request(user_input, self.event_handler)  # use function to create request

            # if batch processing mode is True, only 'status' and 'result' request available
            if self.event_handler.batch_processing_mode.status:
                if request.command != 'status' and request.command != 'result':
                    # raise exception if request is not 'status' and not 'result' in batch processing mode
                    raise BatchProcessingModeCommandError(request.command)

            self.handle_request(request)  # handle request
        except Exception as ex:  # if any exception occurred - add text of exception to the showing queue
            self.data_to_show.appendleft([str(ex), ''])


    def handle_request(self, request: Union[StatusRequest, ResultRequest, Task, InfoRequest]):
        """
        handle request according to request parameters
        """
        if request.command == 'task':  # if request is task and
            if request.is_batch_processing_mode:  # batch processing mode in task is true
                # set batch_processing_mode status and task
                self.event_handler.batch_processing_mode.status = True
                self.event_handler.batch_processing_mode.task = request
                # generate request for result of task and put it to the wait container
                result_request: ResultRequest = request.generate_result_request()
                self.wait_for_result[result_request.request_identifier_on_client] = result_request
                # inform user about activated batch_processing_mode
                self.data_to_show.appendleft(['Batch processing mode activated. '
                                             'Only "status" and "result" requests available', ''])
        # add request to the send request queue
        self.data_to_send.appendleft(request)


    def handle_response(self, response: Union[StatusRequest, ResultRequest, Task, InfoRequest]):
        """
        handle response from server
        """
        if response.request_identifier_on_client in self.wait_for_result.keys():  # if the response is expected
            del self.wait_for_result[response.request_identifier_on_client]   # remove request from waiting dict

            # updating task if batch processing mode is active and response contain identifier
            if self.event_handler.batch_processing_mode.status and \
                    response.request_identifier_on_client == \
                    self.event_handler.batch_processing_mode.task.request_identifier_on_client:
                self.event_handler.batch_processing_mode.task = response

            # add response to the showing queue
            self.data_to_show.appendleft([response.show_result(), ''])

            # deactivate batch processing mode if batch processing mode is active and
            # response contain result of task solving
            if self.event_handler.batch_processing_mode.status and \
                    response.request_identifier_on_client == \
                    self.event_handler.batch_processing_mode.task.request_identifier_on_result:
                self.event_handler.batch_processing_mode.status = False
                self.event_handler.batch_processing_mode.task = None
                self.data_to_show.appendleft(['Batch processing mode deactivated. Response with result received ', ''])
