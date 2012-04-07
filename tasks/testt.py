#! coding: utf-8

import sys
import json
import os
import time

def write(msg):
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()

def main():

#    try:

    if sys.argv[1] == '-i':
        with open('testt.json') as f:
            d = json.load(f)
            write(json.dumps(d, indent = 2))

    elif sys.argv[1] == '-r':
        textdata = raw_input()
        #data = json.loads(data)
        for i in xrange(10):
            time.sleep(0.5)
            write(json.dumps({ "hello": "world" }))

#    except:
#        print 'Error!'
#        sys.exit(-1)

if __name__ == '__main__':
    main()