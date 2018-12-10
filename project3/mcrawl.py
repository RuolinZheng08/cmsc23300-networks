#!/usr/bin/env python3

import argparse
import socket
import re
import os
import sys
import threading
import queue
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
  ./mcrawl.py -h eychtipi.cs.uchicago.edu -p 80 -f testdir
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

  data = ''

  # Get cookie if the worker is not yet associated with a cookie
  if not worker in cookies:
    request = 'GET /{} HTTP/1.1\r\nHost: {}\r\n\r\n'.format(page, hostname)
  else:
    request = ''.join(['GET /{} HTTP/1.1\r\n',
  'Host: {}\r\n', 'Cookie:{} \r\n\r\n']).format(page, hostname, cookies[worker])

  mysock.send(request.encode())
  
  header, content = mysock.recv(330).decode().split('\r\n\r\n')
  cookie = re.findall(r'Set-Cookie: (.+?);', header)[0]
  if not cookie in cookies.values():
    cookies[worker] = cookie
  data += content

  while True:
    chunk = mysock.recv(1024).decode()
    data += chunk
    if len(chunk) < 1:
      break

  mysock.close()

  fname = re.sub(r'/', '_', page)

  if not re.search(r'\.html?', fname):
    with open(fname, 'wb') as f:
      f.write(data.encode())
    return None
  else:
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
        for link in outlinks:
          if not link in crawled:
            to_crawl.put(link)
      to_crawl.task_done()
    except:
      pass

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

  for t in threads:
    t.start()

  to_crawl.join()

  for i in range(args.numthreads):
    to_crawl.put(None)

  for t in threads:
    t.join()

  print(len(cookies))

if __name__ == '__main__':
  main()