#-------------------------------------------------------------------------------
# Name:         server.py
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

import subprocess
import json
import os, sys
import datetime

import task

def GenerateId(data):
    import hashlib
    title  = data['title']
    author = data['author']
    id = hashlib.md5(title + author).hexdigest()
    return id

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
                task_descr = task.TaskDescription(self, line, data)
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

class Taskjob:
    def __init__(self, data):
        self.data = data

    def Start(self):
        pass

    def Stop(self):
        pass

    def Pause(self):
        pass

    def Status(self):
        pass


def main():
    pass

if __name__ == '__main__':
    main()
