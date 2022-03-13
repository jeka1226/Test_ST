import sys
import os
from subprocess import Popen, DEVNULL, call, PIPE

def set_window_title():
    if sys.platform == 'win32':
        os.system("title " + "Result Window")  # set windows title as "Result Window"
    else:
        pass


def start_subprocess():
    if sys.platform == 'win32':
        func: callable = lambda: Popen(['start', '/wait', 'python', 'ResultWindow.py'],
                                       shell=True, stderr=DEVNULL, stdout=DEVNULL)

    elif sys.platform == 'linux':
        func = null
    else:
        func = null
    return func

def stop_subprocess(pid):
    if sys.platform == 'win32':
        func: callable = lambda: call(['taskkill', '/F', '/T', '/PID', str(pid)], stderr=DEVNULL, stdout=DEVNULL)

    elif sys.platform == 'linux':
        func = null
    else:
        func = null
    return func

def null():
    pass