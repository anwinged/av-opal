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
            self.models.append(DataDescription(self, label, data, self.server))

    def GetModelsDescriptions(self):
        return self.models

#-------------------------------------------------------------------------------

class Parameter:
    def __init__(self, data):
        self.data = data

    def GetType(self):
        return self.data['type']

    def GetTitle(self):
        return self.data.get('title', '')

    def GetComment(self):
        return self.data.get('comment', '')

    def GetDefault(self):
        return self.data.get('default')

    def GetTestExpresion(self):
        return self.data.get('test')

    def Test(self, value):
        return True

    #def __repr__(self):
    #    return "'{}'".format(
    #        self.GetType()
    #    )

#-------------------------------------------------------------------------------

class DataDescription:
    def __init__(self, parent, label, data, taskd):
        self.parent = parent
        self.label  = label
        self.data   = data
        self.taskd  = taskd

        # создание описаний параметров
        self.pdata = self.data.get('params', {})
        for label in self.pdata:
            par = Parameter(self.pdata[label])
            self.pdata[label] = par

        self.specs = []
        # рекурсивное создание описаний спецификаций
        for label, data in self.data.get('spec', {}).iteritems():
            self.specs.append(DataDescription(self, label, data, self.taskd))

    def GetLabel(self):
        return self.label

    def GetTitle(self):
        return self.data.get('title', self.label)

    def GetAuthor(self):
        return self.data.get('author', 'Unknown')

    def GetId(self):
        return None

    def GetSpecifications(self):
        return self.specs

    def IsExecutable(self):
        return self.data.get('exec', True)

    def __getitem__(self, label):
        return self.pdata.get(label)

#-------------------------------------------------------------------------------

class DataDefinition:
    def __init__(self, datadescr, parent = None):
        self.DD = datadescr
        self.parent = parent
        self.params = {}
        for param in self.DD.pdata:
            self.params[param] = self.DD[param].GetDefault()

        self.taskjob = None

    def __getitem__(self, label):
        return self.params[label]

    def __setitem__(self, label, value):
        if self.DD[label].Test(value):
            self.params[label] = value
        else:
            raise ValueError

    def PackParams(self):

        owner = self
        package = []
        while owner:
            data = {'label': owner.DD.GetLabel(), 'params': owner.params}
            package.append(data)
            owner = owner.parent
        package.reverse()

        return package

#-------------------------------------------------------------------------------

import server, json
from pprint import pprint

def main():
    s = server.LocalServer()
    s.LoadTasksDescriptions()
    ds = s.GetTasksDescriptions()
    models = []
    for d in ds:
        models.extend(d.GetModelsDescriptions())

    model = models[0]

    mdef = DataDefinition(model)
    #pprint(mdef.DD.data)
    mdef['x'] = 20

    p = mdef.PackParams()
    pprint(p)

if __name__ == '__main__':
    main()
