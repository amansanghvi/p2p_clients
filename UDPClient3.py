#Python 3
#Usage: python3 UDPClient3.py localhost 12000
#coding: utf-8
from socket import *
import sys
from Helpers import Message

#Server would be running on the same host as Client
if (len(sys.argv) < 3):
    raise ValueError("python3 {} [serverName] [serverPort]".format(sys.argv[0]))
serverName = sys.argv[1]
serverPort = int(sys.argv[2])


clientSocket = socket(AF_INET, SOCK_DGRAM)

message = input("Please type Subscribe\n")
clientSocket.sendto(message.encode(),(serverName, serverPort))
#wait for the reply from the server
receivedMessage, serverAddress = clientSocket.recvfrom(2048)

print(receivedMessage)
if (receivedMessage.decode()=='Subscription successfull'):
    #Wait for 10 back to back messages from server
    for i in range(10):
        receivedMessage, serverAddress = clientSocket.recvfrom(2048)
        print(receivedMessage.decode())

#prepare to exit. Send Unsubscribe message to server
# clientSocket.sendto(message.encode(),(serverName, serverPort))
# clientSocket.close()
# Close the socket
