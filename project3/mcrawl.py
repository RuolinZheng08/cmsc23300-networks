#!/usr/bin/env python3

import argparse, socket, re, os, sys, shutil, threading
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
  def __init__(self, hostname):
    HTMLParser.__init__(self)
    self.hostname = hostname
    self.outlinks = set()

  def handle_starttag(self, tag, attrs):
    '''Retrieve all outlinks wrapped in <a href> tags from a HTML file'''
    tag = tag.lower()
    if tag == 'a' or tag == 'img': 
      for key, val in attrs:
        key = key.lower()
        if (tag == 'a' and key == 'href') or (tag == 'img' and key == 'src'):
          val = re.sub(r'\./|https?://|#', '', val)
          if val != '' and not re.search(r'\.com|\.edu|\.org|\.gov', val):
            self.outlinks.add(val)

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
  print('Fetching page: {}'.format(page))
  mysock = socket.socket()
  mysock.connect((hostname, port))
  mysock.sendall('GET /{}\r\n'.format(page).encode())
  data = bytearray()

  while True:
    chunk = mysock.recv(1024)
    data.extend(chunk)
    if len(chunk) < 1:
      break

  if page == '/':
    fname = 'index.html'
  else:
    if page.endswith('/'):
      page = page[:-1]
    fname = re.sub(r'/', '_', page)

  if re.search(r'\.png|\.jpg|\.gif|\.pdf', fname):
    with open(fname, 'wb') as f:
      f.write(data)
    return None
  else:
    data = data.decode()
    with open(fname, 'w') as f:
      f.write(data)
    htmlparser = MyHTMLParser(hostname)
    htmlparser.feed(data)
    return htmlparser.outlinks

def crawl_web(hostname, port, to_crawl):
  '''Recursively fetch all pages given a single-seeded queue'''
  crawled = []

  while to_crawl:
    page = to_crawl.pop()
    outlinks = crawl_page(hostname, port, page)
    crawled.append(page)
    if outlinks is not None:
      for link in outlinks:
        if not link in crawled:
          to_crawl.add(link)

def main():
  args = parse_args()
  
  if os.path.exists(args.dirname):
    shutil.rmtree(args.dirname)
  os.mkdir(args.dirname)
  os.chdir(args.dirname)

  crawl_web(args.hostname, args.port, set(['/']))

if __name__ == '__main__':
  main()