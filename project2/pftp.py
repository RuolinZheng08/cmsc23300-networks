#!/usr/bin/env python3

import argparse, os, sys, socket, re

exit_codes = {
  0: 'Operation successfully completed',
  1: 'Can\'t connect to server',
  2: 'Authentication failed',
  3: 'File not found',
  4: 'Syntax error in client request',
  5: 'Command not implemented by server',
  6: 'Operation not allowed by server',
  7: 'Generic error',
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

def print_log(fname, log_list):
  if fname == '-':
    for log in log_list:
      print(log, end='')
  else:
    with open(fname, 'w') as fout:
      for log in log_list:
        fout.write(log)

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
  log_list = []
  response = None

  # Control Process
  ctrl_sock = socket.socket()
  try:
    ctrl_sock.connect((sess.hostname, sess.port))
  except:
    myexit(1)

  # Connect
  response = ctrl_sock.recv(255).decode()
  serv_code = int(response[:3])
  check_code(serv_code, 220)
  log_list.append(f'S->C: {response[:3]} Server {sess.hostname}\n')

  # USER
  request = f'USER {sess.username}\r\n'
  ctrl_sock.send(request.encode())
  log_list.append(f'C->S: {request}')

  response = ctrl_sock.recv(255).decode()
  log_list.append(f'S->C: {response}')
  user_code = int(response[:3])
  check_code(user_code, 331)

  # PASS
  request = f'PASS {sess.password}\r\n'
  ctrl_sock.send(request.encode())
  log_list.append(f'C->S: {request}')

  response = ctrl_sock.recv(255).decode()
  log_list.append(f'S->C: {response}')
  pass_code = int(response[:3])
  check_code(pass_code, 230)

  # PASV
  request = f'PASV\r\n'
  ctrl_sock.send(request.encode())
  log_list.append(f'C->S: {request}')

  response = ctrl_sock.recv(255).decode()
  log_list.append(f'S->C: {response}')
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
  
  ctrl_sock.send(f'SIZE {sess.file}\r\n'.encode())
  response = ctrl_sock.recv(255).decode()
  fsize = int(re.findall(r'\d+', response)[-1])

  # Transfer binary files
  request = f'RETR {sess.file}\r\n'
  ctrl_sock.send(request.encode())
  log_list.append(f'C->S: {request}')

  response = ctrl_sock.recv(255).decode()
  log_list.append(f'S->C: {response}')
  binf_code = int(response[:3])
  check_code(binf_code, 150)

  try:
    with open(sess.file, 'wb') as fout:
      while True:
        data = data_sock.recv(2048)
        if len(data) < 1:
          break
        fout.write(data)
  except:
    myexit(7)

  ctrl_sock.close()
  
  return log_list

def main():
  args = parse_args()
  if args.file and args.hostname:
    sess = Session(file=args.file, hostname=args.hostname, \
      port=args.port, username=args.username, password=args.password)

    log_list = handle_session(sess)

    if args.log:
      print_log(args.log, log_list)

    myexit(0)
  
if __name__ == '__main__':
  main()