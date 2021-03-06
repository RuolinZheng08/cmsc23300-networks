Ruolin Zheng
ruolinzheng
CMSC 233 Project 1 - netcat

To Compile:
`make`

Usage:
./snc [-l] [-u] [hostname] port

Implementation:
According to the flags given, the program will act either as a server or
a client, either in TCP mode or in UDP mode.
In TCP mode, the server listens for and accepts incoming requests (with address
specified or any address), then reads and prints to stdout any message sent 
from the connected client. The client connects to the server, reads from stdin
and sends the message to the server. Data is transferred in a continuous stream
in such a case. Upon pressing CTRL+D in either side to close the connection, 
the opposite side automatically exits.
In UDP mode, the server reads input from a specified socket (of specified 
address or any address), then prints to stdout the message. The client sends
messages in a chunk to the specified server, and exits when CTRL+D is pressed.
This, however, does not affect the server, which could continue to read and
output message if other UDP client connects.

Handling CTRL+D in TCP:
In client, when CTRL+D is pressed and stdin is empty, the client exits 
immediately and simultaneously shuts down the server. Does not handle the case
in which stdin is non-empty.

Functions:
See snc.c function comments.

Project Requirements / Error Handling:
- Given invalid options: print input error help message and exit
- Missing required options: print input error help message and exit
- Given illegal args like port 111111 and IP 897.233:
  print input error help message and exit
- (Server) Designated port used by another application: 'internal error'
- (Client) Could not connect to designated server: 'internal error'

Issues Encountered:
CTRL+D implementation in TCP client.
Forking another process to allow for simultaneous read and write.

Sample execution:
Terminal window 1                   Terminal window 2
`./snc -l 9999`                     `./snc localhost 9999`
                                    type 'hello'
prints 'hello' on stdout
                                    press CTRL+D
simultaneously exits                exits
