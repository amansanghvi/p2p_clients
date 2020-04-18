import datetime as dt
from Globals import PORT_OFFSET, IP_ADDRESS
import socket as s

class Message:
    UNSUBSCRIBE = "UNSUBSCRIBE"
    SUBSCRIBE = "SUBSCRIBE"
    INSERT = "INSERT {} {}" # File name and predecessor ID
    GET = "GET {} {}" # File name and requester port.
    POST = "POST {}" # File name.
    CONNECT = "CONNECT"
    PING = "PING {}" # Source port
    PONG = "PONG {}" # Source port
    JOIN = "JOIN {}" # Joiner's port
    YOUR_SUCC = "YOUR_SUCC {}" # Target's successor port
    MY_SUCC = "MY_SUCC {} {}" # Source's successors ports
    QUIT = "QUIT {}" # Source's port
    BYE = "BYE {}" # Source's port
    DIE = "DIE"
    UNKNOWN = "UNKNOWN"

    def __init__(self, messageType, data=[], isRequest=True):
        self._messages = list(filter(lambda x: isinstance(x, str), Message.__dict__.values()))
        self._messageType = self.resolveType(messageType)
        self._data = data

    def resolveType(self, messageType):
        messageType = messageType.upper()
        if messageType not in self._messages:
            return self.UNKNOWN
        return messageType
    
    @staticmethod
    def fromMessage(encodedMessage):
        message = encodedMessage.decode().upper().split()
        print(message)
        messageType = message[0] + (" {}"*(len(message)-1))
        if (len(message) > 2):
            return Message(messageType, [int(i) for i in message[1:]])
        elif(len(message) == 2):
            return Message(messageType, int(message[1]))
        else:
            return Message(messageType)
            
    def mType(self):
        return self._messageType

    def data(self):
        return self._data

    def content(self):
        if self._messageType == self.UNKNOWN or self._messageType == self.DIE:
            return self._messageType.encode()
        elif isinstance(self._data,list):
            return self._messageType.format(self._data[0], self._data[1]).encode()
        else:
            return self._messageType.format(self._data).encode()

class Peer:
    _CONNECT_ATTEMPTS = 4
    _port = 12000
    _attempts_remaining = _CONNECT_ATTEMPTS
    _status = 1

    def __init__(self, port):
        self._port = port
        self._attempts_remaining = self._CONNECT_ATTEMPTS
        self._status = 1
    
    def attempt_failed(self):
        self._attempts_remaining -= 1

    def is_lost(self):
        return self._attempts_remaining <= 0
    
    def connected(self):
        self._attempts_remaining = self._CONNECT_ATTEMPTS
        self._status = 1

    def port(self):
        return self._port

    def ID(self):
        return to_id(self._port)
    
    def send_ping(self):
        self._status = -1
    
    def response_recieved(self):
        return self._status > 0

def file_hash(f):
    return int(f) % 256

def is_valid_file_name(name):
    return len(name) == 4 and name.isdigit()

def to_id(port):
    return port - PORT_OFFSET

def to_port(id):
    return id + PORT_OFFSET

def send_tcp_with_retrys(data, port):
    for _ in range(0, 2):
        try:
            socket = s.socket(s.AF_INET, s.SOCK_STREAM)
            socket.connect((IP_ADDRESS, port))
            socket.sendall(data)
            socket.close()
            print("Sent message: {} to port {}".format(data,port))
            return True
        except:
            pass
    print("Unable to send content to {}".format(port))
    return False

def get_file_name(file_code):
    return "{:04d}".format(file_code)

def get_file(file_name):
    f = open(file_name+".pdf", "r")
    return f

def create_file(file_name, close=True):
    f = open(file_name+".pdf", "w+") # Create file if not exists
    if (close):
        f.close()
    return f

def first_peer_owns_file(peers, hashed_name, ID):
    return (peers[0].ID() >= ID and hashed_name <= peers[0].ID() and hashed_name > ID) \
            or (peers[0].ID() <= ID and (hashed_name > ID or hashed_name <= peers[0].ID()))
