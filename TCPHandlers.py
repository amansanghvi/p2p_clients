import socket as s
import threading
import datetime as dt
import time

from Helpers import Message, to_id, Peer, send_tcp_with_retrys
import Globals as g
from Globals import IP_ADDRESS

def init_tcp(serv_sock, _server_port):
    global tcp_socket 
    global server_port
    global run
    tcp_socket = serv_sock
    server_port = _server_port
    run = True

    tcp_server_thread=threading.Thread(name="TCPServer",target=run_tcp_server)
    tcp_server_thread.daemon=True
    tcp_server_thread.start()
    return tcp_server_thread

def run_tcp_server():
    global tcp_socket
    global run
    while run:
        try:
            conn, addr = tcp_socket.accept() 
        except ConnectionAbortedError as error:
            if (not run):
                print("Shutting TCP server down.")
                return
            else:
                raise error
        # lock acquired by client 
        # TODO: Acquire lock
        print('Connected to :', addr[0], ':', addr[1])

        # Start a new thread and return its identifier 
        tcp_thread=threading.Thread(name=addr, target=tcp_handler, args=(conn,addr))
        tcp_thread.daemon=True
        tcp_thread.start()
    
def tcp_handler(conn, addr):
    global run
    
    print('Server is ready for service')
    data = b""
    try:
        data = conn.recv(2048)
    except:
        return
    
    if not data:
        return
    message = Message.fromMessage(data)
    if (message.mType() == Message.JOIN):
        conn.close()
        target = message.data()
        p0, p1 = 0, 0
        with g.peer_lock:
            p0 = g.peers[0].port()
            p1 = g.peers[1].port()
            if (p0 == target or p1 == target):
                return
            socket = s.socket(s.AF_INET, s.SOCK_STREAM)
            if ((p0 < server_port and (target < p0 or target > server_port)) # If next in chain.
                    or (p0 > server_port and target < p0 and target > server_port)):
                if (send_tcp_with_retrys(target, Message(Message.MY_SUCC, [p0, p1]).content())):
                    g.peers = [Peer(target), g.peers[0]]
                else:
                    return
                print("Peer {} Join request received".format(to_id(target)))
                print("My first successor is Peer {}".format(to_id(target)))
                print("My second successor is Peer {}".format(to_id(p0)))
                send_tcp_with_retrys(p0, data)
            elif((p1 < p0 and (target < p1 or target > p0))
                    or (p1 > p0 and target < p1 and target > p0)):
                g.peers[1] = Peer(target)
                print("Successor Change request received")
                print("My new first successor is Peer {}".format(to_id(p0)))
                print("My new second successor is Peer {}".format(to_id(target)))
        print("Peer {} Join request forwarded to my successor".format(to_id(target)))
        send_tcp_with_retrys(p0, data)

        return 
    elif (message.mType() == Message.QUIT):
        socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        socket.connect((IP_ADDRESS, g.peers[0].port()))
        print("Recieved QUIT from {}".format(message.data()))
        if (message.data() == g.peers[0].port()):
            socket.sendall(Message(Message.BYE, server_port).content())
            peer_data = socket.recv(1024) # TODO: Add retrys
            socket.close()

            with g.peer_lock:
                peer_message = Message.fromMessage(peer_data)
                peers = peer_message.data()
                
                assert(peer_message.mType() == Message.MY_SUCC)    
                if (peers[0] == g.peers[1].port()):
                    g.peers = [g.peers[1], Peer(peers[1])]
                else:
                    g.peers = [Peer(peers[0]), Peer(peers[1])]
                g.peer_lock.notify()
            print("Said Goodbye")
            conn.close()
            return
        elif (message.data() == g.peers[1].port()):
            socket.sendall(Message(Message.YOUR_SUCC, server_port).content())
            peer_data = socket.recv(1024) # TODO: Add retrys
            socket.close()

            with g.peer_lock:
                peer_message = Message.fromMessage(peer_data)
                peers = peer_message.data()
                assert(peer_message.mType() == Message.MY_SUCC)
                g.peers[1] = Peer(peers[1])
                g.peer_lock.notify()

        conn.close()
        send_tcp_with_retrys(g.peers[0].port(), data)
        print("QUIT forwarded to successor")
        return
    elif (message.mType() == Message.YOUR_SUCC):
        conn.sendall(Message(Message.MY_SUCC, [g.peers[0].port(), g.peers[1].port()]).content())
    elif(message.mType() == Message.DIE):
        print("TCP recieved DIE. R.I.P")
        run = False

    conn.close()
    
