import socket as s
import threading
import datetime as dt
import time

from Helpers import *
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
    if message.mType() == Message.JOIN:
        handle_join(conn, message, data)
    elif message.mType() == Message.QUIT:
        handle_quit(conn, message, data)
    elif message.mType() == Message.INSERT:
        handle_insert(conn, message, data)
    elif message.mType() == Message.GET:
        handle_get(conn, message, data)
    elif message.mType() == Message.POST:
        handle_post(conn, message, data)
    elif message.mType() == Message.YOUR_SUCC:
        conn.sendall(Message(Message.MY_SUCC, [g.peers[0].port(), g.peers[1].port()]).content())
    elif message.mType() == Message.DIE:
        print("TCP recieved DIE. R.I.P")
        run = False

    conn.close()

def handle_post(conn, message, data):
    file_name = get_file_name(message.data())
    print("Receiving File {} from Peer".format(file_name))
    f = create_file("_{}".format(file_name), False)
    while True:
        fdata = conn.recv(4096)
        if (not fdata):
            break
        f.write(fdata)
    f.close()

def handle_get(conn, message, data):
    conn.close()
    file_code, source = message.data()
    file_name = get_file_name(file_code)
    hashed_name = file_hash(file_name)
    socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    if file_name in g.table:
        message = Message(Message.POST, file_name)
        try:
            socket.connect((IP_ADDRESS, source))
            socket.sendall(message.content())
        except:
            print("Requester no longer exists")
            return
        f = get_file(file_name)
        while True:
            fdata = f.read(4096)
            socket.sendall(fdata.encode())
            if not fdata:
                break
        f.close()
        socket.close()
    elif hashed_name == g.ID:
        print("File {} not found.".format(file_name))
    else:
        dest = g.peers[0] if first_peer_owns_file(g.peers, hashed_name, g.ID) else g.peers[1]
        try:
            socket.connect((IP_ADDRESS, dest.port()))
            socket.sendall(data)
            socket.close()
        except:
            try:
                socket.connect((IP_ADDRESS, g.peers[0].port()))
                socket.sendall(data)
                socket.close()
            except:
                print("Unable to forward message")

def handle_insert(conn, message, data):
    conn.close()
    file_code, prev_id = message.data()
    file_name = get_file_name(file_code)
    hashed_name = file_hash(file_code)
    if (prev_id < g.ID and hashed_name > prev_id and hashed_name <= g.ID) \
        or (prev_id > g.ID and (hashed_name <= g.ID or hashed_name > prev_id)):
        print("Store {} request accepted".format(file_name))
        with g.table_lock:
            if file_name not in g.table:
                g.table[file_name] = True
                create_file(file_name)
    else:
        if (first_peer_owns_file(g.peers, hashed_name, g.ID)):
            message = Message(Message.INSERT, [file_name, g.ID])
            send_tcp_with_retrys(message.content(), g.peers[0].port())
            print("Store {} request forwarded to successor {}".format(file_name, g.peers[0].ID()))
        else:
            message = Message(Message.INSERT, [file_name, g.peers[0].ID()])
            send_tcp_with_retrys(message.content(), g.peers[1].port())
            print("Store {} request forwarded to successor {}".format(file_name, g.peers[1].ID()))


def handle_join(conn, message, data):
    conn.close()
    target = message.data()
    p0, p1 = 0, 0
    with g.peer_lock:
        p0 = g.peers[0].port()
        p1 = g.peers[1].port()
        if (p0 == target or p1 == target):
            return # Case should never happen (duplicate ID)
        if ((p0 < server_port and (target < p0 or target > server_port)) # If next in chain.
                or (p0 > server_port and target < p0 and target > server_port)):
            if (send_tcp_with_retrys(Message(Message.MY_SUCC, [p0, p1]).content(), target)):
                g.peers = [Peer(target), g.peers[0]]
            else:
                return
            print("Peer {} Join request received".format(to_id(target)))
            print("My first successor is Peer {}".format(to_id(target)))
            print("My second successor is Peer {}".format(to_id(p0)))
            send_tcp_with_retrys(data, p0)
            # TODO: Transfer some files if they belong to target
        elif((p1 < p0 and (target < p1 or target > p0))
                or (p1 > p0 and target < p1 and target > p0)):
            g.peers[1] = Peer(target)
            print("Successor Change request received")
            print("My new first successor is Peer {}".format(to_id(p0)))
            print("My new second successor is Peer {}".format(to_id(target)))
    print("Peer {} Join request forwarded to my successor".format(to_id(target)))
    send_tcp_with_retrys(data, p0)

def handle_quit(conn, message, data):
    socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    for i in range(0, 3):
        try:
            socket.connect((IP_ADDRESS, g.peers[0].port()))
            break
        except:
            print("Failed to connect to dying host")
            if i == 2:
                return
    
    print("Recieved QUIT from {}".format(message.data()))
    if (message.data() == g.peers[0].port()):
        for i in range(0,3):
            try:
                socket.sendall(Message(Message.BYE, server_port).content())
                peer_data = socket.recv(1024)
                socket.close()
                break
            except:
                pass
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
        peer_data = False
        for i in range(0, 3):
            try:
                socket.sendall(Message(Message.YOUR_SUCC, server_port).content())
                peer_data = socket.recv(1024) # TODO: Add retrys
                socket.close()
                break
            except:
                if i == 2:
                    return
        if (peer_data):
            with g.peer_lock:
                peer_message = Message.fromMessage(peer_data)
                peers = peer_message.data()
                assert(peer_message.mType() == Message.MY_SUCC)
                g.peers[1] = Peer(peers[1])
                g.peer_lock.notify()

    conn.close()
    send_tcp_with_retrys(data, g.peers[0].port())
    print("QUIT forwarded to successor")
    
