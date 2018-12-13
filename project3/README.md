Ruolin Zheng
ruolinzheng
CMSC 233 Project 3 - HTTP Crawler

Usage:
./mcrawl1.py [ -n max-flows ] [ -h hostname ] [ -p port ] [-f localdirectory]
./mcrawl2.py [ -n max-flows ] [ -h hostname ] [ -p port ] [-f localdirectory]

Note:
The program runs fastest in Python 3.7. Timeout problems may occur if too many threads are spawn, so the ideal value for max-flow should be 4 - 6. When ran on eychtipi.cs.uchicago.edu, 88 files are expected to be retrieved.

Implementation:
Part I & II
One thread retrieves a cookie and its peer threads share the cookie when sending request to the server. Cookie retrieval is protected by an RLock and is reset upon a 402 response from the server. The program crawls all <href> and <src> tag found in a seed HTML file and repeats the process for all internal links crawled, stopping at outgoing links. It prints to stdout as it downloads the files.

Part III
Each thread retrieves a unique cookie and identify itself to the server with that cookie before receiving a 402 response. All cookies are stored in a worker-cookie dictionary and a particular cookie is reset upon 402. As in above, the program crawls all <href> and <src> tag found in a seed HTML file and repeats the process for all internal links crawled, stopping at outgoing links. Printing to stdout is disabled for the sake of speed.

Functions:
See function docstring comments.

Project Requirements:
- Part I & II Multi-thread identified by the same cookie
- Part III Multi-thread each identified by a distinct cookie

Competition:
See competition.txt.
