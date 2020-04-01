import socket as s
import threading
import time

PORT_OFFSET = 12000
RETRY_SECONDS = 2

IP_ADDRESS = '127.0.0.1'

timeout=False

# peers = []
# ID = 0
# server_port = PORT_OFFSET
# PING_INTERVAL = 30
# ping_socket = "Please run init_globals before using this"
# udp_socket  = "Please run init_globals before using this"
# tcp_socket  = "Please run init_globals before using this"
# t_lock      = "Please run init_globals before using this"
# peer_lock   = "Please run init_globals before using this"

def init_globals(_ID, _server_port, _peers, _ping_interval):
    global peers
    global ID
    global server_port
    global ping_interval
    global ping_socket
    global udp_socket
    global tcp_socket
    global t_lock
    global peer_lock
    global thread_list

    thread_list = []
    
    peers = _peers
    ping_interval = _ping_interval
    server_port = _server_port
    ID = _ID

    ping_socket = s.socket(s.AF_INET, s.SOCK_DGRAM)
    
    udp_socket = s.socket(s.AF_INET, s.SOCK_DGRAM)
    udp_socket.bind((IP_ADDRESS, server_port))

    tcp_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    tcp_socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
    tcp_socket.bind((IP_ADDRESS, server_port))
    tcp_socket.listen()

    t_lock=threading.Condition()
    peer_lock=threading.Condition()

    print("Globals initialised")

