import signal
import sys

from core.server_core import ServerCore
from utils import get_host

my_p2p_server = None

def signal_handler(signal, frame):
    shutdown_server()

def shutdown_server():
    global my_p2p_server
    my_p2p_server.shutdown()


def main(my_port, c_host, c_port):
    signal.signal(signal.SIGINT, signal_handler)
    global my_p2p_server
    my_p2p_server = ServerCore(my_port, c_host, c_port) 
    my_p2p_server.start()
    my_p2p_server.join_network()


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--c_host',default=get_host())
    parser.add_argument('--c_port', default=5000,type=int)
    parser.add_argument('-p', '--port', default=5001,
                    type=int, help='port to listen on')

    args = parser.parse_args()
    c_host = args.c_host
    c_port = args.c_port
    port = args.port

    main(port, c_host, c_port)