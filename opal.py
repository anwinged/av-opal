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
import re

#-----------------------------------------------------------------------------
# Главная форма
#-----------------------------------------------------------------------------

class MainFrame(forms.MainFrame):
    def __init__(self):
        forms.MainFrame.__init__(self, None)

        self.name_id = 1

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
        self.Bind(wx.EVT_MENU, self.OnAddModelToRoot,
            id = forms.ID_ADD_MODEL_ROOT)
        self.Bind(wx.EVT_MENU, self.OnAddModelToSelected,
            id = forms.ID_ADD_MODEL_SELECTED)
        self.Bind(wx.EVT_MENU, self.OnDuplicate,
            id = forms.ID_DUPLICATE_MODEL)
        self.Bind(wx.EVT_MENU, self.OnModelProcess,
            id = forms.ID_PROCESS_MODEL)

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

        def StateToStr(state):
            if   state == server.JOB_READY:
                return 'Ready'
            elif state == server.JOB_RUNNING:
                return 'Running'
            elif state == server.JOB_STOPPED:
                return 'Stopped'
            elif state == server.JOB_COMPLETED:
                return 'Completed'
            else:
                return 'Unknown'

        try:
            um = self.m_user_models
            cycle_count = 0
            while True:
                wx.MutexGuiEnter()
                print 'cycle{:-8}'.format(cycle_count)
                cycle_count += 1
                item = um.GetRootItem()
                while item.IsOk():
                    data = um.GetPyData(item)
                    if data:
                        jid = data[1]
                        if jid != None and self.server.IsJobChanged(jid):
                            state = self.server.GetJobState(jid)
                            um.SetItemText(item, StateToStr(state[0]), 1)
                            p = state[1]
                            p = 'Unknown' if p < 0 else '{:%}'.format(p)
                            um.SetItemText(item, p, 2)
                            um.SetItemText(item, state[2], 3)
                            print jid, state

                    item = um.GetNext(item)
                wx.MutexGuiLeave()
                time.sleep(0.2)
        except Exception, e:
            print 'Error in overseer: ', e

    def CheckName(self, name):
        """
        Проверяет имя на уникальность в иерархии пользовательских моделей.
        Возвращает True, если имя уникально, иначе False.
        """
        um = self.m_user_models
        item = um.GetRootItem()
        while item.IsOk():
            item_name = um.GetItemText(item)
            if item_name == name:
                return False
            item = um.GetNext(item)
        return True

    def GenerateName(self, name):
        """
        На основе переданного имени генерирует новое имя модели таким образом,
        чтобы оно осталось уникальным в рамках существующей иерархии моделей.
        """
        m = re.match(r'(.+)\s+\d*', name)
        basename = m.group(1) if m else name
        while True:
            name = basename + ' ' + str(self.name_id)
            if self.CheckName(name):
                return name
            self.name_id += 1

    def BuildSpecs(self, model):
        """
        Выстраивает иерархию спецификаций для выбранной модели
        """
        def DoItem(item, model):
            sp.SetPyData(item, model)
            for spec in model.GetSpecs():
                child = sp.AppendItem(item, spec.GetTitle())
                DoItem(child, spec)

        sp = self.m_specs
        sp.DeleteAllItems()
        root = sp.AddRoot(model.GetTitle())
        DoItem(root, model)
        sp.ExpandAll()
        sp.SortChildren(root)

    def AddModelToRoot(self, model):
        """
        Добавляет пользовательскую модель или спецификацию
        в корень дерева моделей.
        """

        ms = []
        while model:
            ms.append(model)
            model = model.GetParent()
        ms.reverse()
        # ms: [root-model, child, child-of-child1, ..., model]

        um = self.m_user_models
        item = um.GetRootItem()
        defparent = None
        for m in ms:
            name = self.GenerateName(m.GetTitle())
            item = um.AppendItem(item, name)
            data = task.DataDefinition(m, defparent)
            defparent = data
            jid  = self.server.CreateJob() if m.IsExecutable() else None
            um.SetPyData(item, [data, jid])

    def NewProject(self, model):
        # 1. загрузить спецификации модели
        # 2. создать одну модель по умолчанию

        self.BuildSpecs(model)

        um = self.m_user_models
        um.DeleteAllItems()
        um.AddRoot('Root')

        self.AddModelToRoot(model)

        return True # Project(model)

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

    def OnAddModelToRoot(self, event):
        item = self.m_specs.GetSelection()
        if not item.IsOk():
            return
        print self.m_specs.GetItemText(item)
        model = self.m_specs.GetPyData(item)
        self.AddModelToRoot(model)

    def OnAddModelToSelected(self, event):
        """
        Добавляет пользовательскую спецификацию к указанной модели или в уже
        существующую иерархию спецификаций.
        """
        item = self.m_specs.GetSelection()
        if not item.IsOk():
            return
        model = self.m_specs.GetPyData(item)

        um = self.m_user_models
        item = um.GetSelection()
        if not item.IsOk():
            return

        pmdef, _ = um.GetPyData(item)

        if pmdef.DD == model.parent:
            modeldef = task.DataDefinition(model, pmdef)
            name = self.GenerateName(model.GetTitle())
            item = um.AppendItem(item, name)
            jid  = self.server.CreateJob() if model.IsExecutable() else None
            um.SetPyData(item, [modeldef, jid])
        else:
            wx.MessageBox('It\'s impossible to append model', 'Error')

    def OnDuplicate(self, event):
        um      = self.m_user_models
        id      = um.GetSelection()
        title   = um.GetItemText(id)
        parent  = um.GetItemParent(id)
        md, jid = um.GetItemPyData(id)

        child   = um.AppendItem(parent, self.GenerateName(title))
        jid     = self.server.CreateJob()
        um.SetPyData(child, [md.Copy(), jid])
        self.SetStatusText('Copy for "{}" created'.format(title), 0)

    def OnModelProcess(self, event):
        um = self.m_user_models
        for i in um.GetSelections():
            data, jid = um.GetItemPyData(i)
            self.server.LaunchJob(jid, data)

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