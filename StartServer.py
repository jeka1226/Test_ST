import os
from Server.Worker import Worker
from Server.ServerEventLoops import MainServer, UserEventLoop






if __name__ == '__main__':
    os.system("title " + "Server Window")
    worker = Worker()
    server = MainServer(UserEventLoop)
    server.worker = worker
    server.run('0.0.0.0', 12345)
