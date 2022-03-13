import os

from Server.ServerEventLoops import MainServer, UserEventLoop
from Server.Worker import worker

if __name__ == '__main__':
    os.system("title " + "Server Window")  # set windows title as "Server Window"
    server = MainServer(UserEventLoop)  # create server
    server.set_worker(worker)  # set worker in server
    server.run('0.0.0.0', 12345)  # start server
