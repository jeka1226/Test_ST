from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Union

from src.ClientRequests import ResultRequest, StatusRequest, InfoRequest, Task
from src.Exceptions import IdentifierNotFound

if TYPE_CHECKING:
    from Server.ServerEventLoops import UserEventLoop
    from Server.Worker import WorkerTask


application_help = """
    You can use 5 commands to control server
        task [option] [batch processing mode] [value]
            create task on server
        
            options                   : type of task
                --reverse             : to reverse symbols in value
                --pair_permutation    : to pairwise characters in a string
                --symbol_repeat       : to repeat symbols according their positions
            
            batch processing mode:
                -b                    : to start task in batch processing mode
            
            value                     : any symbols
            
            
        status [identifier]
            get task status
            
            identifier                : unique identifier, that was generated by task request            
            
            in batch processing mode identifier not taken into account
            
        result [identifier]
            get task result
            
            identifier                : unique identifier, that was generated by task request            
            
            in batch processing mode identifier not taken into account
            
        identifiers
            get identifiers all task
            
        help
            get help
    """



def semaphore_decorator(func: callable) -> callable:
    """
    Decorator of method "run" in classes:
    Union[ServerResultRequest, ServerInfoRequest, ServerStatusRequest, ServerTask]
    It provides safe access to the information in Worker
    """

    @wraps(func)
    def wrapper(self: Union[ServerResultRequest, ServerInfoRequest, ServerStatusRequest, ServerTask],
                *args,
                **kwargs):
        """semaphore.acquire before func() and semaphore.release before exit"""
        self.event_handler.worker.semaphore.acquire()  # block
        func(self, *args, **kwargs)
        self.event_handler.worker.semaphore.release()  # unblock
        self.event_handler.data_to_send.appendleft(self)  # add data to the data_to_send container
    return wrapper


class ServerResultRequest(ResultRequest):
    """
    result request class on server side.
    """
    @semaphore_decorator
    def run(self):
        self.event_handler: UserEventLoop
        # add error info if requested identifier not exit
        if self.identifier not in self.event_handler.worker.tasks.keys():
            self.error = str(IdentifierNotFound(self.identifier))
            self.result = None
        else:  # add result of task if requested identifier exit
            task: WorkerTask = self.event_handler.worker.tasks[self.identifier]
            self.error = None
            self.result: str = task.result


class ServerStatusRequest(StatusRequest):
    """
    status request class on server side.
    """
    @semaphore_decorator
    def run(self):
        self.event_handler: UserEventLoop
        # add error info if requested identifier not exit
        if self.identifier not in self.event_handler.worker.tasks.keys():
            self.error = str(IdentifierNotFound(self.identifier))
            self.result = None
        else:  # add status of task if requested identifier exit
            task: WorkerTask = self.event_handler.worker.tasks[self.identifier]
            self.error = None
            self.result: str = task.status


class ServerInfoRequest(InfoRequest):
    """
    info request class on server side.
    """
    @semaphore_decorator
    def run(self):
        self.event_handler: UserEventLoop
        if self.command == 'help':
            self.result: str = application_help  # add help info
        elif self.command == 'identifiers':
            # add list of identifiers
            self.result: str = str(list(self.event_handler.worker.tasks.keys()))[1:-1]


class ServerTask(Task):
    """
    create task request class on server side.
    """
    @semaphore_decorator
    def run(self):
        self.event_handler: UserEventLoop

        task_identifier = self.event_handler.worker.add_task(self)  # get st
        self.result = task_identifier


commands = {'status': ServerStatusRequest, 'result': ServerResultRequest,
            'help': ServerInfoRequest, 'identifiers': ServerInfoRequest,
            'task': ServerTask}
