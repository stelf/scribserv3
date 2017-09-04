
import re
import logging

logger = logging.getLogger('automator')
hdlr = logging.FileHandler('test.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

class scribus(object):
    @staticmethod
    def getColorNames():
        print 'scribus.getColorNames()'
        return ['{{COLOR1}}', '{{COLOR2}}']

    @staticmethod
    def changeColor(a, b):
        print 'scribus.changeColor( %s, %s)' % (a, b)

def processColors(xlat):
    if xlat is None:
        return
    p = re.compile('[{}]')

    logger.info(r'! process colors')
    try:
        colcodes = [p.sub('', n)
                    for n in scribus.getColorNames()
                    if '{' in n and '}' in n]

        print "! colcodes %s" % str(colcodes)

        cn = {name: xlat[name].split(',')
              for name in colcodes
              if name in xlat and ',' in xlat[name]}

        print "! colors xlat %s " % cn

        for name, val in cn.iteritems():
            scribus.changeColor(name, val)
            logger.info('..replaced color %s => cmyk(%s)', name, xlat[name])

    except scribus.ScribusException:
        logger.error('..scribus failed operation: %s', sys.exc_info()[1].message)
    except StandardError:
        logger.error('..python standard error raised: %s', sys.exc_info()[1].message)
        logger.error(sys.exc_info())

processColors({u'CAPT': u'ANOTHER', u'COLOR1': u'1,2,3,4', u'DESC1': u'ANNN2233', u'DESC2': u'AAEEEYYAAE'})