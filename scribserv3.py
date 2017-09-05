#!/usr/bin/python2

# ****************************************************************************
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# ****************************************************************************


"""

(C) 2017 by Gheorghi Penkov

see the README.md for usage

"""

# VERSION = "v0.5 - w/working templating"
# VERSION = "v0.6 - w/colors & unit test"
# VERSION = "v0.7 - w/local+remote debug"
# VERSION = "v7.2 - w/local+remote debug & even smarter"
# VERSION = "v7.3 - replace ftw"
VERSION = "v7.4 - timeouts"

# ----------------------------------------------------------------------------

# uncomment this in order to debug remotely
# with winpdb (http://www.winpdb.org/)
# import rpdb2;
# rpdb2.start_embedded_debugger('slivi4smet')

# uncomment this in order to debug remotely
# as descibed in https://donjayamanne.github.io/pythonVSCodeDocs/docs/debugging_remote-debugging/
# although, not working at the time of writing fo this code

# import ptvsd
# ptvsd.enable_attach("slivi4smet", address=('0.0.0.0', 3040))
# ptvsd.wait_for_attach()

CONNECTION_TIMEOUT = 60
INACTIVE_TIMEOUT = 20
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
    import socket
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

    def replaceText(text, code):
        l = scribus.getTextLength(code)
        scribus.selectText(0, l-1, code)
        scribus.deleteText(code)
        scribus.insertText(text, 0, code)

        l = scribus.getTextLength(code)
        scribus.selectText(l-1, 1, code)
        scribus.deleteText(code)

    scribus.replaceText = replaceText

except ImportError:
    print '! yo runnin standalone, baba!'
    scribus = scribusdummy

# ----------------------------------------------------------------------------

logger = logging.getLogger('automator')

if LOGFILE is None:
    hdlr = logging.NullHandler()
else:
    hdlr = logging.FileHandler(LOGFILE)
    
# ----------------------------------------------------------------------------

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

        # options are described at
        # https://www.scribus.net/svn/Scribus/trunk/Scribus/doc/en/scripterapi-PDFfile.html

        pdf.compress = 0

        pdf.version = 15        # 15 = PDF 1.5 (Acrobat 6)
        pdf.bleedr = 2

        pdf.allowPrinting = True
        pdf.allowCopy = True

        pdf.outdst = 0          # out destination - printer
        pdf.file = opath
        pdf.profilei = True     # embed color profile
        pdf.embedPDF = True     # PDF in PDF
        pdf.useLayers = True    # export the layers (if any)
        pdf.fontEmbedding = 1   # text to curves

        pdf.resolution = 300    # good enough for most prints
        pdf.quality = 1         # high image quality

        pdf.save()
    else:
        logger.warn('no PDF printing in standalone run')

# ----------------------------------------------------------------------------

def processColors(xlat):
    if xlat is None:
        return
    rclean = re.compile('[{}]')
    rcmyk = re.compile(r'[(]*([\d\s,]+)[)]*')

    logger.info(r'! process colors')
    try:
        colcodes = [rclean.sub('', n)
                    for n in scribus.getColorNames()
                    if '{' in n and '}' in n]

        logger.info("! colcodes %s", str(colcodes))

        cn = {name: map(int, rcmyk.search(xlat[name]).group(1).split(', '))
              for name in colcodes
              if name in xlat and ',' in xlat[name]}

        logger.info("! colors xlat %s ", str(cn))

        for name, val in cn.iteritems():
            scribus.changeColor(name, *val)
            logger.info('..replaced color %s => (%s)', name, xlat[name])

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
            logger.info(r'..process item: [%s] ', item)
            buf = scribus.getAllText(item[0])
            logger.info(r'...cur text: [%s]', buf)
            phc = None
            # try to figure placeholder
            mbuf = re.search(r'[{]+(\w+)[}]+', buf)
            if mbuf is not None:
                # placeholder text
                phc = mbuf.group(1)
                Automator3.codes[item[0]] = phc
            else:
                # have we been here before?
                if item[0] in Automator3.codes:
                    phc = Automator3.codes[item[0]]

            # ok. do we have a xlat for this?
            if phc is not None and phc in xlat:
                nstr = xlat[phc]
            else:
                nstr = buf

            try:
                scribus.replaceText(nstr, item[0])
                logger.info('...new text: ' + str(nstr))
            except scribus.ScribusException:
                logger.error('.. scribus setText failed')

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
        logger.info('! adapter %s' % VERSION)
        self.saved = dict()
#        print self.socket.getTimeout()

        while 1:
            data = self.rfile.readline().strip()
            if not data:
                self.shutdown()
                return

            self.lineReceived(data)

    def server_close(self):
        logger.info('! finalize work and shutdown.')
        self.shutdown()

    def __init__(self, sock, client, tcpserv):
        self.socket = sock
        sock.settimeout(INACTIVE_TIMEOUT)
        try:
            SocketServer.StreamRequestHandler.__init__(self, sock, client, tcpserv)
        except socket.timeout:
            logger.info('! timeout waiting for input')
            self.shutdown()

    # self.accb = reactor.callLater(INACTIVE_TIMEOUT,
    #     functools.partial(
    #         Automator3.autoclose,
    #         self))

    def shutdown(self):
        """Close connection and app.

        Typically in case of inactivity.

        """

        logger.warn('! shutdown system.')

        try:
            # as per http://forums.scribus.net/index.php?topic=1448.0
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
        logger.info('..decoding params...')
        marg = re.search(r'(.*?):(.*)', arg)
        if marg:
            [opath, xlatenc] = [marg.group(1), marg.group(2)]
        else:
            logger.error('..bad argument: [%s]', arg)
            return 'ERR_BAD_ARG: %s' % arg

        logger.info('..opath: [%s]', opath)
        jsxlat = urllib.unquote(urllib.unquote(xlatenc))
        logger.info('..json: [%s]', jsxlat)

        try:
            xlat = json.loads(jsxlat)
            logger.info('..xlat: %s', xlat)
        except StandardError:
            logger.error('..error decoding json: %s', sys.exc_info()[1].message)
            return 'ERR_BAD_JSON: %s' % jsxlat

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
                try:
                    logger.info('.commence command [%s]', code)
                    res = self.answers[code]['fun'](arg)
                    if res:
                        self.sendLine(res)
                except scribus.ScribusException:
                    logger.error('.scribus failed: %s ', sys.exc_info()[1].message)
                except StandardError:
                    logger.error('.things went wrong: %s ', sys.exc_info())
                    self.sendLine('INTERNAL ERROR')
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

# maybe leave this true at some point when
# all development is done
scribus.setRedraw(False)

if len(argv) > 1:
    PORT = int(argv[1])
else:
    PORT = DEFAULT_PORT

if 'PRINTONLY' in argv:
    exportPDF('/tmp/test.pdf')
else:
    print '! starting automation on port %d, timeout in %d secs' % (PORT, CONNECTION_TIMEOUT)
    print '! log is at %s ' % LOGFILE
    logger.info('! starting automation on port %d, timeout in %d secs', PORT, CONNECTION_TIMEOUT)
    server = TCPServerV4(('localhost', PORT), Automator3)
    server.handle_request()

# --------------------------------------------------------------------

import urllib

# code = 'CONVERT'
# arg = '{"CAPT": "ANOTHER","DESC1": "ANNN2233","DESC2": "AAEEEYYAAE", "COLOR1" : "1,2,3,4", "BABA": "cmyk(100, 20, 50, 10)"}'
# arg = '{"NAMEs": "THE FUCKMAN","BABA": "cmyk(100, 20, 50, 10)"}'

# arg = '{"CAPT":"kfhgms/fgkmh/fklg", "COLOR" : "cmyk(32,45,44,12)"}'

# argenc = urllib.quote(arg)
# print argenc

# res = Automation.answers[code]['fun']('Result.PDF:' + str(argenc))

# xvfb-run -n 2 scribus-ng  -py ./scribserv3.py 22025 -- template.sla
# CONVERT:DBG.pdf:%7B%22CAPT%22%3A%20%22ichi%20da%20kuilla%22%2C%22DESC1%22%3A%20%22sex%20more%20for%20everyone%22%2C%22DESC2%22%3A%20%22houwyacc%20mooyacc%20greive%20est%20cos%28mes%29%22%7D
# CONVERT:DBG22.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%7D
# CONVERT:DBG-color.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%2C%20%22COLOR1%22%20%3A%20%221%2C2%2C3%2C4%22%2C%20%22BABA%22%3A%20%22cmyk%2810%2C%2020%2C%2030%2C%2040%29%22%7D
# CONVERT:temp/result.pdf:%7B%22NAME%22%3A%20%22THE%20BEST%20FUCKMAN%22%2C%22BABA%22%3A%20%22cmyk%28100%2C%2020%2C%2050%2C%2010%29%22%7D
# CONVERT:temp/result.pdf:%7B%22CAPT%22%3A%22kfhgms/fgkmh/fklg%22%2C%20%22COLOR%22%20%3A%20%22cmyk%2832%2C45%2C44%2C12%29%22%7D
