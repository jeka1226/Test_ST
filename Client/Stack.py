from __future__ import annotations
import time
from typing import List, Dict, Tuple, Any, TYPE_CHECKING, Union, Deque
from src.ClientRequests import StatusRequest, ResultRequest, Task, InfoRequest, create_request
from src.Exceptions import BatchProcessingModeCommandError, BatchProcessingTaskIdentifierNotFound
from collections import deque
import sys
from json import dumps
from threading import Thread
from subprocess import PIPE, Popen, DEVNULL, call

if TYPE_CHECKING:
    from Client.ClientEventLoops import ClientEventLoop


class Input:
    def __init__(self, event_handler: ClientEventLoop):
        self.event_handler: ClientEventLoop = event_handler
        self.data_to_show: deque = self.event_handler.stack.data_to_show
        self.create_request: callable = self.event_handler.stack.create_request

        self.input_thread: Thread = Thread(target=self.threading_input, daemon=True)
        self.send_thread: Thread = Thread(target=self.send_results, daemon=True)
        self.result_window: Thread = Thread(target=self.start_subprocess, daemon=True)
        self.result_window_subprocess: Popen = None

        if self.event_handler.is_start_result_window:
            self.result_window.start()
            time.sleep(0.5)
        self.event_handler.result_window_sender.connect()
        self.input_thread.start()
        self.send_thread.start()


    def start_subprocess(self):
        self.result_window_subprocess = Popen(['start', '/wait', 'python', 'ResultWindow.py'], shell=True,
                                              stderr=DEVNULL, stdout=DEVNULL)
        self.result_window_subprocess.wait()
        print('\nResultWindow closed')

    def stop_subprocess(self):
        if self.event_handler.is_start_result_window:
            call(['taskkill', '/F', '/T', '/PID', str(self.result_window_subprocess.pid)],
                  stderr=DEVNULL, stdout=DEVNULL)


    def threading_input(self):
        while True:
            user_input: str = input('INPUT COMMAND:')
            self.event_handler.stack.create_request(user_input)

    def send_results(self):
        time.sleep(0.5)
        while True:
            if len(self.data_to_show) > 0:
                data_to_send: str = self.data_to_show.pop()
                data_to_send = dumps([data_to_send]) + 'endofmsg'
                try:
                    self.event_handler.result_window_sender.send_msg(data_to_send.encode('utf-8'))
                except TimeoutError:
                    print('TimeoutError')
                except Exception as ex:
                    print(ex)
                    return


class BatchProcessingMode:
    def __init__(self, event_handler: ClientEventLoop):
        self.event_handler: ClientEventLoop = event_handler
        self.status: bool = False
        self.task: Task = None


class Stack:
    def __init__(self, event_handler: ClientEventLoop):
        self.event_handler: ClientEventLoop = event_handler
        self.data_to_send: Deque = deque()
        self.wait_for_result: Dict = dict()
        self.data_to_show: Deque = deque()


    def handle_response(self, response: Union[StatusRequest, ResultRequest, Task, InfoRequest]):
        if response.request_identifier_on_client in self.wait_for_result.keys():
            del self.wait_for_result[response.request_identifier_on_client]

            if self.event_handler.batch_processing_mode.status and \
                    response.request_identifier_on_client == \
                    self.event_handler.batch_processing_mode.task.request_identifier_on_client:
                self.event_handler.batch_processing_mode.task = response

            if self.event_handler.batch_processing_mode.status and \
                    response.request_identifier_on_client == \
                    self.event_handler.batch_processing_mode.task.request_identifier_on_result:
                self.event_handler.batch_processing_mode.status = False
                self.event_handler.batch_processing_mode.task = None
            self.data_to_show.appendleft(response.show_result())


    def create_request(self, user_input: str):
        try:
            request: Union[StatusRequest, ResultRequest, Task, InfoRequest] = create_request(user_input, self.event_handler)
            if self.event_handler.batch_processing_mode.status:
                if request.command != 'status' and request.command != 'result':
                    raise BatchProcessingModeCommandError(request.command)

            self.handle_request(request)
        except Exception as ex:
            self.data_to_show.appendleft(str(ex))


    def handle_request(self, request: Union[StatusRequest, ResultRequest, Task, InfoRequest]):
        if request.command == 'task':
            if request.is_batch_processing_mode:
                self.event_handler.batch_processing_mode.status = True
                self.event_handler.batch_processing_mode.task = request
                result_request: ResultRequest = request.generate_result_request()
                self.wait_for_result[result_request.request_identifier_on_client] = result_request
        self.data_to_send.appendleft(request)
