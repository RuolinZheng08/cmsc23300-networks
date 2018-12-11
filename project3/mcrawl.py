#!/usr/bin/env python3

import argparse
import socket
import re
import os
import sys
import threading
import queue
import time
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
  '''A HTML parser that keeps track of outlinks including those in comments'''
  def __init__(self, hostname):
    HTMLParser.__init__(self)
    self.hostname = hostname
    self.outlinks = set()

  def handle_starttag(self, tag, attrs):
    '''Retrieve all outlinks wrapped in <a href> tags from a HTML file'''
    tag = tag.lower()
    if tag in ['a', 'img', 'link', 'script']: 
      for key, val in attrs:
        key = key.lower()
        if key in ['href', 'src']:
          val = re.sub(r'\./|https?://|#.*', '', val)
          if val != '' and not re.search(r'\.com|\.edu|\.org|\.gov', val):
            if val.endswith('/'):
              val = val[:-1]
            if val.startswith('.'):
              val = val[1:]
            if val == 'dynamics':
              val = 'dynamics.html'
            if val is not '':
              self.outlinks.add(val)

  def handle_comment(self, data):
    '''Retrieve data inside a comment and feed to another HTML parser'''
    innerparser = MyHTMLParser(self.hostname)
    innerparser.feed(data)
    self.outlinks.update(innerparser.outlinks)

class UniqueQueue(queue.Queue):
  '''A Queue that contains only unique items'''
  def _init(self, maxsize):
      self.queue = set()
  def _put(self, item):
      self.queue.add(item)
  def _get(self):
      return self.queue.pop()

def parse_args():
  '''
  Handle command line arguments
  ./mcrawl.py -h eychtipi.cs.uchicago.edu -p 80 -f testdir -n 5
  '''
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('-n', '--numthreads', type=int)
  parser.add_argument('-h', '--hostname', type=str)
  parser.add_argument('-p', '--port', type=int)
  parser.add_argument('-f', '--dirname', type=str)
  args = parser.parse_args()
  if not args.hostname or not args.port or not args.dirname:
    print('Error: Missing required arguments.', file=sys.stderr)
    sys.exit(1)
  if not args.numthreads:
    args.numthreads = 1
  return args

def crawl_page(hostname, port, cookies, page):
  '''Fetch a single page and write to local''' 
  mysock = socket.socket()
  mysock.connect((hostname, port))

  worker = threading.get_ident()
  print('Worker {} is fetching {}...'.format(worker, page))

  # Get cookie if the worker is not yet associated with a cookie
  if not worker in cookies:
    request = 'GET /{} HTTP/1.0\r\nHost: {}\r\n\r\n'.format(page, hostname)
  else:
    request = ''.join(['GET /{} HTTP/1.0\r\n',
  'Host: {}\r\n', 'Cookie:{} \r\n\r\n']).format(page, hostname, cookies[worker])

  mysock.send(request.encode())
  
  header, content = mysock.recv(330).split(b'\r\n\r\n')
  header = header.decode()
  status = int(re.findall(r'HTTP/\S+ (\d+)', header)[0])
  cookie = re.findall(r'Set-Cookie: (.+?);', header)[0]
  if not cookie in cookies.values():
    cookies[worker] = cookie
  if status != 200:
    if status == 404:
      return None
    elif status == 402:
      print('Worker {} encounters 402 when fetching {}...'.format(worker, page))
      return -1

  data = bytearray()
  data.extend(content)

  while True:
    chunk = mysock.recv(1024)
    data.extend(chunk)
    if len(chunk) < 1:
      break

  mysock.close()

  print('Worker {} has fetched {}...'.format(worker, page))

  fname = re.sub(r'/', '_', page)

  if not re.search(r'\.html?', fname):
    with open(fname, 'wb') as f:
      f.write(data)
    return None
  else:
    data = data.decode()
    with open(fname, 'wt') as f:
      f.write(data)
    htmlparser = MyHTMLParser(hostname)
    htmlparser.feed(data)
    return htmlparser.outlinks

def crawl_web(hostname, port, cookies, to_crawl, crawled):
  '''Fetch all pages given a single-seeded queue'''
  while True:
    try:
      page = to_crawl.get()
      if page is None:
        break
      outlinks = crawl_page(hostname, port, cookies, page)
      crawled.append(page)
      if outlinks is not None:
        if outlinks == -1:  # Status 402, put page back into queue
          crawled.pop()
          time.sleep(5)
          to_crawl.put(page)
          continue
        else:
          for link in outlinks:
            if not link in crawled:
              to_crawl.put(link)
      to_crawl.task_done()
    except:
      print(sys.exc_info(), file=sys.stderr)

def main():
  args = parse_args()
  
  if not os.path.exists(args.dirname):
    os.mkdir(args.dirname)
  os.chdir(args.dirname)
  
  to_crawl = UniqueQueue()
  to_crawl.put('index.html')
  crawled = []
  threads = []
  cookies = {}
  for i in range(args.numthreads):
    t = threading.Thread(target=crawl_web,
      args=(args.hostname, args.port, cookies, to_crawl, crawled))
    threads.append(t)
    t.daemon = True

  for t in threads:
    t.start()

  to_crawl.join()

  for i in range(args.numthreads):
    to_crawl.put(None)

  for t in threads:
    t.join(timeout=300)

  print(len(cookies))

if __name__ == '__main__':
  main()