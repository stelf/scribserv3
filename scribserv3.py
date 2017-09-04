#!/usr/bin/python2

# uncomment this in order to debug remotely
# with winpdb (http://www.winpdb.org/)

# import rpdb2; 
# rpdb2.start_embedded_debugger('dqdomraz')

CONNECTION_TIMEOUT = 15
INACTIVE_TIMEOUT = 120
DEFAULT_PORT = 22022
LOGFILE = 'scribserv.log'

# LOGFILE = None

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

# ----------------------------------------------------------------------------

class scribusdummy(object):
    page = 0
    class ScribusException(Exception):
        pass

    @staticmethod
    def getColorNames():
        print 'scribus.getColorNames()'
        return ['{{COLOR1}}', '{{COLOR2}}']

    @staticmethod
    def changeColor(name, c, m, y, k):
        print 'scribus.changeColor( "%s", %d, %d, %d, %d)' % (name, c, m, y, k)

    @staticmethod
    def setRedraw(a):
        print 'scribus.setRedraw(%s)' % a

    @staticmethod
    def pageCount():
        print 'scribus.pageCount()'
        return 1

    @staticmethod
    def gotoPage(a):
        print 'scribus.gotoPAge(%d)' % a

    @staticmethod
    def getAllText(a):
        print 'scribus.getAllText("%s")' % a
        return 'dummy text'

    @staticmethod
    def setText(nstr, item):
        print 'scribus.setText("%s", "%s")' % (nstr, item)

    @staticmethod
    def getPageItems():
        print 'scribus.getPageItems()'
        return [('Image1', 2, 1), ('Text3', 4, 3), ('Text4', 4, 4), ('Image6', 2, 6)]

# ----------------------------------------------------------------------------

try:
    import scribus
    from scribus import PDFfile, haveDoc
except ImportError:
    print '! yo runnin standalone, baba!'
    scribus = scribusdummy

# ----------------------------------------------------------------------------

logger = logging.getLogger('automator')

if LOGFILE is None:
    hdlr = logging.NullHandler()
else:
    hdlr = logging.FileHandler(LOGFILE)# ---------------------------------------------

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
    if 'PDFfile' in globals():
        pdf = PDFfile()
        pdf.compress = 0
        pdf.bleedr = 2
        pdf.file = opath
        pdf.embedPDF = True
        pdf.save()
    else:
        logger.warn('no PDF printing in standalone run')

# ----------------------------------------------------------------------------

def processColors(xlat):
    if xlat is None:
        return
    p = re.compile('[{}]')

    logger.info(r'! process colors')
    try:
        colcodes = [p.sub('', n)
                    for n in scribus.getColorNames()
                    if '{' in n and '}' in n]

        logger.info("! colcodes %s", str(colcodes))

        cn = {name: map(int, xlat[name].split(','))
              for name in colcodes
              if name in xlat and ',' in xlat[name]}

        logger.info("! colors xlat %s ", str(cn))

        for name, val in cn.iteritems():
            scribus.changeColor(name, *val)
            logger.info('..replaced color %s => cmyk(%s)', name, xlat[name])

    except scribus.ScribusException:
        logger.error('..scribus failed: %s', sys.exc_info()[1].message)
    except StandardError:
        logger.error('..standard error: %s', sys.exc_info()[1].message)

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

            phc = None

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
            if phc is not None and xlat[phc]:
                nstr = xlat[phc]
            else:
                nstr = buf

            scribus.setText(nstr, item[0])
            logger.info('...new text: ' + str(nstr))

        page += 1

    logger.info('! done processing template')

class Automator3(SocketServer.StreamRequestHandler):
    def sendLine(self, line):
        """abstract line sender

        network daemon changed 3 times, so some plumbing was needed
        """
        self.wfile.write(line + "\r\n")

    def handle(self):
        logger.info('! handle request. initiate dialogue.')
        logger.info('INTEGRATE v0.7 - w/local+remote debug')
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

        processTemplate(xlat)
        processColors(xlat)

        Automator3.EXPORT(opath)
        logger.info('! done :D')

        # scribus.closeDoc()
        return 'DONE'

    @staticmethod
    def EXPORT(opath):
        exportPDF(opath)
        logger.info('! export current to PDF')

    @staticmethod
    def OPEN(opath='temp/good1.sla'):
        logger.info('! open experiments')
        try:
            scribus.openDoc(opath)
        except scribus.ScribusException:
            logger.error('.can not open [%s], because %s', opath, sys.exc_info()[1].message)

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

        logger.info('! done processing command [%s]', code)

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
# arg = '{"CAPT": "ANOTHER","DESC1": "ANNN2233","DESC2": "AAEEEYYAAE", "COLOR1" : "1,2,3,4"}'
# argenc = urllib.quote(arg)
# print 'DBG: ' + argenc

# res = Automation.answers[code]['fun']('Result.PDF:' + str(argenc))

#
# CONVERT:DBG.pdf:%7B%22CAPT%22%3A%20%22ichi%20da%20kuilla%22%2C%22DESC1%22%3A%20%22sex%20more%20for%20everyone%22%2C%22DESC2%22%3A%20%22houwyacc%20mooyacc%20greive%20est%20cos%28mes%29%22%7D
# CONVERT:DBG22.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%7D
# CONVERT:DBG-color.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%2C%20%22COLOR1%22%20%3A%20%221%2C2%2C3%2C4%22%7D
#
