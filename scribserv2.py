#!/usr/bin/python2

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor

try:
    import re
    import sys
    import urllib
    import json
    from sys import argv
except:
    print '! missing some crucial system module !'

try:
    import scribus
    from scribus import PDFfile, haveDoc
except:
    print '! yo runnin standalone, baba!'

tdata = {
    'CAPT': 'Caption baba',
    'DESC1': 'Description ino',
    'DESC2': 'Description dve'
}

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
        self.curdoc = None

    @staticmethod
    def CONVERT(arg):
        # print '...open file for work [%s] ' % arg
        # self.curdoc = scribus.openDoc(arg)

        # -----------------------------------------------------------

        print '..decode params... '

        marg = re.search(r'(.*?):(.*)', arg)
        if marg:
            [opath, xlatenc] = [marg.group(1), marg.group(2)]
        else:
            print  'ERR_BAD_ARG: %s' % arg
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

        print '! process template...'
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
    def REPLACE(arg):
        print 'replace textholders'

    @staticmethod
    def EXPORT(opath):
        exportPDF(opath)
        print 'export current to PDF'

    def EXIT(self):
        print 'closing remote connection'
        self.transport.loseConnection()

    def connectionMade(self):
        self.transport.write('Good Automator for Scribus (GAS) v0.3\r\n')
        self.transport.write('HELLO, VISIONR! :D\r\n')

    def lineReceived(self, line):
        if line == '' or ':' not in line:
            self.sendLine(self.answers[None]['msg'])
            return 'ERR_NO_PARAM'

        mln = re.search(r'(.*?):(.*)', line)
        if mln:
            [code, arg] = [mln.group(1), mln.group(2)]
        else:
            self.sendLine('ERR_BAD_CMD')
            return 'ERR_BAD_CMD'

        print '.cmd [%(code)s] && arg [%(arg)s]' % { 'code':code, 'arg': arg}

        if self.answers.has_key(code):
            if self.answers[code]['fun']:
                try:
                    print '.commence command [%s]' % code
                    res = self.answers[code]['fun'](arg)
                    self.sendLine(res)
                except:
                    print '.things went wrong: %s ' % sys.exc_info()[0]
                    self.sendLine('INTERNAL ERROR')
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
    'REPLACE': {
        'fun': Automation.REPLACE,
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
    None : {
        'fun': None,
        'msg': "I don't know what you mean"}}

# ------------------------------

if 'scribus' in globals():  
    scribus.setRedraw(False)

if len(argv) > 1:
    PORT = int(argv[2])
else:
    PORT = 22022

print '! starting automation on port %d' % PORT

endpoint = TCP4ServerEndpoint(reactor, PORT)
endpoint.listen(AutomationFactory())
reactor.run()

def checkInactive():
    print '! checking for inactivity'

cb = reactor.callLater(2, checkInactive)

# code = 'CONVERT'
# arg = '{"CAPT": "ichi da kuilla","DESC1": "sex more for everyone","DESC2": "houwyacc mooyacc greive est cos(mes)"}'
# argenc = urllib.quote(arg)
# print 'DBG: ' + argenc
# res = Automation.answers[code]['fun']('Result.PDF:' + str(argenc))

# CONVERT:DBG.pdf:%7B%22CAPT%22%3A%20%22ichi%20da%20kuilla%22%2C%22DESC1%22%3A%20%22sex%20more%20for%20everyone%22%2C%22DESC2%22%3A%20%22houwyacc%20mooyacc%20greive%20est%20cos%28mes%29%22%7D

