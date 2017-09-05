#!/usr/bin/python2

CONNECTION_TIMEOUT = 15
INACTIVE_TIMEOUT = 120
PORT = 22022

try:
    import re
    import SocketServer
    import urllib
    import sys
    import json
    from sys import argv
    import functools
except:
    print '! missing some crucial system modules !'


class Mini(SocketServer.StreamRequestHandler):
    def sendLine(self, line):
        self.wfile.write(line + "\r\n")

    def handle(self):
        print '! handle request. initiate dialogue.'
        self.sendLine('INTEGRATE v0.4')        
        self.saved = {}
        
        while 1:
            data = self.rfile.readline().strip()
            if not data:
                server.shutdown
                return
            print 'DATA: %s' % data

print '! starting automation on port %d, timeout in %d secs' % (PORT, CONNECTION_TIMEOUT)
server = SocketServer.TCPServer(('localhost', PORT), Mini)
server.timeout = CONNECTION_TIMEOUT
server.handle_request()

print '! done work'