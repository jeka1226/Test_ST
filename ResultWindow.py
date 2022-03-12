import os
from Server.TCPServer import TCPServer
from Server.ServerEventLoops import ResultWindowEventLoop






if __name__ == '__main__':
    os.system("title " + "Result Window")
    server = TCPServer(ResultWindowEventLoop)
    server.run('0.0.0.0', 12346)
