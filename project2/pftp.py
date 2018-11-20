#!/usr/bin/env python3

import argparse, os, sys, socket, re, threading, time

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
  500: 5,
  530: 2,
  550: 3,
}

class Session(object):
  '''Contain the specified file, hostname, port, username, and password'''
  def __init__(self, *args):
    self.file = args[0] or None
    self.hostname = args[1] or None
    self.port = args[2] or 21
    self.username = args[3] or 'anonymous'
    self.password = args[4] or 'user@localhost.localnet'

def myexit(errno):
  '''Print error code and message to stderr and exit with error code'''
  print(f'Exit {str(errno)}: - {exit_codes.get(errno, exit_codes.get(7))}', \
    file=sys.stderr)
  sys.exit(errno)

def check_code(result, expected, extra=None):
  '''Check the response code from the FTP server; exit if mismatch'''
  # Temporary walkaround for '550 Permission Denied'
  if 'Permission Denied' in extra:
    myexit(6)
  if not result == expected:
    myexit(serv_resps.get(result, 7))
  return None

def parse_args():
  '''Handle command line arguments'''
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

  args = None
  try:
    args = parser.parse_args()
  except SystemExit as e:
    if e.code != 0:
      myexit(4)
  if not args:
    myexit(0)

  return args

def request_handler(sock, request, logfd):
  '''Encode, send and log a request sent from FTP client to server'''
  sock.send(request.encode())
  if logfd == '-':
    print(f'C->S: {request}', end='')
  elif logfd:
    logfd.write(f'C->S: {request}')
  return None

def response_handler(sock, exp_code, logfd):
  '''Decode, receive, check and log a response sent from FTP server to client'''
  response = sock.recv(255).decode()
  if logfd == '-':
    print(f'S->C: {response}', end='')
  elif logfd:
    logfd.write(f'S->C: {response}')

  # Temporary walkaround for port 22's strange ValueError 'SSH'
  try:
    check_code(int(response[:3]), exp_code, response)

    if int(response[:3]) == 227:
      data_port = re.findall(r'\d+', response)[-2:]
      data_port = int(data_port[0]) * 256 + int(data_port[1])
      return data_port

    if int(response[:3]) == 213:
      fsize = int(re.split(r'\s', response)[1])
      return fsize
  except ValueError:
    pass

  return None

def session_handler(sess, logfd, data, num_thrd=None, tid=None):
  '''
  Open the control and data process for a FTP transfer session;
  enable multithreaded session if specified
  '''
  # Control Process
  ctrl_sock = socket.socket()
  try:
    ctrl_sock.connect((sess.hostname, sess.port))
  except:
    myexit(1)

  # Connect -> USER -> PASS -> PASV
  response_handler(ctrl_sock, 220, logfd)
  request_handler(ctrl_sock, f'USER {sess.username}\r\n', logfd)
  response_handler(ctrl_sock, 331, logfd)
  request_handler(ctrl_sock, f'PASS {sess.password}\r\n', logfd)
  response_handler(ctrl_sock, 230, logfd)
  request_handler(ctrl_sock, f'PASV\r\n', logfd)
  data_port = response_handler(ctrl_sock, 227, logfd)

  # Data Process
  data_sock = socket.socket()
  try:
    data_sock.connect((sess.hostname, data_port))
  except:
    myexit(1)

  # SIZE
  request_handler(ctrl_sock, f'SIZE {sess.file}\r\n', logfd)
  fsize = response_handler(ctrl_sock, 213, logfd)

  # Thread-only
  if num_thrd:
    data['fsize'] = fsize
    step = fsize // num_thrd
    startpos = tid * step
    endpos = (tid + 1) * step if tid != num_thrd - 1 else fsize
    step = endpos - startpos

    # Thread-only: REST -> TYPE I
    request_handler(ctrl_sock, f'REST {startpos}\r\n', logfd)
    response_handler(ctrl_sock, 350, logfd)
    request_handler(ctrl_sock, f'TYPE I\r\n', logfd)
    response_handler(ctrl_sock, 200, logfd)

  # RETR
  request_handler(ctrl_sock, f'RETR {sess.file}\r\n', logfd)
  response_handler(ctrl_sock, 150, logfd)

  # Normal Download
  # data is a single bytearray
  if not num_thrd:
    try:
      while True:
        chunk = data_sock.recv(1024)
        data.extend(chunk)
        if len(chunk) < 1:
          break
    except:
      myexit(7)

  # Thread-only: Parallel Download
  # data is a dict containing a bytearray for each thread
  else:
    try:
      count = 0
      temp = bytearray()
      while True:
        chunk = data_sock.recv(2048)
        temp.extend(chunk)
        count += len(chunk)
        if len(chunk) < 1 or count >= endpos:
          if len(temp) < step:
            myexit(7)
          data[tid] = temp[:step]
          break
    except:
      myexit(7)

  response_handler(ctrl_sock, 226, logfd)
  request_handler(ctrl_sock, f'QUIT\r\n', logfd)
  response_handler(ctrl_sock, 221, logfd)

  # Clean up
  ctrl_sock.close()

  return data, fsize

################################################################################
def main():
  args = parse_args()

  # Syntax error
  if args.version:
    print('pftp, Version: 0.1, Author: Ruolin Zheng')
    myexit(0)
  if args.thread and (args.file or args.hostname):
    myexit(4)

  # Logging
  logfd = None
  if args.log:
    logfd = open(args.log, 'w') if args.log != '-' else '-'

  # Thread
  if args.thread:
    sessions, threads = [], []
    try:
      lines = open(args.thread, 'r').readlines()
    except:
      myexit(7)

    username, password, hostname, file = None, None, None, None
    for line in lines:
      line = re.sub(r'ftp://', '', line.rstrip())
      url = re.split(r'@', line)
      if len(url) == 2:
        username, password = re.split(r':', url[0])
        url = url[1]
      else:
        url = url[0]
      path = re.split(r'/', url)
      file = path[-1]
      hostname = '/'.join(path[:-1])

      newsess = Session(file, hostname, args.port, username, password)
      sessions.append(newsess)

    datalist = {}
    for sess, tid in zip(sessions, range(len(sessions))):
      newthread = threading.Thread(target=session_handler, \
        args=(sess, logfd, datalist), \
        kwargs={'num_thrd': len(sessions), 'tid': tid})
      newthread.daemon = True
      threads.append(newthread)

    for thread in threads:
      thread.start()
      time.sleep(0.2)

    for thread in threads:
      thread.join(timeout=5)

    # Obtain the file size
    fsize = datalist.pop('fsize', None)
    if len(datalist) != len(threads):
      myexit(7)
    if fsize != sum([len(chunk) for chunk in datalist.values()]):
      myexit(7)

    try:
      with open(sess.file, 'wb') as fout:
        for tid in sorted(datalist.keys()):
          fout.write(datalist[tid])
    except:
      myexit(7)

  # Normal
  elif args.file and args.hostname:
    args.hostname = re.sub(r'ftp://', '', args.hostname)
    sess = Session(args.file, args.hostname, args.port, \
      args.username, args.password)
    data, fsize = session_handler(sess, logfd, bytearray())

    if not data or len(data) != fsize:
      myexit(7)
    try:
      with open(sess.file, 'wb') as fout:
        fout.write(data)
    except:
      myexit(7)

  # Clean up
  if logfd and logfd != '-':
    logfd.close()

  myexit(0)

if __name__ == '__main__':
  main()