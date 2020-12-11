import signal
import sys

from core.server_core import ServerCore

my_p2p_server = None

def signal_handler(signal, frame):
    shutdown_server()

def shutdown_server():
    global my_p2p_server
    my_p2p_server.shutdown()


def main(my_port):
    signal.signal(signal.SIGINT, signal_handler)
    global my_p2p_server
    my_p2p_server = ServerCore(my_port, None, None) 
    my_p2p_server.start()


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000,
                    type=int, help='port to listen on')

    args = parser.parse_args()
    port = args.port
    
    main(port)