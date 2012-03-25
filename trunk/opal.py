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

class Project:
    pass

def main():
    import pprint
    s = server.LocalServer()
    s.LoadTasksDescriptions()
    ds = s.GetTasksDescriptions()
    ms = []
    for d in ds:
        ms.extend(d.GetModelsDescriptions())

    m = ms[0]
    pprint.pprint(m.data)

    print m.GetSpecifications()

if __name__ == '__main__':
    main()
