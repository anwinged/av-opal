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
import wx
import wx.propgrid as wxpg
import forms
import time
import datetime
import os
import threading

#-----------------------------------------------------------------------------
# Главная форма
#-----------------------------------------------------------------------------

class MainFrame(forms.MainFrame):
    def __init__(self):
        forms.MainFrame.__init__(self, None)

        s = server.LocalServer()
        s.LoadModels()
        models = s.GetModels()
        s.Start()
        self.server = s

        model = models[0]

        self.m_user_models.Bind(wx.EVT_TREE_SEL_CHANGED,
            self.OnModelActivated)
        self.m_params.Bind(wxpg.EVT_PG_CHANGING,
            self.OnParamChanging)
        self.m_params.Bind(wxpg.EVT_PG_CHANGED,
            self.OnParamChanged)

        self.Bind(wx.EVT_MENU, self.OnTest, id = forms.ID_TEST)
        self.Bind(wx.EVT_MENU, self.OnDuplicate, id = forms.ID_DUPLICATE)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        ov = threading.Thread(target = self.Overseer)
        ov.daemon = 1
        ov.start()

        self.NewProject(model)


    def OnClose(self, event):
        self.server.Stop()
        self.Destroy()

    def Overseer(self):
        try:
            um = self.m_user_models
            cycle_count = 0
            while True:
                wx.MutexGuiEnter()
                print 'cycle {:-8} '.format(cycle_count)
                cycle_count += 1
                item = um.GetRootItem()
                while item.IsOk():
                    data = um.GetPyData(item)
                    if data:
                        jid = data[1]

                        if jid != None and self.server.IsJobChanged(jid):
                            tid     = self.server.GetJobTID(jid)
                            meta    = self.server.GetTaskMeta(tid)
                            t       = os.path.basename(meta['exec'])
                            state   = self.server.GetJobState(jid)
                            um.SetItemText(item, str(state[0]), 1)
                            um.SetItemText(item, '{}: {:%}'.format(t, state[1]), 2)
                            print jid, state

                    item = um.GetNext(item)
                wx.MutexGuiLeave()
                time.sleep(0.1)
        except Exception, e:
            print 'Error in overseer: ', e

    def NewProject(self, project):
        # 1. загрузить спецификации модели
        # 2. создать одну модель по умолчанию
        model   = project
        um      = self.m_user_models
        root    = um.AddRoot('Root')
        data    = task.DataDefinition(model)

        child   = um.AppendItem(root, 'Default')
        jid     = self.server.CreateJob()
        um.SetPyData(child, [data, jid])

    def SelectUserModel(self, model_def, jid):

        def SelectProperty(param_type):
            """
            По указанному имени типа возвращает "свойство" для списка "свойств"

            Смотри руководство пользователя для того, чтобы получить полную
            информацию о всех типах данных, используемых в Opal.
            """
            if param_type == 'bool':
                return wxpg.BoolProperty
            elif param_type == 'int':
                return wxpg.IntProperty
            elif param_type == 'float' or param_type == 'double':
                return wxpg.FloatProperty
            elif param_type == 'string':
                return wxpg.StringProperty
            elif param_type == 'list':
                return wxpg.ArrayStringProperty
            else:
                # очень плохо, если это произошло
                raise KeyError()

        msg = model_def.PackParams()
        pg = self.m_params
        pg.ClearPage(0)
        #pg.Append(wxpg.PropertyCategory('Model properties'))
        for k, v in model_def.params.iteritems():
            p = model_def.DD[k]
            title = p.GetTitle() or k
            prop = SelectProperty(p.GetType())
            pid = pg.Append(prop(title, value = v))
            pg.SetPropertyClientData(pid, k)
            pg.SetPropertyHelpString(pid, p.GetComment())

        pd = model_def.PackParams()
        self.SetStatusText(pd, 0)

    def OnModelActivated(self, event):
        item = event.GetItem()
        data = self.m_user_models.GetPyData(item)
        if data:
            self.SelectUserModel(data[0], data[1])

    def OnParamChanging(self, event):
        #value = event.GetValue()
        #print repr(value)
        #wx.MessageBox(value, 'changing')
        #event.Veto()
        pass

    def OnParamChanged(self, event):
        prop = event.GetProperty()
        if not prop:
            return
        value = prop.GetValue()
        param = prop.GetClientData()
        um = self.m_user_models
        id = um.GetSelection()
        data, jid = um.GetItemPyData(id)
        data[param] = value

    def OnTest(self, event):

        um = self.m_user_models
        id = um.GetSelection()
        data, jid = um.GetItemPyData(id)

        self.server.LaunchJob(jid, data)

    def OnDuplicate(self, event):
        um      = self.m_user_models
        id      = um.GetSelection()
        title   = um.GetItemText(id)
        parent  = um.GetItemParent(id)
        md, jid = um.GetItemPyData(id)
        child   = um.AppendItem(parent, title + ' Copy')
        jid     = self.server.CreateJob()
        um.SetPyData(child, [md.Copy(), jid])
        self.SetStatusText('Copy for "{}" created'.format(title), 0)

    def OnIdle(self, event):
        pass

#-----------------------------------------------------------------------------
# Приложение
#-----------------------------------------------------------------------------

class ThisApp(wx.App):

    def OnInit(self):
        # Создание главного окна
        frame = MainFrame()
        self.SetTopWindow(frame)
        frame.Show(True)
        return True

#-----------------------------------------------------------------------------
# Запуск приложения
#-----------------------------------------------------------------------------

if __name__ == "__main__":
    app = ThisApp(redirect = False)
    app.MainLoop()