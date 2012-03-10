#!/usr/bin/env python
#! coding: utf-8

import subprocess

#-------------------------------------------------------------------------------

class LocalServer:
    """
    """
    def __init__(self):
        self.max_run = 2
        self.cur_run = 0

        self.task_queue = []

    def GetTaskDescriptionList(self):
        pass

    def GetTaskCount(self):
        pass

    def GetTask(self, index):
        pass

    def AddTask(self, *args):
        pass

#-------------------------------------------------------------------------------

class TaskDescription:
    """
    Description of the task. Task runs on server.
    """
    def __init__(self, server, tid, data):
        self.server = server
        self.tid = tid
        self.data = data

#-------------------------------------------------------------------------------

class ObjectDescription:
    def __init__(self, taskdescr, label, data):
        pass

class ObjectDefinition:
    def __init__(self, taskdescr, label, data):
        pass

class Parameter:
    def __init__(self, paramdescr):
        pass

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
    pass

if __name__ == '__main__':
    main()
