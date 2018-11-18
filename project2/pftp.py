#!/usr/bin/env python3

import argparse, os, sys, socket, re, threading

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

class Session(object):
  def __init__(self, *args):
    self.file = args[0] or None
    self.hostname = args[1] or None
    self.port = args[2] or 21
    self.username = args[3] or 'anonymous'
    self.password = args[4] or 'user@localhost.localnet'

def myexit(errno):
  print(f'Exit {str(errno)}: - {exit_codes.get(errno, exit_codes.get(7))}')
  sys.exit(errno)

def check_code(result, expected):
  pass

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--version', help='name, version, author of the \
    application', action='store_true')
  parser.add_argument('-f', '--file', type=str, help='specifies the file to \
    download')
  parser.add_argument('-t', '--thread', type=str, help='specifies the \
    para-config-file for multi-thread downloads')
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

def request_handler(sock, request, logfn):
  sock.send(request.encode())
  print(f'C->S: {request}', end='')
  return None

def response_handler(sock, exp_code, logfn):
  response = sock.recv(255).decode()
  print(f'S->C: {response}', end='')
  check_code(int(response[:3]), exp_code)

  if int(response[:3]) == 227:
    data_port = re.findall(r'\d+', response)[-2:]
    data_port = int(data_port[0]) * 256 + int(data_port[1])
    return data_port

  if int(response[:3]) == 213:
    fsize = int(re.split(r'\s', response)[1])
    return fsize

  return None

def session_handler(sess, logfn, data, num_thrd=None, tid=None):
  # Control Process
  ctrl_sock = socket.socket()
  try:
    ctrl_sock.connect((sess.hostname, sess.port))
  except:
    myexit(1)

  # Connect -> USER -> PASS -> PASV
  response_handler(ctrl_sock, 220, None)
  request_handler(ctrl_sock, f'USER {sess.username}\r\n', None)
  response_handler(ctrl_sock, 331, None)
  request_handler(ctrl_sock, f'PASS {sess.password}\r\n', None)
  response_handler(ctrl_sock, 230, None)
  request_handler(ctrl_sock, f'PASV\r\n', None)
  data_port = response_handler(ctrl_sock, 227, None)

  # Data Process
  data_sock = socket.socket()
  try:
    data_sock.connect((sess.hostname, data_port))
  except:
    myexit(1)

  # SIZE
  if num_thrd:
    request_handler(ctrl_sock, f'SIZE {sess.file}\r\n', None)
    fsize = response_handler(ctrl_sock, 213, None)
    step = fsize // num_thrd
    startpos = tid * step
    endpos = (tid + 1) * step if tid != num_thrd - 1 else fsize
    step = endpos - startpos

  # Thread-only: REST -> TYPE I
    request_handler(ctrl_sock, f'REST {startpos}\r\n', None)
    response_handler(ctrl_sock, 350, None)
    request_handler(ctrl_sock, f'TYPE I\r\n', None)
    response_handler(ctrl_sock, 200, None)

  # RETR
  request_handler(ctrl_sock, f'RETR {sess.file}\r\n', None)
  response_handler(ctrl_sock, 150, None)

  # Normal Download
  # data is a single bytearray
  if not num_thrd:
    while True:
      chunk = data_sock.recv(1024)
      data.extend(chunk)
      if len(chunk) < 1:
        break

  # Thread-only: Parallel Download
  # data is a dict containing bytearrays corresponding to each thread
  else:
    count = 0
    temp = bytearray()
    while True:
      chunk = data_sock.recv(2048)
      temp.extend(chunk)
      count += len(chunk)
      if len(chunk) < 1 or count >= endpos:
        data[tid] = temp[:step]
        break

  ctrl_sock.close()

  return data

def main():
  args = parse_args()
  if args.thread and (args.file or args.hostname):
    myexit(4)

  # Thread
  if args.thread:
    sessions = []
    threads = []
    lines = open(args.thread, 'r').readlines()

    for line in lines:
      line = re.sub(f'ftp://', '', line.rstrip())
      configs = re.split(r'[:@/]', line)
      newsess = Session(configs[3], configs[2], args.port, configs[0], configs[1])
      sessions.append(newsess)

    datalist = {}
    for sess, tid in zip(sessions, range(len(sessions))):
      newthread = threading.Thread(target=session_handler, \
        args=(sess, args.log, datalist), \
        kwargs={'num_thrd': len(sessions), 'tid': tid})
      threads.append(newthread)

    for thread in threads:
      thread.start()

    for thread in threads:
      thread.join()

    with open(sess.file, 'wb') as fout:
      for data in datalist.values():
        fout.write(data)

  # Normal
  elif args.file and args.hostname:
    sess = Session(args.file, args.hostname, args.port, \
      args.username, args.password)
    data = session_handler(sess, args.log, bytearray())

    if data:
      with open(sess.file, 'wb') as fout:
        fout.write(data)

  myexit(0)

if __name__ == '__main__':
  main()