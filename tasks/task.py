#! coding: utf-8

import sys
import json

def main():

##    if len(sys.argv) != 2:
##        print 'Error!'
##        return
##
##    if sys.argv[1] == '-i':
    with open('task.js') as f:
        d = json.load(f)
        print json.dumps(d, indent = 2)

##    elif sys.argv[1] == '-r':
##        data = raw_input()
##        data = json.loads(data)

if __name__ == '__main__':
    main()