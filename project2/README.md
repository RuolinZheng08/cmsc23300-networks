Ruolin Zheng
ruolinzheng
CMSC 233 Project 2 - FTP

Usage:
./pftp.py [-s hostname] [-f file] [options]
./pftp.py -h | --help
./pftp.py - v | --version
./pftp.py [-t para-config-file]

Options:
See project writeup.

Implementation:
In normal, single-threaded download, the program opens a control socket to 
initiate a file request from the FTP server in passive mode. It then opens a
data socket on a given port of the server based on the response it receives
after sending out PASV. The data socket receives the file and the file is then
saved to local. The control socket closes upon completion of this process.
In multi-threaded download, each thread initiates a download session of a
different portion of the file and perform the control and data socket options
as described above. Prior to making the file request, each client specifies to
the server the start position of the file with RECV. Upon receiving the portion
it is responsible for, the data socket stops reading and exits. The complete
file is saved to local by combining the portions from a dictionary containing
thread-portion mapping.
The program exits with 0 upon successful completion and exits with other error
code per the nature of the error.

Functions:
See pftp.py function comments.

Project Requirements:
- Basic FTP Operation
- Parallel FTP Download

Extra Credit:
This project attempts the extra credit for changing directory on the FTP server.
e.g. ./pftp.py -s ftp://mirror.keystealth.org/debian/ -f ls-lR.gz
