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
import json
import time
import datetime
import threading
import subprocess
import hashlib

import task

globallock = threading.Lock()
def WriteToLog(msg):
    with globallock:
        tm = str(datetime.datetime.now())
        msg = tm + '  ' + str(msg)
        #self.log.write(msg + '\n')
        print msg

class JIDError(Exception):
    def __str__(self):
        return 'Invalid jid'

class LocalServer:
    def __init__(self, conf = 'tasks.conf', workers = 2):
        """
        """
        self.conf        = conf         # файл с конфигурацией задач
        self.workers     = workers      # количество потоков выполнения
        self.tasks_meta  = {}           # идентификаор задачи
        self.models      = []           # список моделей
        self.next_job_id = 1            # очередной идентификатор работы
        self.jobs        = {}           # очередб работ
        self.log         = None         #
        self.running     = False        #
        self.queue_lock  = threading.Lock()

        # init actions
        self.WriteToLog('local server initialized')

    def Close(self):
        self.Stop()
        self.WriteToLog('local server closed\n')

    def __del__(self):
        self.Close()

    def WriteToLog(self, msg):
        tm = str(datetime.datetime.now())
        msg = tm + '  ' + msg
        # self.log.write(msg + '\n')
        print msg

    def TestTaskData(self, data):
        pass

    def LoadModels(self):
        self.tasks_meta = {}
        self.models = []
        self.WriteToLog('tasks interrogation starts')
        for line in open(self.conf, 'r'):
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

                # вычисляем псевдоуникальный идентификатор модели
                tid = hashlib.md5(data['meta']).hexdigest()
                # сохраняем описание задачи
                self.tasks_meta[tid] = {
                    'title':    data.get('title', ''),
                    'author':   data.get('author', ''),
                    'meta':     data['meta'],
                    'exec':     line,
                    'models':   []
                }

                # выделяем описания моделей
                ms = data.get('models', {})
                for label, data in ms.iteritems():
                    model_descr = task.DataDescription(None, label, data, tid)
                    # добавляем в список описаний
                    self.models.append(model_descr)
                    self.tasks_meta[tid]['models'].append(model_descr)

                self.WriteToLog('Task from "{}" asked'.format(line))
            except IOError, e:
                self.WriteToLog('file "{}" not found'.format(line))
            except subprocess.CalledProcessError, e:
                self.WriteToLog('file "{}" not opened, error {} (msg: {})'.format(line, e, e.output))
            except ValueError, e:
                self.WriteToLog('file "{}" not opened, error "{}")'.format(line, e))

    def GetModels(self):
        return self.models

    def GetTaskMeta(self, tid):
        return self.tasks_meta.get(tid)

    def CheckModel(self, tid, model_label):
        models = self.tasks_meta[tid]['models']
        for model in models:
            if model_label == model.GetLabel():
                return model
        return None

    #--------------------------------------------------------------------------

    def CreateJob(self):
        jid = self.next_job_id
        self.next_job_id += 1
        with self.queue_lock:
            self.jobs[jid] = Job()
        return jid

    def GetJobsCount(self):
        return len(self.jobs)

    def GetJobState(self, jid):
        job = self.jobs.get(jid)
        if job:
            return job.GetState()

    def IsJobChanged(self, jid):
        job = self.jobs.get(jid)
        return job.IsChanged() if job else False

    def GetJobResult(self, jid):
        job = self.jobs.get(jid)
        return job.GetResult() if job else None

    def GetJobTID(self, jid):
        job = self.jobs.get(jid)
        return job.tid if job else None

    def LaunchJob(self, jid, data_def):
        job = self.jobs.get(jid)
        if job:
            tid      = data_def.DD.tid
            datadump = data_def.PackParams()
            job.Launch(tid, datadump)
        return True

    def StopJob(self, jid):
        job = self.jobs.get(jid)
        if job:
            job.Stop()

    def DeleteJob(self, jid):
        job = self.jobs.get(jid)
        if job:
            job.Stop()
            del self.jobs[jid]

    #--------------------------------------------------------------------------

    def Start(self):
        self.running = True
        for i in xrange(self.workers):
            worker = Worker(self)
            worker.start()

    def Stop(self):
        self.running = False

#-------------------------------------------------------------------------------

class Worker(threading.Thread):
    number = 0

    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server
        self.daemon = True
        self.id = Worker.number
        Worker.number += 1
        WriteToLog('worker started')

    def FindNextJob(self):
        with self.server.queue_lock:
            for jid, job in self.server.jobs.iteritems():
                # если нашли ожидающую вызова работу
                if job.state == JOB_READY:
                    job.state = JOB_RUNNING # пометим, как запущенную
                    WriteToLog('Job ({}) found'.format(jid))
                    return job
        return None

    def ProcessJob(self, job):
        try:
            execpath = self.server.GetTaskMeta(job.tid)['exec']
            # запускаем процесс на выполнение
            proc = subprocess.Popen([execpath, '-r'], shell = True,
                stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT, cwd = os.path.dirname(execpath))
            job.proc = proc
            # передаем стартовые параметры
            proc.stdin.write(job.datadump + '\n')
            proc.stdin.flush()
            # пока процесс не завершится (или его не прибьют)
            while proc.poll() == None:
                msg = proc.stdout.readline()
                self.ProcessMessage(job, msg)
                if not self.server.running:
                    proc.kill()
                    raise KeyError
        except Exception, e:
            WriteToLog('Job loop failed: ' + str(e))
            job.Finish(JOB_STOPPED)
        else:
            job.Finish(JOB_COMPLETED, 1.0)

    def ProcessMessage(self, job, msg):
        try:
            # разбираем полученный ответ
            data = json.loads(msg)
            # извлекаем оттуда ответ
            ans = data['answer']
            # ответ получен ок или предупреждение
            # записываем значение прогресса, если имеется
            if ans == 'ok' or ans == 'warning':
                job.percent = data.get('value', 0.0)
            # в ответе пришел результат вычислений
            # помещаем в секцию результата
            elif ans == 'result':
                job.result = task.ResultData(data['result'])
            # произошла ошибка
            elif ans == 'error':
                WriteToLog('Error! ' + msg)
            # недокументированный ответ приложения
            else:
                pass
            # возможно, комментарий прольет свет на проблему
            job.comment = data.get('comment', '')
            # почему изменяем флаг состояния здесь в конце?
            # потому как только после правильной обработки сообщения
            # мы можем быть уверены, что состояние действительно изменилось
            job.ChangeState()
        except KeyError as e:
            pass
        except ValueError as e:
            pass

    def Cycle(self):
        # найти следующее готовое к выполнению задание
        job = self.FindNextJob()
        # и, если нашли, приступаем к выполнению
        if job:
            WriteToLog("{} started!".format(self.id))
            self.ProcessJob(job)
            WriteToLog("{} finished!".format(self.id))
        else:
            time.sleep(1)

    def run(self):
        while True:
            if not self.server.running:
                return
            self.Cycle()

#-------------------------------------------------------------------------------

JOB_READY     = 0
JOB_RUNNING   = 1
JOB_STOPPED   = 2
JOB_COMPLETED = 3

class Job:
    def __init__(self):
        self.tid      = None
        self.datadump = None
        self.state    = JOB_STOPPED  # состояние выполнения работы
        self.percent  = -1.0         # прогресс (от 0.0 до 1.0 или -1.0)
        self.comment  = ''           # комментарий к ходу выполнения
        self.result   = None         # результат вычислений
        self.proc     = None         # ссылка на субпроцесс
        self.state_id = 0
        self.last_state_id = 0

    def ChangeState(self):
        self.state_id += 1

    def GetState(self):
        self.last_state_id = self.state_id
        return (self.state, self.percent, self.comment)

    def IsChanged(self):
        return self.state_id != self.last_state_id

    def Launch(self, tid, datadump):
        self.tid        = tid
        self.datadump   = datadump
        self.state      = JOB_READY
        self.percent    = -1.0
        self.ChangeState()

    def Stop(self):
        if self.proc and self.proc.poll() == None:
            WriteToLog('Try to kill')
            self.proc.kill()
            self.ChangeState()
            WriteToLog('Job killed')

    def Finish(self, state, percent = None):
        self.proc = None
        self.state = state
        if percent:
            self.percent = percent
        self.ChangeState()

    def GetResult(self):
        return self.result

#-------------------------------------------------------------------------------

import random
from pprint import pprint

def main():
    s = LocalServer(workers = 2)
    s.LoadModels()
    s.Start()
    models = s.GetModels()
    model = models[0]
    md = task.DataDefinition(model)
    md['d'] = 10
    md['r'] = 3.14

    slots = [ s.CreateJob() for i in xrange(1) ]
    for jid in slots:
        md['n'] = random.randint(20, 30)
        print jid, md['n']
        s.LaunchJob(jid, md)

    time.sleep(5)

    for jid in slots:
        pprint(s.GetJobResult(jid))
        print ''

if __name__ == '__main__':
    main()
