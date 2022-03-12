class IdentifierNotFound(Exception):
    """
    Exception raised when there is no such task identifier.
    """
    def __init__(self, identifier):
        """*identifier* is the input identifier which caused the error"""
        if identifier is None:
            identifier = ''
        super().__init__(f'Identifier "{identifier}" not found. '
                         f'Please check list of identifiers (call "identifiers")')


class TaskTypeNotFound(Exception):
    """
    Exception raised when there is no such task type.
    """
    def __init__(self, task_type: str):
        """*task_type* is the input task type which caused the error"""
        if task_type is None:
            task_type = ''
        super().__init__(f'Task type "{task_type}" not found. '
                         f'Please check list of task types, call "task help"')


class CommandNotFound(Exception):
    """
    Exception raised when there is no such command.
    """
    def __init__(self, command: str):
        """*command* is the input command which caused the error"""
        if command is None:
            command = ''
        super().__init__(f'Command "{command}" not found. Call "help"')


class BatchProcessingModeCommandError(Exception):
    """
    Exception raised when there is no such command in batch processing mode.
    """
    def __init__(self, command: str):
        """*command* is the input command which caused the error"""
        if command is None:
            command = ''
        super().__init__(f'Command "{command}" not found. '
                         f'Only "status" and "result" commands are available in batch processing mode')

class BatchProcessingTaskIdentifierNotFound(Exception):
    """
    Exception raised when there is no batch processing task identifier.
    """
    def __init__(self):
        """*command* is the input command which caused the error"""
        super().__init__(f'Task identifier of batch processing mode not found.')
