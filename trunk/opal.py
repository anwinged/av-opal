#!/usr/bin/env python
#! coding: utf-8

import subprocess
import json
import os, sys
import datetime

#-------------------------------------------------------------------------------

def GenerateId(data):
    import hashlib
    title  = data['title']
    author = data['author']
    id = hashlib.md5(title + author).hexdigest()
    return id

#-------------------------------------------------------------------------------

class LocalServer:
    """
    """
    def __init__(self):
        self.max_run = 2
        self.cur_run = 0

        self.task_descrs = []
        self.task_queue = []
        self.log = None

        self.Init()

    def Init(self):
        self.log = open('log.txt', 'w')
        self.WriteToLog('local server initialized')

    def Close(self):
        self.WriteToLog('local server closed\n')

    def __del__(self):
        self.Close()

    def WriteToLog(self, msg):
        tm = str(datetime.datetime.now())
        msg = tm + '  ' + msg
        self.log.write(msg + '\n')
        print msg

    def Start(self):
        pass

    def Stop(self):
        pass

    def TestTaskData(self, data):
        pass

    def LoadTasksDescriptions(self, source = 'tasks.conf'):
        """
        """
        self.task_descrs = []

        self.WriteToLog('tasks interrogation starts')
        for line in open(source, 'r'):
            try:
                # нормализуем указанный путь
                line = os.path.normpath(line)
                # считываем данные через shell (важно для скриптовых языков)
                textdata = subprocess.check_output([line, '-i'], shell = True)
                # загружаем данные описания задачи
                data = json.loads(textdata)
                # провряем их на корректность
                self.TestTaskData(data)
                # пакуем все в объект-описание задачи
                task_descr = TaskDescription(self, line, data)
                # добавляем в список описаний
                self.task_descrs.append(task_descr)
                self.WriteToLog('Task from "{}" asked'.format(line))
            except IOError, e:
                self.WriteToLog('file "{}" not found'.format(line))
            except subprocess.CalledProcessError, e:
                self.WriteToLog('file "{}" not opened, error {} (msg: {})'.format(line, e, e.output))
            except ValueError, e:
                self.WriteToLog('file "{}" not opened, error "{}")'.format(line, e))

    def GetTasksDescriptions(self):
        """
        Return list with task descriptions
        """
        return self.task_descrs

    def GetTaskCount(self):
        pass

    def GetTask(self, index):
        pass

    def AddTask(self, task):
        pass

#-------------------------------------------------------------------------------

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
            self.models.append(ModelDescription(self, label, data))

    def GetModelsDescriptions(self):
        return self.models

#-------------------------------------------------------------------------------

class Parameter:
    def __init__(self, paramdescr):
        pass

def DoDataParametrization(data):
    pass

class ObjectDescription:
    def __init__(self, parentdescr, label, data):
        self.parentdescr = parentdescr
        self.label       = label
        self.data        = data
        DoDataParametrization(self.data)

    def GetLabel(self):
        return self.label

    def GetTitle(self):
        return self.data.get('title', self.label)

    def GetAuthor(self):
        return self.data.get('author', 'Unknown')

    def GetId(self):
        return None

class ModelDescription(ObjectDescription):
    def __init__(self, taskdescr, label, data):
        ObjectDescription.__init__(self, taskdescr, label, data)
        self.methods = []
        for label, data in self.data['methods'].iteritems():
            self.methods.append(MethodDescription(self, label, data))

    def GetMethodsDescriptions(self):
        return self.methods

class MethodDescription(ObjectDescription):
    def __init__(self, modeldescr, label, data):
        ObjectDescription.__init__(self, modeldescr, label, data)

#-------------------------------------------------------------------------------

class ObjectDefinition:
    def __init__(self, objectdescr):
        self.descr = objectdescr
        self.params = {}

class ModelDefinition(ObjectDefinition):
    def __init__(self, modeldescr):
        ObjectDefinition(self, modeldescr)

class MethodDefinition(ObjectDefinition):
    def __init__(self, methoddescr):
        ObjectDefinition(self, methoddescr)

#-------------------------------------------------------------------------------

class Task:
    def __init__(self, server):
        pass

    def Start(self):
        pass

    def Stop(self):
        pass

    def Pause(self):
        pass

    def Status(self):
        pass

#-------------------------------------------------------------------------------

def main():
    s = LocalServer()
    s.LoadTasksDescriptions()
    ds = s.GetTasksDescriptions()
    ms = ds[0].GetModelsDescriptions()
    for m in ms:
        print m.GetTitle()
        print m.GetLabel()
        print m.GetAuthor()
        print m.GetId()

if __name__ == '__main__':
    main()
