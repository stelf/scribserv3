#!/usr/bin/python2

INACTIVE_TIMEOUT = 120
DEFAULT_PORT = 22022

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.python.failure import Failure

try:
    import re
    import urllib
    import sys
    import json
    from sys import argv
    import functools
except:
    print '! missing some crucial system module !'

try:
    import scribus
    from scribus import PDFfile, haveDoc
except:
    print '! yo runnin standalone, baba!'

# ----------------------------------------------------------------------------


def exportPDF(opath='VR_EXPORT.pdf'):
    pdf = PDFfile()
    pdf.compress = 0
    pdf.bleedr = 2
    pdf.file = opath
    pdf.embedPDF = True
    pdf.save()

class Automation(LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.saved = {}
        self.curdoc = None
        self.accb = reactor.callLater(INACTIVE_TIMEOUT, 
            functools.partial(
                Automation.autoclose, 
                self))

    def autoclose(self):
        print '! close connection due to innactivity.'
        self.transport.loseConnection()
        try:
            import PyQt4.QtGui as gui

            app = gui.QApplication.instance()
            app.exit(0)
        except:
            print r'running without Scribus. just close connection'
 
    def backup(self):
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
        page = 1
        pagenum = scribus.pageCount()
        print '! restore values into %d pages' % pagenum
        
        while page <= pagenum:
            scribus.gotoPage(page)
            pitems = scribus.getPageItems()
            for item in pitems:
                if item[1] == 4:
                    if self.saved.get(item[0]) != None:
                       scribus.setText(self.saved[item[0]], item[0])
            page += 1

    @staticmethod
    def CONVERT(arg):
        print '..decode params... '
        marg = re.search(r'(.*?):(.*)', arg)
        if marg:
            [opath, xlatenc] = [marg.group(1), marg.group(2)]
        else:
            print 'ERR_BAD_ARG: %s' % arg
            return 'ERR_BAD_ARG: %s' % arg

        print '..opath: %s' % opath
        jsxlat = urllib.unquote(urllib.unquote(xlatenc))
        print '..json: %s' % jsxlat

        try:
            xlat = json.loads(jsxlat)
            print '..xlat: %s' % xlat
        except:
            print '..error decoding json: %s' % sys.exc_info()[0]

        # -----------------------------------------------------------

        print r'! process template...'
        page = 1
        pagenum = scribus.pageCount()
        while page <= pagenum:
            print r'.process page ' + str(page)
            scribus.gotoPage(page)
            pitems = scribus.getPageItems()
            for item in pitems:
                print r'..process item ' + str(item)
                if item[1] == 4:
                    buf = scribus.getAllText(item[0])
                    print r'...cur: ' + str(buf)

                    mbuf = re.search(r'[{]+(\w+)[}]+', buf)
                    v = mbuf.group(1)
                    if v and xlat[v]:
                        nstr = xlat[v]
                    else:
                        nstr = buf

                    scribus.setText(nstr, item[0])
                    print '...new: ' + str(nstr)

            page += 1

        # -----------------------------------------------------------

        print '! export...'
        exportPDF(opath)
        print '! done :D'

        # scribus.closeDoc()
        return 'DONE'

    @staticmethod
    def EXPORT(opath):
        exportPDF(opath)
        print 'export current to PDF'

    @staticmethod
    def EXIT(aobj):
        print '! closing remote connection'
        aobj.transport.loseConnection()

    def connectionMade(self):
        self.transport.write('Good Automator for Scribus (GAS) v0.3\r\n')
        self.transport.write('HELLO, VISIONR! :D\r\n')

    def lineReceived(self, line):
        if line == '' or ':' not in line:
            self.sendLine(self.answers[None]['msg'])
            return

        mln = re.search(r'(.*?):(.*)', line)
        if mln:
            [code, arg] = [mln.group(1), mln.group(2)]
        else:
            self.sendLine('ERR_BAD_CMD')
            return

        print '.cmd [%(code)s] && arg [%(arg)s]' % {'code': code, 'arg': arg}

        if (arg == '' or arg == None):
            arg = self

        if self.answers.has_key(code):
            if self.answers[code]['fun']:
                self.accb.reset(INACTIVE_TIMEOUT)
                self.backup()
                try:                    
                    print '.commence command [%s]' % code
                    res = self.answers[code]['fun'](arg)
                    if res:
                        self.sendLine(res)
                except:
                    print '.things went wrong: %s ' % sys.exc_info()[0]
                    self.sendLine('INTERNAL ERROR')
                self.restore()
            else:
                self.sendLine(self.answers[code]['msg'])
        else:
            self.sendLine(self.answers[None]['msg'])


class AutomationFactory(Factory):
    def buildProtocol(self, addr):
        return Automation(self)


Automation.answers = {
    'CONVERT': {
        'fun': Automation.CONVERT,
        'msg': 'DONE'
    },
    'EXPORT': {
        'fun': Automation.EXPORT,
        'msg': 'DONE'
    },
    'EXIT': {
        'fun': Automation.EXIT,
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

print '! starting automation on port %d' % PORT

endpoint = TCP4ServerEndpoint(reactor, PORT)
endpoint.listen(AutomationFactory())

reactor.run()


# import urllib

# code = 'CONVERT'
# arg = '{"CAPT": "ANOTHER","DESC1": "ANNN2233","DESC2": "AAEEEYYAAE"}'
# argenc = urllib.quote(arg)
# print 'DBG: ' + argenc
# res = Automation.answers[code]['fun']('Result.PDF:' + str(argenc))

#
#
# CONVERT:DBG.pdf:%7B%22CAPT%22%3A%20%22ichi%20da%20kuilla%22%2C%22DESC1%22%3A%20%22sex%20more%20for%20everyone%22%2C%22DESC2%22%3A%20%22houwyacc%20mooyacc%20greive%20est%20cos%28mes%29%22%7D
# CONVERT:DBG22.pdf:%7B%22CAPT%22%3A%20%22ANOTHER%22%2C%22DESC1%22%3A%20%22ANNN2233%22%2C%22DESC2%22%3A%20%22AAEEEYYAAE%22%7D

