#!/usr/bin/env python3

import argparse, socket, re, os, sys, shutil, threading
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
  '''Retrieve all outlinks wrapped in <a href> tags from a HTML file'''
  def __init__(self, hostname):
    HTMLParser.__init__(self)
    self.hostname = hostname
    self.outlinks = []
  def handle_starttag(self, tag, attrs):
    if tag.lower() == 'a':
      for key, val in attrs:
        if key == 'href':
          val = re.sub(r'\./|https?://|#', '', val)
          if val != '' and not re.search(r'\.com|\.edu|\.org', val):
            self.outlinks.append(val)

def parse_args():
  '''
  Handle command line arguments
  ./mcrawl -h http://eychtipi.cs.uchicago.edu -p 80 -f testdir
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
  '''Fetch a single page'''
  print('Fetching page: {}'.format(page))
  mysock = socket.socket()
  mysock.connect((hostname, port))
  mysock.sendall('GET /{}\r\n'.format(page).encode())
  data = ''

  while True:
    chunk = mysock.recv(1024).decode()
    data += chunk
    if len(chunk) < 1:
      break

  fname = re.sub('/', '_', page)
  with open(fname, 'w') as f:
    f.write(data)

  htmlparser = MyHTMLParser(hostname)
  htmlparser.feed(data)
  return htmlparser.outlinks

def crawl_web(hostname, port, seed):
  '''Recursively fetch all pages from a given seed'''
  to_crawl = [seed]
  crawled = []

  while to_crawl:
    page = to_crawl.pop()
    outlinks = crawl_page(hostname, port, page)
    for link in outlinks:
      if not link in crawled:
        to_crawl.append(link)
    crawled.append(page)

def main():
  args = parse_args()
  
  if os.path.exists(args.dirname):
    shutil.rmtree(args.dirname)
  os.mkdir(args.dirname)
  os.chdir(args.dirname)

  crawl_web(args.hostname, args.port, 'index.html')

if __name__ == '__main__':
  main()