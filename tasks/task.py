#! coding: utf-8

import sys
import json
import os

def main():

#    try:

    d = os.path.dirname(__file__)
    os.chdir(d)

    if sys.argv[1] == '-i':
        with open('task.js') as f:
            d = json.load(f)
            print json.dumps(d, indent = 2)

    elif sys.argv[1] == '-r':
        textdata = raw_input()
        data = json.loads(data)

#    except:
#        print 'Error!'
#        sys.exit(-1)

if __name__ == '__main__':
    main()