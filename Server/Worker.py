from __future__ import annotations
import time
from typing import List, Dict, Tuple, Any, TYPE_CHECKING, Union
from threading import Thread
from collections import deque
from threading import Semaphore




if TYPE_CHECKING:
    from src.ServerRequest import WorkerTask


class Worker:
    """"""
    def __init__(self):
        self.semaphore = Semaphore(1)
        self.current_identifier = 0
        self.tasks = dict()
        self.deque = deque()
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()

    def add_task(self, task: WorkerTask):
        self.semaphore.acquire()
        self.current_identifier += 1
        task.identifier = self.current_identifier
        task.status = 'in deque'
        self.tasks[self.current_identifier] = task
        self.deque.appendleft(self.current_identifier)
        self.semaphore.release()


    def run(self):
        while True:
            if len(self.deque) > 0:
                identifier = self.deque.pop()
                self.tasks[identifier].run()
            else:
                time.sleep(0.1)



