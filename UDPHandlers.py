import socket as s
import threading
import time

import Globals as g
from Helpers import Message, Peer, to_id
from Globals import RETRY_SECONDS, IP_ADDRESS

def init_udp(_udp_socket, _ping_socket, _server_port, _ping_interval):
    global udp_socket
    global ping_socket
    global SERVER_PORT
    global PING_INTERVAL

    udp_socket = _udp_socket
    ping_socket = _ping_socket

    SERVER_PORT = _server_port
    PING_INTERVAL = _ping_interval

    ping_thread=threading.Thread(name="PingEmitter",target=run_udp_server)
    ping_thread.daemon=True
    ping_thread.start()

    udp_server_thread=threading.Thread(name="UDPServer",target=ping_emitter)
    udp_server_thread.daemon=True
    udp_server_thread.start()
    return [udp_server_thread, ping_thread]

def run_udp_server():

    while True:
        data, addr = udp_socket.recvfrom(1024) # buffer size is 1024 bytes
        message = Message.fromMessage(data)

        if (message.mType() == Message.PING):
            socket = s.socket(s.AF_INET, s.SOCK_DGRAM)
            socket.sendto(Message(Message.PONG, SERVER_PORT).content(), (addr[0], message.data()))
            print("Ping request message received from Peer {}".format(to_id(message.data())))
            
        elif (message.mType() == Message.PONG):
            with g.peer_lock:
                for p in g.peers:
                    if p.port() == message.data():
                        p.connected()
                        break
                g.peer_lock.notify()
            print("Ping response received from Peer {}".format(to_id(message.data())))
        elif (message.mType() == Message.DIE):
            print("UDP recieved DIE. R.I.P")
            return
        # Start a new thread and return its identifier 
        # TODO: Change to ping handler
        # recv_thread=threading.Thread(name=addr, target=recv_handler, args=(data,addr))
        # recv_thread.daemon=True
        # recv_thread.start()


def ping_emitter():
    # go through the list of the subscribed peers and send them the current time after every 1 second
    while(1):
        #get lock
        with g.peer_lock:
            for p in g.peers:
                ping_socket.sendto(Message(Message.PING, SERVER_PORT).content(), (IP_ADDRESS, p.port()))
                p.send_ping()
                print('Ping request sent to Peer {}'.format(to_id(p.port())))
            # notify other thread
            g.peer_lock.notify()
        # sleep for PING_INTERVAL
        retry_thread = threading.Thread(name="RetryThread",target=retry_pings)
        retry_thread.daemon=True
        retry_thread.start()

        time.sleep(PING_INTERVAL)

def retry_pings():
    for _ in range(0, 4):
        time.sleep(RETRY_SECONDS)
        peers_to_connect = list(filter(lambda p: not p.response_recieved(), g.peers))

        if (len(peers_to_connect) == 0):
            return
        with g.peer_lock:
            for p in g.peers:
                if not p.response_recieved():
                    p.attempt_failed()
                    ping_socket.sendto(Message(Message.PING, SERVER_PORT).content(), (IP_ADDRESS, p.port()))
                else:
                    peers_to_connect = list(filter(lambda p: not p.response_recieved(), g.peers))
                    if len(peers_to_connect) == 0:
                        break
            g.peer_lock.notify()
        peers_to_connect = list(filter(lambda p: not p.response_recieved(), g.peers))
        if (len(peers_to_connect) == 0):
            return

        
        socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        if (g.peers[0].is_lost()):
            print("Peer {} is no longer alive".format(to_id(p.port())))
            socket.connect((IP_ADDRESS, g.peers[1].port()))
            socket.sendall(Message(Message.YOUR_SUCC, g.server_port).content())
            succs = Message.fromMessage(socket.recv(1024)).data()
            with g.peer_lock:
                g.peers = [g.peers[1], Peer(succs[0])]
            print("Successors updated.")
            print("My first successor is Peer {}".format(g.peers[0].ID()))
            print("My second successor is Peer {}".format(g.peers[1].ID()))
        elif(g.peers[1].is_lost()):
            print("Peer {} is no longer alive".format(to_id(p.port())))
            socket.connect((IP_ADDRESS, g.peers[0].port()))
            socket.sendall(Message(Message.YOUR_SUCC, g.server_port).content())
            succs = Message.fromMessage(socket.recv(1024)).data()
            with g.peer_lock:
                g.peers[1] = Peer(succs[0])
            print("Successors updated.")
            print("My first successor is Peer {}".format(g.peers[0].ID()))
            print("My second successor is Peer {}".format(g.peers[1].ID()))
        socket.close()