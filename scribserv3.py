#!/usr/bin/python2

CONNECTION_TIMEOUT = 15
INACTIVE_TIMEOUT = 120
DEFAULT_PORT = 22022
LOGFILE = 'scribserv.log'

try:
    import logging
    import re
    import SocketServer
    import urllib
    import sys
    import json
    from sys import argv
    import functools
except:
    print '! missing some crucial system modules !'

try:
    import scribus
    from scribus import PDFfile, haveDoc
except:
    print '! yo runnin standalone, baba!'

# ----------------------------------------------------------------------------

logger = logging.getLogger('automator')
hdlr = logging.FileHandler(LOGFILE)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

# ----------------------------------------------------------------------------

def exportPDF(opath='VR_EXPORT.pdf'):
    pdf = PDFfile()
    pdf.compress = 0
    pdf.bleedr = 2
    pdf.file = opath
    pdf.embedPDF = True
    pdf.save()

class Automator3(SocketServer.StreamRequestHandler):
    def sendLine(self, line):
        self.wfile.write(line + "\r\n")

    def handle(self):
        logger.info('! handle request. initiate dialogue.')
        logger.info('INTEGRATE v0.5')
        self.saved = dict()

        while 1:
            data = self.rfile.readline().strip()
            if not data:
                self.shutdown()
                return

            self.lineReceived(data)

    # def __init__(self, socket, client, tcpserv):
    #     self.socket = socket
    #     socket.settimeout(INACTIVE_TIMEOUT)
        
    #     # self.accb = reactor.callLater(INACTIVE_TIMEOUT, 
    #     #     functools.partial(
    #     #         Automator3.autoclose, 
    #     #         self))

    def shutdown(self):
        """Close connection and app. 
        
        Typically in case of inactivity.

        """

        logger.warn('! shutdown system.')

        try:
            import PyQt4.QtGui as gui

            logger.warn('! shutdown server')
            self.connection.close()

            logger.warn('! shutdown app')
            app = gui.QApplication.instance()
            app.exit(0)
        except:
            logger.warn(r'could not import PyQt4.QtGui. just close all')
            self.connection.close()

    def backup(self):
        if not 'scribus' in globals():
            return

        page = 1
        pagenum = scribus.pageCount()
        print '! backup template values from %d pages' % pagenum
        
        while page <= pagenum:
            scribus.gotoPage(page)
            pitems = scribus.getPageItems()
            for item in pitems:
                if item[1] == 4:
                    buf = scribus.getAllText(item[0])
                    self.saved[item[0]] = buf
            page += 1

    def restore(self):
        if not 'scribus' in globals():
            return

        page = 1
        pagenum = scribus.pageCount()
        logger.info('! restore values into %d pages' % pagenum)

        while page <= pagenum:
            scribus.gotoPage(page)
            pitems = scribus.getPageItems()
            for item in pitems:
                if item[1] == 4:
                    if self.saved.get(item[0]) != None:
                       scribus.setText(self.saved[item[0]], item[0])
            page += 1

        logger.info('! done restore')


    @staticmethod
    def CONVERT(arg):
        logger.info('..decode params.')
        marg = re.search(r'(.*?):(.*)', arg)
        if marg:
            [opath, xlatenc] = [marg.group(1), marg.group(2)]
        else:
            logger.error('ERR_BAD_ARG: %s' % arg)
            return 'ERR_BAD_ARG: %s' % arg

        logger.info('..opath: %s' % opath)
        jsxlat = urllib.unquote(urllib.unquote(xlatenc))
        logger.info('..json: %s' % jsxlat)

        try:
            xlat = json.loads(jsxlat)
            logger.info('..xlat: %s' % xlat)
        except:
            logger.error('..error decoding json: %s' % sys.exc_info()[1].message)

        # -----------------------------------------------------------

        logger.info(r'! process template')
        page = 1
        pagenum = scribus.pageCount()
        while page <= pagenum:
            logger.info(r'.process page ' + str(page))
            scribus.gotoPage(page)
            pitems = scribus.getPageItems()
            for item in pitems:
                if item[1] == 4:
                    logger.info(r'..process text ' + str(item))
                    buf = scribus.getAllText(item[0])
                    logger.info(r'...cur text: ' + str(buf))

                    mbuf = re.search(r'[{]+(\w+)[}]+', buf)
                    v = mbuf.group(1)
                    if v and xlat[v]:
                        nstr = xlat[v]
                    else:
                        nstr = buf

                    scribus.setText(nstr, item[0])
                    logger.info('...new text: ' + str(nstr))

            page += 1

        # -----------------------------------------------------------

        logger.info('! export...')
        exportPDF(opath)
        logger.info('! done :D')

        # scribus.closeDoc()
        return 'DONE'

    @staticmethod
    def EXPORT(opath):
        exportPDF(opath)
        logger.info('export current to PDF')

    @staticmethod
    def EXIT(self):
        logger.warn('! closing remote connection and shutdown server')
        self.shutdown()

    # def setup(self):
    #     print '! incoming connection'

    def lineReceived(self, line):
        """Handle a line recieved from network.

        Dispatch to corresponding handler, as 
        described in self.operations.
        """
        if line == '' or ':' not in line:
            self.sendLine(self.answers[None]['msg'])
            return

        mln = re.search(r'(.*?):(.*)', line)
        if mln:
            [code, arg] = [mln.group(1), mln.group(2)]
        else:
            self.sendLine('ERR_BAD_CMD')
            return

        logger.info('.cmd [%(code)s] && arg [%(arg)s]' % {'code': code, 'arg': arg})

        if (arg == '' or arg == None):
            arg = self

        if self.answers.has_key(code):
            if self.answers[code]['fun']:
                if hasattr(self, 'accb'): self.accb.reset(INACTIVE_TIMEOUT)
                self.backup()
                try:                    
                    logger.info('.commence command [%s]' % code)
                    res = self.answers[code]['fun'](arg)
                    if res:
                        self.sendLine(res)
                except:
                    logger.error('.things went wrong: %s ' % sys.exc_info()[1].message)
                    self.sendLine('INTERNAL ERROR')
                self.restore()
            else:
                self.sendLine(self.answers[code]['msg'])
        else:
            self.sendLine(self.answers[None]['msg'])

        logger.info('! done processing ')

Automator3.answers = {
    'CONVERT': {
        'fun': Automator3.CONVERT,
        'msg': 'DONE'
    },
    'EXPORT': {
        'fun': Automator3.EXPORT,
        'msg': 'DONE'
    },
    'EXIT': {
        'fun': Automator3.EXIT,
        'msg': None
    },
    None: {
        'fun': None,
        'msg': "I don't know what you mean"}}

# ------------------------------

if 'scribus' in globals():
    scribus.setRedraw(False)

if len(argv) > 1:
    PORT = int(argv[2])
else:
    PORT = DEFAULT_PORT

logger.info('! starting automation on port %d, timeout in %d secs' % (PORT, CONNECTION_TIMEOUT))
server = SocketServer.TCPServer(('localhost', PORT), Automator3)
server.timeout = CONNECTION_TIMEOUT
server.handle_request()

# import urllib

# code = 'CONVERT'
# arg = '{"CAPT": "ANOTHER","DESC1": "ANNN2233","DESC2": "AAEEEYYAAE"}'
# argenc = urllib.quote(arg)
# print 'DBG: ' + argenc
# res = Automation.answers[code]['fun']('Result.PDF:' + str(argenc))

# CONVERT:DBG.pdf:%7B%22CAPT%22%3A%20%22ichi%20da%20kuilla%22%2C%22DESC1%22%3A%20%22sex%20more%20for%20everyone%22%2C%22DESC2%22%3A%20%22houwyacc%20mooyacc%20greive%20est%20cos%28mes%29%22%7D
# CONVERT:DBG22.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%7D