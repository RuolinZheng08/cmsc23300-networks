#!/usr/bin/env python3

import argparse, socket, re, os, sys, threading, queue
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
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
            self.outlinks.add(val)

  def handle_comment(self, data):
    '''Retrieve data inside a comment and feed to another HTML parser'''
    innerparser = MyHTMLParser(self.hostname)
    innerparser.feed(data)
    self.outlinks.update(innerparser.outlinks)

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

def crawl_page(hostname, port, page):
  '''Fetch a single page and write to local'''
  print('Fetching page: {}...'.format(page))
  mysock = socket.socket()
  mysock.connect((hostname, port))
  mysock.sendall('GET /{} HTTP/1.1\r\nHost: {}\r\n\r\n'.format(page, \
    hostname).encode())
  data = bytearray()

  while True:
    chunk = mysock.recv(1024)
    data.extend(chunk)
    if len(chunk) < 1:
      break

  mysock.close()

  if page.endswith('/'):
    page = page[:-1]
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

def crawl_web(hostname, port, to_crawl, crawled):
  '''Recursively fetch all pages given a single-seeded queue'''
  while True:
    page = to_crawl.get()
    if page is None:
      break
    outlinks = crawl_page(hostname, port, page)
    crawled.append(page)
    if outlinks is not None:
      for link in outlinks:
        if not link in crawled and not link in to_crawl.queue:
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
  for i in range(args.numthreads):
    t = threading.Thread(target=crawl_web, \
      args=(args.hostname, args.port, to_crawl, crawled))
    threads.append(t)

  for t in threads:
    t.start()

  to_crawl.join()

  for i in range(args.numthreads):
    to_crawl.put(None)

  for t in threads:
    t.join()

if __name__ == '__main__':
  main()