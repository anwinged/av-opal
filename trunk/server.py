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

globallock = threading.Lock()
def WriteToLog(msg):
    with globallock:
        tm = str(datetime.datetime.now())
        msg = tm + '  ' + str(msg)
        #self.log.write(msg + '\n')
        print msg


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
        self.jobs_queue = []
        self.log = None

        self.queue_lock = threading.Lock()

        # init actions

        self.log = open('log.txt', 'w')
        self.WriteToLog('local server initialized')

        for i in xrange(2):
            worker = Worker(self.jobs_queue, self.queue_lock)
            worker.start()

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
                line = os.path.abspath(line)
                # считываем данные через shell (важно для скриптовых языков)
                textdata = subprocess.check_output([line, '-i'], shell = True,
                    cwd = os.path.dirname(line))
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

    def AddJob(self, taskd, datadump):
        job = Job(taskd, datadump)
        with self.queue_lock:
            self.jobs_queue.append(job)
        WriteToLog('Job added')
        return job

#-------------------------------------------------------------------------------

class Worker(threading.Thread):
    number = 0

    def __init__(self, queue, lock):
        threading.Thread.__init__(self)
        self.queue = queue
        self.lock = lock
        self.daemon = True
        WriteToLog('worker started')
        self.id = Worker.number
        Worker.number += 1

    def Cycle(self):
        job = None
        # найти следующее готовое к выполнению задание
        with self.lock:
            for j in self.queue:
                if not j.IsBusy():
                    job = j
                    job.SetBusy()
                    break
        # и, если нашли, приступаем к выполнению
        if job:
            WriteToLog("{} started!".format(self.id))
            job.Start()
            WriteToLog("{} finished!".format(self.id))
        else:
            time.sleep(1)

    def run(self):
        while True:
            self.Cycle()

#-------------------------------------------------------------------------------

JOB_READY     = 0
JOB_BUSY      = 1
JOB_RUNNING   = 2
JOB_STOPPED   = 3
JOB_COMPLETED = 4

class Job:
    def __init__(self, taskd, datadump):
        self.taskd   = taskd
        self.datad   = datadump
        self.state   = JOB_READY
        self.percent = 0.0
        self.comment = ''
        self.result  = None
        self.proc    = None

    def ProcessMsg(self, msg):
        # разбираем полученный ответ
        data = json.loads(msg)
        # извлекаем оттуда ответ
        ans = data['answer']
        # ответ получен ок или предупреждение
        # записываем значение прогресса, если имеется
        if ans == 'ok' or ans == 'warning':
            self.percent = data.get('value', 0.0)
        # в ответе пришел результат вычислений
        # помещаем в секцию результата
        elif ans == 'result':
            self.result = data['result']
        # произошла ошибка
        elif ans == 'error':
            WriteToLog('Error! ' + msg)
        # недокументированный ответ приложения
        else:
            pass
        # возможно, комментарий прольет свет на проблему
        self.comment = data.get('comment', '')


    def Start(self):
        try:
            self.state = JOB_RUNNING
            execpath = self.taskd.execpath
            # запускаем процесс на выполнение
            self.proc = subprocess.Popen([execpath, '-r'], shell = True,
                stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT, cwd = os.path.dirname(execpath))
            # передаем стартовые параметры
            istream = self.proc.stdin
            ostream = self.proc.stdout
            istream.write(self.datad + '\n')
            istream.flush()
            # пока процесс не завершится (или его не прибьют)
            while self.proc.poll() == None:
                try:
                    msg  = ostream.readline()
                    #msg = msg.strip()
                    self.ProcessMsg(msg)
                except Exception, e:
                    #WriteToLog('Income msg failed: ' + str(e))
                    pass
            self.state = JOB_COMPLETED
        except Exception, e:
            WriteToLog('Job loop failed: ' + str(e))
            self.state = JOB_STOPPED

    def SetBusy(self):
        self.state = JOB_BUSY

    def IsBusy(self):
        return self.state != JOB_READY

    def IsRunning(self):
        return self.state == JOB_BUSY or self.state == JOB_RUNNING

    def IsFinished(self):
        return self.state == JOB_COMPLETED or self.state == JOB_STOPPED

    def IsComplete(self):
        return self.GetStatus() == JOB_COMPLETE

    def Stop(self):
        WriteToLog('Try to kill')
        if self.proc and self.proc.poll() == None:
            self.proc.kill()
            WriteToLog('Job killed')

    def GetState(self):
        return self.state

    def GetResult(self):
        return self.result

def main():
    pass

if __name__ == '__main__':
    main()
