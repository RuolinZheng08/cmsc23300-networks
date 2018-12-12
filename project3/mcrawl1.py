#!/usr/bin/env python3

# Submission for Part I & II

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
  def __init__(self):
    HTMLParser.__init__(self)
    self.outlinks = set()

  def handle_starttag(self, tag, attrs):
    '''Retrieve all outlinks wrapped in <a href> tags from a HTML file'''
    tag = tag.lower()
    if tag in ['a', 'img', 'link', 'script']: 
      for key, val in attrs:
        key = key.lower()
        if key in ['href', 'src']:
          val = re.sub(r'^\.?/|https?://|#.*', '', val)
          if val != '' and not re.search(r'\.com|\.edu|\.org|\.gov', val):
            if val.endswith('/'):
              val = val + 'index.html'
            if val is not '':
              self.outlinks.add(val)

  def handle_comment(self, data):
    '''Retrieve data inside a comment and feed to another HTML parser'''
    innerparser = MyHTMLParser()
    innerparser.feed(data)
    self.outlinks.update(innerparser.outlinks)

def parse_args():
  '''
  Handle command line arguments
  ./mcrawl1.py -h eychtipi.cs.uchicago.edu -p 80 -f testdir -n 5
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

def crawl_page(hostname, port, lock, page):
  '''Fetch a single page and write to local''' 
  mysock = socket.socket()
  mysock.connect((hostname, port))

  worker = threading.get_ident()
  # print('Worker {} is fetching {}...'.format(worker, page))

  # Get cookie on first attempt or a fresh one after 402
  global cookie
  with lock:
    if not cookie:
      request = 'GET /{} HTTP/1.0\r\nHost: {}\r\n\r\n'.format(page, hostname)
    else:
      request = ''.join(['GET /{} HTTP/1.0\r\n',
    'Host: {}\r\n', 'Cookie:{} \r\n\r\n']).format(page, hostname, cookie)

    mysock.send(request.encode())
    
    # Check status code and cookie information in header
    header, content = mysock.recv(330).split(b'\r\n\r\n')
    header = header.decode()

    temp = re.findall(r'HTTP/\S+ (\d+)', header)
    if temp:
      status = int(temp[0])
      if status != 200:
        if status == 404:
          # print('Worker {} encounters 404 when fetching {}'.format(worker, page))
          return None
        elif status == 402:
          # print('Worker {} encounters 402 when fetching {}...'
          #   .format(worker, page))
          if cookie:
            cookie = None  # Reset cookie upon 402
          return -1
        elif status == 500:
          print('Internal Server Error')
          sys.exit(1)

    if not cookie:
      temp = re.findall(r'Set-Cookie: (.+?);', header)
      if temp:
        cookie = temp[0]
  
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
    htmlparser = MyHTMLParser()
    htmlparser.feed(data)
    return htmlparser.outlinks

def crawl_web(hostname, port, lock, to_crawl, crawled):
  '''Fetch all pages given a single-seeded queue'''
  while True:
    page = to_crawl.get()
    if page is None:
      break
    outlinks = crawl_page(hostname, port, lock, page)
    crawled.append(page)
    if outlinks is not None:
      if outlinks == -1:  # Status 402, put page back into queue
        time.sleep(1)
        crawled.pop()
        to_crawl.put(page)
      else:
        dirname = re.findall(r'^(.+/).*', page)
        for link in outlinks:
          if not link in crawled and not link in to_crawl.queue:
            if dirname and not re.search(r'\.\.', link):
              link = dirname[0] + link
            to_crawl.put(link)
    to_crawl.task_done()

def main():
  args = parse_args()
  
  if not os.path.exists(args.dirname):
    os.mkdir(args.dirname)
  os.chdir(args.dirname)
  
  to_crawl = queue.Queue()
  to_crawl.put('index.html')
  crawled = []
  threads = []
  global cookie
  cookie = None
  lock = threading.RLock()

  for i in range(args.numthreads):
    t = threading.Thread(target=crawl_web,
      args=(args.hostname, args.port, lock, to_crawl, crawled))
    t.daemon = True
    threads.append(t)

  for t in threads:
    t.start()

  to_crawl.join()

  for i in range(args.numthreads):
    to_crawl.put(None)

  for t in threads:
    t.join(timeout=15)

  print('Finished.')
  sys.exit(0)

if __name__ == '__main__':
  main()