

try:
    import sys
    from scribus import PDFfile, haveDoc


except ImportError:
    print 'This script only runs from within Scribus.'
    sys.exit(1)

try:
# get the os module
    import os
    import time
except ImportError:
    print 'Something went wrong importing os & time'
    sys.exit(1)

def loop_forever():

    # for line in iter(sys.stdin.readline, ''): # get line as soon as it is available
    #     print int(line)**2 # find square
    #     sys.stdout.flush()  # make the answer available immediately
    #     time.sleep(.5) # a delay to show that the answer is available immediately

    print 'eeh?'

print (sys.version) 

# loop_forever()

