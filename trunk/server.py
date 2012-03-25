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

import os
import sys
import json
import time
import datetime
import threading
import subprocess

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
        self.max_workers = 2

        self.task_descrs = []
        self.task_queue = []
        self.log = None

        self.lock = threading.Lock()

        # init actions

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

    def GetJobsCount(self):
        pass

    def GetJob(self, index):
        pass

    def AddJob(self, taskdescr, data):
        pass

#-------------------------------------------------------------------------------

class Worker(threading.Thread):
    def __init__(self, queue, lock):
        threading.Thread.__init__(self)
        self.queue = queue
        self.lock = lock
        self.daemon = True

    def FindNext(self):
        result = None
        for job in self.queue:
            if job.GetStatus() == JOB_STOP:
                result = job
        return result

    def run(self):
        while True:
            job = None
            with self.lock:
                job = FindNext()
            if job:
                job.Start()
            else:
                time.sleep(1)

#-------------------------------------------------------------------------------

JOB_STOP     = 0
JOB_RUN      = 1
JOB_PAUSE    = 2
JOB_COMPLETE = 4

class Job:
    def __init__(self, taskd, datadump):
        self.taskd   = taskd
        self.datad   = datadump
        self.status  = JOB_STOP
        self.percent = 0.0
        self.result  = None

        #self.

    def Start(self):
        pass

    def Stop(self):
        pass

    def Pause(self):
        pass

    def GetStatus(self):
        return self.status

    def IsComplete(self):
        return self.GetStatus() == JOB_COMPLETE

    def GetResult(self):
        return self.result

def main():
    pass

if __name__ == '__main__':
    main()
