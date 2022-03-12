from __future__ import annotations
from src.ClientRequests import ResultRequest, StatusRequest, InfoRequest, Task
from typing import List, Dict, Tuple, Any, TYPE_CHECKING, Union
from src.Exceptions import IdentifierNotFound
import time


if TYPE_CHECKING:
    from Server.ServerEventLoops import UserEventLoop


class ServerRequest:
    def run(self):
        self.event_handler: UserEventLoop
        self.event_handler.data_to_send.appendleft(self)


class ServerResultRequest(ResultRequest, ServerRequest):
    def __init__(self, *args, **kwargs):
        super(ServerResultRequest, self).__init__(*args, **kwargs)

    def run(self):
        self.event_handler.worker.semaphore.acquire()
        if self.identifier not in self.event_handler.worker.tasks.keys():
            self.error = str(IdentifierNotFound(self.identifier))
            self.result = None
        else:
            task: WorkerTask = self.event_handler.worker.tasks[self.identifier]
            self.error = None
            self.result: str = task.result
        self.event_handler.worker.semaphore.release()
        super().run()


class ServerStatusRequest(StatusRequest, ServerRequest):
    def __init__(self, *args, **kwargs):
        super(ServerStatusRequest, self).__init__(*args, **kwargs)

    def run(self):
        self.event_handler.worker.semaphore.acquire()
        if self.identifier not in self.event_handler.worker.tasks.keys():
            self.error = str(IdentifierNotFound(self.identifier))
            self.result = None
        else:
            task: WorkerTask = self.event_handler.worker.tasks[self.identifier]
            self.error = None
            self.result: str = task.status
        self.event_handler.worker.semaphore.release()
        super().run()


class ServerInfoRequest(InfoRequest, ServerRequest):
    def __init__(self, *args, **kwargs):
        super(ServerInfoRequest, self).__init__(*args, **kwargs)

    def run(self):
        self.event_handler.worker.semaphore.acquire()
        if self.command == 'help':
            self.result: str = application_help
        elif self.command == 'identifiers':
            self.result: str = str(list(self.event_handler.worker.tasks.keys()))[1:-1]
        self.event_handler.worker.semaphore.release()
        super().run()
        pass


class ServerTask(Task, ServerRequest):
    def __init__(self, *args, **kwargs):
        super(ServerTask, self).__init__(*args, **kwargs)

    def run(self):
        self.event_handler.worker.semaphore.acquire()
        self.event_handler.worker.current_identifier += 1
        task_identifier = self.event_handler.worker.current_identifier
        self.result = task_identifier

        # create WorkerTask
        worker_task = WorkerTask(
            self.event_handler,
            self.request_identifier_on_client,
            self.command,
            self.error,
            self.task_type,
            self.is_batch_processing_mode,
            self.request_identifier_on_result,
            self.data,
            task_identifier)

        # add WorkerTask in deque
        self.event_handler.worker.tasks[task_identifier] = worker_task
        self.event_handler.worker.deque.appendleft(task_identifier)
        self.event_handler.worker.semaphore.release()
        super().run()


commands = {'status': ServerStatusRequest, 'result': ServerResultRequest,
            'help': ServerInfoRequest, 'identifiers': ServerInfoRequest,
            'task': ServerTask}


application_help = """
    THIS
    IS
    HELP
    """


class WorkerTask:
    def __init__(self,
                 event_handler: UserEventLoop,
                 request_identifier_on_client: int,
                 command: str,
                 error: str,
                 task_type: str,
                 is_batch_processing_mode: bool,
                 request_identifier_on_result: int,
                 data: str,
                 identifier: str):


        self.event_handler: UserEventLoop = event_handler
        self.request_identifier_on_client: int = request_identifier_on_client
        self.command: str = command
        self.error: str = error
        self.task_type: str = task_type
        self.is_batch_processing_mode = is_batch_processing_mode
        self.request_identifier_on_result = request_identifier_on_result
        self.data = data
        self.identifier = identifier

        self.result = None
        self.status: str = 'wait to deque'


    def symbol_repeat(self):
        time.sleep(7)
        self.result = ''.join(list(s*(num+1) for num, s in enumerate(self.data)))


    def pair_permutation(self):
        time.sleep(5)
        len_data = len(self.data)
        self.result = ''.join(
            list(
                self.data[num + 1] + self.data[num]
                if num < len_data - 1
                else self.data[num]
                for num in range(0, len_data, 2)
            )
        )


    def reverse(self):
        time.sleep(15)
        self.result = self.data[::-1]


    def run(self):
        self.status = 'in work'
        self.__getattribute__(self.task_type.lstrip('-'))()
        if self.is_batch_processing_mode:
            # create result response
            result_response = ServerResultRequest(
                self.event_handler,
                self.request_identifier_on_result,
                'result',
                None,
                self.identifier,
                self.result)

            self.event_handler.data_to_send.appendleft(result_response)
        self.status = 'done'
