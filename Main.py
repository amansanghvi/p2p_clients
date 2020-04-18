# Sample code for Multi-Threaded Server
#Python 3
# Usage: python3 UDPserver3.py
#coding: utf-8
import socket as s
import threading
import time
import datetime as dt
import sys

from Helpers import *
import Globals as g
from Globals import IP_ADDRESS
from UDPHandlers import init_udp
from TCPHandlers import init_tcp

# ClientID will be port#. TCP port
# Each ServerClient will have a list of 'peers'
# Each ServerClient will have 1 listening thread and 1 polling thread.
# On TCP connection, another thread will spawn to collect all the data.
# One thread will listen to the incoming port, the other will send pings/info

#Server will run on this port + id

def print_usage(use):
    print("Invalid Usage: ", use)
    print("Valid commands:\ninsert|store [filename]\nexit|quit")

def init_network(id, succ_1, succ_2, ping_interval):

    peers = [Peer(to_port(succ_1)), Peer(to_port(succ_2))]
    
    g.init_globals(id, to_port(id), peers, ping_interval)
    g.thread_list += init_udp(g.udp_socket, g.ping_socket, g.server_port, g.ping_interval)
    g.thread_list.append(init_tcp(g.tcp_socket, to_port(id)))

def join_network(id, contact, ping_interval): # TODO: THIS FUNCTION

    server_port = to_port(id)
    g.init_globals(id, server_port, [], ping_interval)  
    
    socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    socket.connect((IP_ADDRESS, to_port(contact)))
    socket.sendall(Message(Message.JOIN, server_port).content())
    
    conn, _ = g.tcp_socket.accept()
    raw_data, _ = conn.recvfrom(2048)
    next_peers = Message.fromMessage(raw_data).data()

    conn.close()
    print("Join request has been accepted")
    print("My first successor is Peer {}".format(to_id(next_peers[0])))
    print("My second successor is Peer {}".format(to_id(next_peers[1])))
    g.peers = [Peer(next_peers[0]), Peer(next_peers[1])]

    init_tcp(g.tcp_socket, server_port)
    init_udp(g.udp_socket, g.ping_socket, server_port, g.ping_interval)

if __name__ == "__main__":
    
    if (len(sys.argv) < 2):
        raise ValueError("Usage: python {} [TYPE] [...ARGS]", sys.argv[0])

    if (sys.argv[1].upper() == "INIT"):
        if (len(sys.argv) != 6):
            raise ValueError("Usage: python {} INIT ID SUCC1 SUCC2 PING_INT", sys.argv[0])
        init_network(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
    elif (sys.argv[1].upper() == "JOIN"):
        if (len(sys.argv) != 5):
            raise ValueError("Usage: python {} JOIN ID PEER PING_INT", sys.argv[0])
        join_network(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    else:
        raise ValueError("Invalid TYPE, please use INIT or JOIN")
    
    #this is the main thread
    while True:
        cmd = input().lower().split(" ")
        if (cmd[0] == "quit" or cmd[0] == "exit"):
            # TODO: Stop threads here.
            killer_message = Message(Message.DIE).content()
            tcp_killer = s.socket(s.AF_INET, s.SOCK_STREAM)
            tcp_killer.connect((IP_ADDRESS, g.server_port))
            tcp_killer.sendall(killer_message)

            udp_killer = s.socket(s.AF_INET, s.SOCK_DGRAM)
            for i in range(0, 5):
                udp_killer.sendto(killer_message, (IP_ADDRESS, g.server_port))
                time.sleep(0.01)
            g.tcp_socket.close()
            g.udp_socket.close()
            # TODO: Transfer files forward.
            with g.peer_lock:
                if g.peers[0].port() == g.server_port:
                    sys.exit()
                listener = s.socket(s.AF_INET, s.SOCK_STREAM)
                listener.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
                listener.bind((IP_ADDRESS, g.server_port))
                listener.listen()
                sender = s.socket(s.AF_INET, s.SOCK_STREAM) 
                print(g.peers[0].port())
                sender.connect((IP_ADDRESS, g.peers[0].port()))

                sender.sendall(Message(Message.QUIT, g.server_port).content())
                while True:
                    conn, _ = listener.accept()
                    data = Message.fromMessage(conn.recv(1024))

                    if (data.mType() == Message.YOUR_SUCC):
                        conn.sendall(Message(Message.MY_SUCC, [g.peers[0].port(), g.peers[1].port()]).content())
                    if (data.mType() == Message.BYE):
                        conn.sendall(Message(Message.MY_SUCC, [g.peers[0].port(), g.peers[1].port()]).content())
                        conn.close()
                        sys.exit(0)
                    conn.close()
        elif(cmd[0] == "store" or cmd[0] == "insert"):
            if (len(cmd) < 2 or not is_valid_file_name(cmd[1])):
                print_usage(cmd)
            else:
                file_name = cmd[1]
                hashed_name = file_hash(file_name)
                print("{} with hash {}".format(file_name, hashed_name))
                if (to_id(g.server_port) == hashed_name):
                    with g.table_lock:
                        if (file_name not in g.table):
                            g.table[file_name] = True # it is stored
                        else:
                            print("File {} being replaced".format(file_name))
                        g.table_lock.notify()
                    print("Store {} request accepted".format(file_name))
                else:
                    if first_peer_owns_file(g.peers, hashed_name, g.ID):
                        message = Message(Message.INSERT, [file_name, g.ID])
                        send_tcp_with_retrys(message.content(), g.peers[0].port())
                        print("Store {} request forwarded to successor {}".format(file_name, g.peers[0].ID()))
                    else:
                        message = Message(Message.INSERT, [file_name, g.peers[0].ID()])
                        send_tcp_with_retrys(message.content(), g.peers[1].port())
                        print("Store {} request forwarded to successor {}".format(file_name, g.peers[1].ID()))   
        elif(cmd[0] == "request" or cmd[0] == "get"):
            if (len(cmd) < 2 or not is_valid_file_name(cmd[1])):
                print_usage(cmd)
            else:
                file_name = cmd[1]
                if file_name in g.table:
                    print("File {} is stored here.".format(file_name))
                    f0 = get_file(file_name)
                    f1 = create_file("_" + file_name, False)
                    while True:
                        data = f0.read(4096)
                        if not data:
                            break
                        f1.write(data)
                    f0.close()
                    f1.close()
                else:
                    hashed_name = file_hash(file_name)
                    if to_id(g.server_port) == hashed_name:
                        print("File {} not found.".format(file_name))
                    else:
                        message = Message(Message.GET, [file_name, g.server_port])
                        dest = g.peers[0] if first_peer_owns_file(g.peers, hashed_name, g.ID) else g.peers[1]
                        send_tcp_with_retrys(message.content(), dest.port())
                        print("File request for {} forwarded to {}".format(file_name, dest.ID()))
        else:
            print_usage(cmd)
            

    

