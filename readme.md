# Assignment 1

Ensure you have files: `UDPHandlers.py`, `TCPHandlers.py`, 
`Globals.py`, `Helpers.py` and `Main.py` in the same directory

## Init
To initialise a p2p client, run the command:  
`python3 Main.py INIT <ID> <ID_SUCC_1> <ID_SUCC_2> <PING_INTERVAL>`  
Where ID is in the range [0, 255]. 
SUCC_1 and SUCC_2 should also be IDs of other p2p architectures.

## Join
To join a p2p client, run the command:  
`python3 Main.py JOIN <ID> <KNOWN_PEER_ID> <PING_INTERVAL>`  
Where ID is in the range [0, 255].

## Exiting
To exit, type `exit` or `quit` in the stdin of the client you want to close.

## Inserting
To insert a file, type `insert <FILE_NAME>` in the stdin of any client.

## Requesting
To request a file, type `get <FILE_NAME>` or `request <FILE_NAME>`
in the stdin of any client.


