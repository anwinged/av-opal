#-------------------------------------------------------------------------------
# Name:         opal.py
# Purpose:
#
# Author:       Anton Vakhrushev
#
# Created:      14.03.2012
# Copyright:    (c) Anton Vakhrushev 2012
# Licence:      LGPL
#-------------------------------------------------------------------------------
#!/usr/bin/env python#!/usr/bin/env python
#! coding: utf-8

import server
import task

def main():
    import pprint
    s = server.LocalServer()
    s.LoadTasksDescriptions()
    ds = s.GetTasksDescriptions()[0]

    pprint.pprint(ds.data)

if __name__ == '__main__':
    main()
