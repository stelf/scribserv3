#!/usr/bin/python2

CONNECTION_TIMEOUT = 15
INACTIVE_TIMEOUT = 120
DEFAULT_PORT = 22028
LOGFILE = 'scribserv.log'

try:
    import logging
    import re
    import SocketServer
    import urllib
    import sys
    import json
    from sys import argv
except ImportError:
    print '! missing some crucial system modules !'

try:
    import scribus
    from scribus import PDFfile, haveDoc
except ImportError:
    print '! yo runnin standalone, baba!'

# ----------------------------------------------------------------------------

logger = logging.getLogger('automator')
hdlr = logging.FileHandler(LOGFILE)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# ----------------------------------------------------------------------------

class TCPServerV4(SocketServer.TCPServer):
    address_family = SocketServer.socket.AF_INET
    allow_reuse_address = True
    timeout = CONNECTION_TIMEOUT

# ----------------------------------------------------------------------------

def exportPDF(opath='VR_EXPORT.pdf'):
    pdf = PDFfile()
    pdf.compress = 0
    pdf.bleedr = 2
    pdf.file = opath
    pdf.embedPDF = True
    pdf.save()

# ----------------------------------------------------------------------------

def processColors(xlat):
    cn = {name: xlat[name].split(',')
          for name in scribus.getColorNames()
          if name in xlat and ',' in xlat[name]}

    for name in cn:
        scribus.setColor(name, cn[name])
        logger.info('..replaced color %s => cmyk(%s)', name, xlat[name])

def processTemplate(xlat):
    if xlat is None:
        return
    logger.info(r'! process template')
    page = 1
    pagenum = scribus.pageCount()
    while page <= pagenum:
        logger.info(r'.process page ' + str(page))
        scribus.gotoPage(page)
        pitems = scribus.getPageItems()
        for item in [p for p in pitems if p[1] == 4]:
            logger.info(r'..process text ' + str(item))
            buf = scribus.getAllText(item[0])
            logger.info(r'...cur text: ' + str(buf))

            # try to figure placeholder
            mbuf = re.search(r'[{]+(\w+)[}]+', buf)
            if mbuf:
                # placeholder text
                phc = mbuf.group(1)
                Automator3.codes[item[0]] = phc
            else:
                # have we been here before?
                if item[0] in Automator3.codes:
                    phc = Automator3.codes[item[0]]

            # ok. do we have a xlat for this?
            if phc and xlat[phc]:
                nstr = xlat[phc]
            else:
                nstr = buf

            scribus.setText(nstr, item[0])
            logger.info('...new text: ' + str(nstr))

        page += 1

class Automator3(SocketServer.StreamRequestHandler):
    def sendLine(self, line):
        """abstract line sender

        network daemon changed 3 times, so some plumbing was needed
        """
        self.wfile.write(line + "\r\n")

    def handle(self):
        logger.info('! handle request. initiate dialogue.')
        logger.info('INTEGRATE v0.6 - with colours')
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

            app = gui.QApplication.instance()

            logger.warn('! shutdown server')
            self.connection.close()
            server.shutdown()

            logger.warn('! shutdown app')
            app.exit(0)

        except StandardError:
            logger.warn(r'could not import PyQt4.QtGui. just close all')
            self.connection.close()
            server.shutdown()

    @staticmethod
    def CONVERT(arg):
        logger.info('..decode params.')
        marg = re.search(r'(.*?):(.*)', arg)
        if marg:
            [opath, xlatenc] = [marg.group(1), marg.group(2)]
        else:
            logger.error('ERR_BAD_ARG: %s', arg)
            return 'ERR_BAD_ARG: %s' % arg

        logger.info('..opath: %s', opath)
        jsxlat = urllib.unquote(urllib.unquote(xlatenc))
        logger.info('..json: %s', jsxlat)

        try:
            xlat = json.loads(jsxlat)
            logger.info('..xlat: %s', xlat)
        except StandardError:
            logger.error('..error decoding json: %s', sys.exc_info()[1].message)

        # --------------------------------------------------------------------

        processColors(xlat)
        processTemplate(xlat)
 
        Automator3.EXPORT(opath)
        logger.info('! done :D')

        # scribus.closeDoc()
        return 'DONE'

    @staticmethod
    def EXPORT(opath):
        exportPDF(opath)
        logger.info('! export current to PDF')

    @staticmethod
    def OPEN(opath):
        logger.info('! open experiments')
        scribus.openDoc('good1.sla')

    @staticmethod
    def EXIT(obj):
        logger.warn('! closing remote connection and shutdown server')
        obj.shutdown()

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

        logger.info('.cmd [%(code)s] && arg [%(arg)s]', {'code': code, 'arg': arg})

        if arg == '' or arg is None:
            arg = self

        if self.answers.has_key(code):
            if self.answers[code]['fun']:
                # if hasattr(self, 'accb'):
                    # self.accb.reset(INACTIVE_TIMEOUT)
                    # self.backup()
                try:
                    logger.info('.commence command [%s]', code)
                    res = self.answers[code]['fun'](arg)
                    if res:
                        self.sendLine(res)
                except StandardError:
                    logger.error('.things went wrong: %s ', sys.exc_info()[1].message)
                    self.sendLine('INTERNAL ERROR')
                # self.restore()
            else:
                self.sendLine(self.answers[code]['msg'])
        else:
            self.sendLine(self.answers[None]['msg'])

        logger.info('! done processing ')

Automator3.codes = dict()

Automator3.answers = {
    'CONVERT': {
        'fun': Automator3.CONVERT,
        'msg': 'DONE'
    },
    'OPEN': {
        'fun': Automator3.OPEN,
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
        'msg': "UNKNOWN CMD"}}

# --------------------------------------------------------------------

if 'scribus' in globals():
    scribus.setRedraw(False)

if len(argv) > 1:
    PORT = int(argv[1])
else:
    PORT = DEFAULT_PORT

print '! starting automation on port %d, timeout in %d secs' % (PORT, CONNECTION_TIMEOUT)
print '! log is at %s ' % LOGFILE

logger.info('! starting automation on port %d, timeout in %d secs', PORT, CONNECTION_TIMEOUT)
server = TCPServerV4(('localhost', PORT), Automator3)
server.handle_request()

# --------------------------------------------------------------------

# import urllib

# code = 'CONVERT'
# arg = '{"CAPT": "ANOTHER","DESC1": "ANNN2233","DESC2": "AAEEEYYAAE", "COLOR1" : "cmyk(1,2,3,4)"}'
# argenc = urllib.quote(arg)
# print 'DBG: ' + argenc
# res = Automation.answers[code]['fun']('Result.PDF:' + str(argenc))

#
# CONVERT:DBG.pdf:%7B%22CAPT%22%3A%20%22ichi%20da%20kuilla%22%2C%22DESC1%22%3A%20%22sex%20more%20for%20everyone%22%2C%22DESC2%22%3A%20%22houwyacc%20mooyacc%20greive%20est%20cos%28mes%29%22%7D
# CONVERT:DBG22.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%7D
# CONVERT:DBG-color.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%2C%20%22COLOR1%22%20%3A%20%22cmyk%281%2C2%2C3%2C4%29%22%7D
#
