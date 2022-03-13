import os

from Server.ServerEventLoops import ResultWindowEventLoop
from Server.TCPServer import TCPServer


if __name__ == '__main__':
    os.system("title " + "Result Window")  # set windows title as "Result Window"
    server = TCPServer(ResultWindowEventLoop)  # create server
    server.safe_print("This is RESULT WINDOW. All results will shown here.")
    server.run('0.0.0.0', 12346)   # start server
