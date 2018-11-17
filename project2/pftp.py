#!/usr/bin/env python3

import argparse, os, sys, socket, re

exit_codes = {
  0: 'Operation successfully completed\n',
  1: 'Can\'t connect to server\n',
  2: 'Authentication failed\n',
  3: 'File not found\n',
  4: 'Syntax error in client request\n',
  5: 'Command not implemented by server,\n',
  6: 'Operation not allowed by server\n',
  7: 'Generic error\n',
}

serv_resps = {
  500: 4,
  530: 2,
  550: 3,
}

class Session(object):
  def __init__(self, *args, **kwargs):
    self.file = kwargs.get('file')
    self.hostname = kwargs.get('hostname')
    self.port = 21 if kwargs.get('port') is None else kwargs.get('port')
    self.username = 'anonymous' if kwargs.get('username') is None \
    else kwargs.get('username')
    self.password = 'user@localhost.localnet' if kwargs.get('password') \
    is None else kwargs.get('password')

def myexit(errno):
  print('Exit Code: ' + str(errno) + ' - ' + \
    exit_codes.get(errno, exit_codes.get(7)))
  sys.exit(errno)

def check_code(response, expected):
  if not response == expected:
    myexit(serv_resps.get(response, 7))
  return

def print_log(fname, text):
  if fname == '-':
    print(text)
  else:
    with open(fname, 'w') as fout:
      fout.write(text)

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--version', help='name, version, author of the \
    application', action='store_true')
  parser.add_argument('-f', '--file', type=str, help='specifies the file to \
    download')
  parser.add_argument('-s', '--hostname', type=str, help='specifies the server \
    to download the file from')
  parser.add_argument('-p', '--port', type=int, help='specifies the port to be \
    used when contacting the server')
  parser.add_argument('-n', '--username', type=str, help='the username to log \
    into the FTP server')
  parser.add_argument('-P', '--password', type=str, help='the password to log \
    into the FTP server')
  parser.add_argument('-l', '--log', type=str, help='logs all the FTP commands \
    exchanged with the server and the corresponding replies')

  args = parser.parse_args()
  if args.version:
    print('pftp, Version: 0.1, Author: Ruolin Zheng')
    myexit(0)

  return args

def handle_session(sess):
  log_text = ''

  # Control Process
  ctrl_sock = socket.socket()
  try:
    ctrl_sock.connect((sess.hostname, sess.port))
  except:
    myexit(1)

  serv_code = int(ctrl_sock.recv(255).decode()[:3])
  check_code(serv_code, 220)
  ctrl_sock.send(f'USER {sess.username}\r\n'.encode())
  user_code = int(ctrl_sock.recv(255).decode()[:3])
  check_code(user_code, 331)
  ctrl_sock.send(f'PASS {sess.password}\r\n'.encode())
  pass_code = int(ctrl_sock.recv(255).decode()[:3])
  check_code(pass_code, 230)
  ctrl_sock.send(f'PASV\r\n'.encode())
  response = ctrl_sock.recv(255).decode()
  pasv_code = int(response[:3])
  check_code(pasv_code, 227)
  data_port = re.findall(r'\d+', response)[-2:]
  data_port = int(data_port[0]) * 256 + int(data_port[1])

  # Data Process
  data_sock = socket.socket()
  try:
    data_sock.connect((sess.hostname, data_port))
  except:
    myexit(1)
  ctrl_sock.send(f'LIST\r\n'.encode())
  print(data_sock.recv(255).decode())

  ctrl_sock.close()
  
  return log_text

def main():
  args = parse_args()
  if args.file and args.hostname:
    sess = Session(file=args.file, hostname=args.hostname, \
      port=args.port, username=args.username, password=args.password)

    log_text = handle_session(sess)

    if args.log:
      print_log(args.log, log_texts)
  
if __name__ == '__main__':
  main()