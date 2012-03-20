#-------------------------------------------------------------------------------
# Name:         task.py
# Purpose:
#
# Author:       Anton Vakhrushev
#
# Created:      14.03.2012
# Copyright:    (c) Anton Vakhrushev 2012
# Licence:      LGPL
#-------------------------------------------------------------------------------
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

class TaskDescription:
    """
    Description of the task. Task runs on server.
    """
    def __init__(self, server, execpath, data):
        """
        ``server`` is owner of task process

        ``execpath`` - path to task executable

        ``data`` is parsed data presentation about models, methods
        and meta information
        """
        self.server     = server
        self.execpath   = execpath
        self.data       = data
        self.models     = []
        for label, data in self.data['models'].iteritems():
            self.models.append(DataDescription(self, label, data))

    def GetModelsDescriptions(self):
        return self.models

#-------------------------------------------------------------------------------

class Parameter:
    def __init__(self, paramdescr):
        pass

def DoDataParametrization(objectdata):
    data = objectdata['data']
    for label in data:
        par = Parameter(data[label])
        data[label] = par

class DataDescription:
    def __init__(self, parentdescr, label, data):
        self.parentdescr = parentdescr
        self.label       = label
        self.data        = data

    def GetLabel(self):
        return self.label

    def GetTitle(self):
        return self.data.get('title', self.label)

    def GetAuthor(self):
        return self.data.get('author', 'Unknown')

    def GetId(self):
        return None

#-------------------------------------------------------------------------------

class DataDefinition:
    def __init__(self, objectdescr):
        self.descr = objectdescr
        self.params = {}
        self.taskjob = None

    def GetParameter(self, label):
        pass

    def SetParameter(self, label, value):
        pass

#-------------------------------------------------------------------------------

def main():
    pass

if __name__ == '__main__':
    main()
