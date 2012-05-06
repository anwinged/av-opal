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

import copy
import json

#-------------------------------------------------------------------------------

class Parameter:
    def __init__(self, label, data):
        self.data = data
        self.data['label'] = label

    def GetLabel(self):
        return self.data['label']

    def GetType(self):
        return self.data['type']

    def GetTitle(self):
        return self.data.get('title', self.GetLabel())

    def GetComment(self):
        return self.data.get('comment', '')

    def GetDefault(self):
        return self.data.get('default')

    def GetTestExpression(self):
        return self.data.get('test')

    def Test(self, value):
        return True

    def DumpData(self):
        """
        Возвращает данные в стандартных контейнерах

        READ ONLY!!!
        """
        return self.data

    def LoadData(self, data):
        self.data = data

class Value(Parameter):
    def __init__(self, label, value):
        if isinstance(value, dict):
            self.data = value
        else:
            self.data = {
                'value': value,
                'type':  value.__class__.__name__
            }
        self.data['label'] = label

    def GetType(self):
        return self.data.get('type', 'unknown')

    def GetValue(self):
        return self.data['value']

class Column(Parameter):
    def __init__(self, colvalues):
        self.data = {}
        # следующие два поля должны обязательно присутствовать
        self.data['label'] = colvalues[0]
        self.data['type']  = colvalues[1]
        try:
            self.data['title'] = colvalues[2]
        except:
            pass

    def DumpData(self):
        return [
            self.GetLabel(),
            self.GetType(),
            self.GetTitle(),
        ]

#-------------------------------------------------------------------------------

class DataDescription:
    def __init__(self, parent, label, data, tid):
        self.parent = parent
        self.label  = label
        self.data   = data
        self.tid    = tid

        # создание описаний параметров
        self.pdata = self.data.get('params', {})
        # заменяем текстовое описание на объект-параметр
        for label in self.pdata:
            par = Parameter(label, self.pdata[label])
            self.pdata[label] = par

        # рекурсивное создание описаний спецификаций
        self.specs = { label: DataDescription(self, label, data, self.tid)
            for label, data in self.data.get('spec', {}).iteritems() }
                    
        # for label, data in self.data.get('spec', {}).iteritems():
        #     self.specs.append(DataDescription(self, label, data, self.tid))

    def GetLabel(self):
        return self.label

    def GetTitle(self):
        return self.data.get('title', self.label)

    def GetAuthor(self):
        return self.data.get('author', 'Unknown')

    def GetId(self):
        return None

    def GetParent(self):
        return self.parent

    def GetSpecs(self):
        return self.specs

    def IsExecutable(self):
        return self.data.get('exec', True)

    def GetImage(self):
        return self.data.get('img')

    def GetTaskId(self):
        return self.tid

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
        self.job = None

    def __getitem__(self, label):
        return self.params[label]

    def __setitem__(self, label, value):
        if self.DD[label].Test(value):
            self.params[label] = value
        else:
            raise ValueError

    def Copy(self):
        res = copy.copy(self)
        res.params = copy.copy(self.params)
        res.job = None
        return res

    def PackParams(self):
        package = []
        owner = self
        while owner:
            data = {'label': owner.DD.GetLabel(), 'params': owner.params}
            package.append(data)
            owner = owner.parent
        package.reverse()
        return json.dumps(package)

#-------------------------------------------------------------------------------

class ResultData:
    def __init__(self, data):
        self.LoadData(data)

    def GetColumns(self):
        return self.head

    columns = property(GetColumns)

    def GetRows(self):
        return self.table

    rows = property(GetRows)

    def GetCell(self, row, col):
        return self.table[row][col]

    def GetColumn(self, index):
        return [ row[index] for row in self.rows ]

    def Zip(self, col1, col2):
        return [ (row[col1], row[col2]) for row in self.rows ]

    def DumpData(self):
        data = {}
        if self.data:
            data['data'] = { key: self.data[key].DumpData() 
                for key in self.data }
        
        if self.head:
            head = [ col.DumpData() for col in self.columns ]
            body = self.table
            data['table'] = [head] + body
        return data

    def LoadData(self, data):
        self.data = {}
        for key, value in data.get('data', {}).iteritems():
            self.data[key] = Value(key, value)

        table = data.get('table', [])
        self.head  = []
        self.table = []
        if table:
            self.head  = [ Column(item) for item in table[0] ]
            self.table = table[1:]

