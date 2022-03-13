from __future__ import annotations

import re
from json import dumps, loads
from typing import TYPE_CHECKING, Union
from src.Exceptions import CommandNotFound, IdentifierNotFound, TaskTypeNotFound, BatchProcessingTaskIdentifierNotFound

if TYPE_CHECKING:
    from Client.ClientEventLoops import ClientEventLoop
    from Server.ServerEventLoops import UserEventLoop



class BaseRequest:
    """
    Base request class
    """
    def __init__(self,
                 event_handler: Union[ClientEventLoop, UserEventLoop],
                 request_identifier_on_client: int,
                 command: str,
                 error: str):
        """
        :param event_handler: event loop class on server or client side
        :param request_identifier_on_client: registered identifier of request on client side
        :param command: request type
        :param error: error occurred when creating the request
        """
        self.event_handler: Union[ClientEventLoop, UserEventLoop] = event_handler
        self.request_identifier_on_client: int = request_identifier_on_client
        self.command: str = command
        self.error: str = error

    def __str__(self) -> str:
        """string representation of request (user input form)"""
        return str(self.command)

    @staticmethod
    def dump(value: list) -> bytes:
        """
        serialization message to json and then encode to the bytes
        :param value: list of all parameters
        """
        return (dumps(value) + 'endofmsg').encode('utf-8')

    @classmethod
    def loads(cls, value: bytes) -> tuple:
        """
        decode bytes to string, then deserialization from json and create tuple of values
        :param value: bytes data
        """
        value: str = value.decode('utf-8')
        value: list = loads(value)
        return tuple(i for i in value)

    @classmethod
    def get_data_from_str(cls, event_handler, command: str, user_input: str) -> int:
        """parser of user input"""
        event_handler.request_num += 1  # increase request_num
        return event_handler.request_num

    def show_result(self) -> str:
        """get string representation of response"""
        return self.command

    def dumps(self) -> bytes:
        """serialization of self to list"""
        return bytes()


class StatusAndResult(BaseRequest):
    """Base class for status and result request"""

    def __init__(self,
                 event_handler: ClientEventLoop,
                 request_identifier_on_client: int,
                 command: str,
                 error: str,
                 identifier: int):
        """
        :param identifier: identifier of task
        """
        super(StatusAndResult, self).__init__(event_handler, request_identifier_on_client, command, error)
        self.identifier: int = identifier  # identifier of requested status  or result

    def __str__(self) -> str:
        return str(self.command) + ' ' + str(self.identifier)

    def show_result(self) -> str:
        self.result: property
        string = str(self.command) + ', ' + str(self.identifier) + ': ' + str(self.result) \
            if self.error is None else str(self.error)
        return string

    @classmethod
    def get_data_from_str(cls, event_handler, command: str, user_input: str) -> tuple:
        request_identifier_on_client: int = super().get_data_from_str(event_handler, command, user_input)
        error = None
        result = None
        # get identifier from Task if batch processing mode is True
        if event_handler.batch_processing_mode.status:
            identifier = event_handler.batch_processing_mode.task.result
            if identifier is None:
                raise BatchProcessingTaskIdentifierNotFound()
        # get identifier from user input if batch processing mode is False
        else:
            re_obj = re.search(f'^\s*{command}\s\s*', user_input)
            if re_obj is None:
                raise IdentifierNotFound(None)
            identifier = user_input[re_obj.end():]

        try:
            identifier = int(identifier)
        except ValueError:
            raise ValueError('ValueError. Identifier must be integer')

        return event_handler, request_identifier_on_client, command, error, identifier, result

    def dumps(self) -> bytes:
        self.result: property
        return self.dump([self.request_identifier_on_client, self.command, self.error, self.identifier, self.result])


class StatusRequest(StatusAndResult):
    """Status request class"""
    def __init__(self,
                 event_handler: ClientEventLoop,
                 request_identifier_on_client: int,
                 command: str,
                 error: str,
                 identifier: int,
                 result: str
                 ):
        """
        :param result: status of task
        """
        super(StatusRequest, self).__init__(event_handler, request_identifier_on_client, command, error, identifier)
        self.result = result  # is the descriptor of _status

    @property
    def result(self) -> str:
        """status of task"""
        return self._status
    @result.setter
    def result(self, value):
        """status of task"""
        self._status = value


class ResultRequest(StatusAndResult):
    """Result request class"""
    def __init__(self,
                 event_handler: ClientEventLoop,
                 request_identifier_on_client: int,
                 command: str,
                 error: str,
                 identifier: int,
                 result: str
                 ):
        """
        :param result: result of task
        """
        super(ResultRequest, self).__init__(event_handler, request_identifier_on_client, command, error, identifier)
        self.result = result  # is the descriptor of _result

    @property
    def result(self) -> str:
        """result of task"""
        return self._result
    @result.setter
    def result(self, value):
        """result of task"""
        self._result = value


class InfoRequest(BaseRequest):
    """
    Class for requests: help, identifiers
    """
    def __init__(self,
                 event_handler: ClientEventLoop,
                 request_identifier_on_client: int,
                 command: str,
                 error: str,
                 result: str):
        """
        :param result: help or identifiers
        """
        super(InfoRequest, self).__init__(event_handler, request_identifier_on_client, command, error)
        self.result = result

    @property
    def result(self) -> str:
        """help or identifiers"""
        return self._info
    @result.setter
    def result(self, value):
        """help or identifiers"""
        self._info = value

    def show_result(self) -> str:
        string = str(self.command) + ': ' + str(self.result) if self.error is None else str(self.error)
        return string

    def dumps(self) -> bytes:
        return self.dump([self.request_identifier_on_client, self.command, self.error, self.result])

    @classmethod
    def get_data_from_str(cls, event_handler, command: str, user_input: str) -> tuple:
        request_identifier_on_client: int = super().get_data_from_str(event_handler, command, user_input)
        error = None
        result = None
        return event_handler, request_identifier_on_client, command, error, result



class Task(BaseRequest):
    """
    Class for task. Task type can be: --symbol_repeat, --pair_permutation, --reverse
    """
    task_types: tuple = ('--symbol_repeat', '--pair_permutation', '--reverse',)
    def __init__(self,
                 event_handler: ClientEventLoop,
                 request_identifier_on_client: int,
                 command: str,
                 error: str,
                 task_type: str,
                 is_batch_processing_mode: bool,
                 request_identifier_on_result: int,
                 data: str,
                 result: str):
        """
        :param event_handler: event loop class on server or client side
        :param request_identifier_on_client: registered identifier of request on client side
        :param command: request type
        :param error: error occurred when creating the request
        :param task_type: type of task: --symbol_repeat, --pair_permutation, --reverse
        :param is_batch_processing_mode: is activated or not
        :param request_identifier_on_result: registered identifier of response with result
        :param data: user input data for task
        :param result: identifier on the server side
        """
        super(Task, self).__init__(event_handler, request_identifier_on_client, command, error)
        self.task_type: str = task_type
        self.is_batch_processing_mode: bool = is_batch_processing_mode
        self.request_identifier_on_result: int = request_identifier_on_result
        self.data: str = data
        self.result: int = result


    def __str__(self) -> str:
        string = str(self.command) + ' ' + \
                 str(self.task_type) + ' ' + \
                 ('-b ' if self.is_batch_processing_mode else '') + \
                 str(self.data)
        return string

    def generate_result_request(self) -> ResultRequest:
        """create request for result on client side"""
        return ResultRequest(self.event_handler, self.request_identifier_on_result, 'result', None, None, None)

    @property
    def result(self) -> int:
        """identifier of task on server side"""
        return self._identifier
    @result.setter
    def result(self, value: int):
        """identifier of task on server side"""
        self._identifier: int = value

    def show_result(self) -> str:
        string = 'identifier: ' + str(self.result) if self.error is None else str(self.error)
        return string


    def dumps(self) -> bytes:
        return self.dump(
            [self.request_identifier_on_client, self.command, self.error, self.task_type,
             self.is_batch_processing_mode, self.request_identifier_on_result, self.data, self.result]
        )

    @classmethod
    def get_data_from_str(cls, event_handler, command: str, user_input: str) -> list:
        request_identifier_on_client: int = super().get_data_from_str(event_handler, command, user_input)
        request_identifier_on_result: int = None
        user_input_split: list = user_input.split()
        result = None
        error, data, task_type = None, None, None
        is_batch_processing_mode = False

        # seek for task type
        if len(user_input_split) < 2:
            raise TaskTypeNotFound(None)
        task_type = user_input_split[1]
        if task_type not in cls.task_types:
            raise TaskTypeNotFound(task_type)

        # seek for batch processing mode
        if len(user_input_split) >= 3:
            if user_input_split[2] == '-b':
                is_batch_processing_mode = True
                request_identifier_on_result: int = super().get_data_from_str(event_handler, command, user_input)

        # seek for data
        re_obj = re.search(f'^\s*{command}\s\s*{task_type}\s\s*(-b\s\s*|)', user_input)
        if re_obj is None:
            raise ValueError('ValueError. The data for task is not correct')
        else:
            data = user_input[re_obj.end():]
        return event_handler, request_identifier_on_client, command, error, \
               task_type, is_batch_processing_mode, request_identifier_on_result, data, result


commands = {'status': StatusRequest, 'result': ResultRequest,
            'help': InfoRequest, 'identifiers': InfoRequest,
            'task': Task}


def create_request(user_input: str, event_handler: ClientEventLoop) -> \
        Union[StatusRequest, ResultRequest, InfoRequest, Task]:
    """create request object according to the user input"""
    # try to find command for request type in user input
    split_data = user_input.split()
    if not split_data:  # if user input is empty
        raise CommandNotFound(None)
    command = split_data[0]
    if command not in commands.keys():  # if command is not exist
        raise CommandNotFound(command)

    request_class = commands[command]  # get class from commands
    init_data = request_class.get_data_from_str(event_handler, command, user_input)  # run user input parser
    request: Union[StatusRequest, ResultRequest, InfoRequest, Task] = request_class(*init_data)  # create request object
    return request
