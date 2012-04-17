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

#-----------------------------------------------------------------------------
# Главная форма
#-----------------------------------------------------------------------------

class MainFrame(forms.MainFrame):
    def __init__(self):
        forms.MainFrame.__init__(self, None)

        s = server.LocalServer()
        s.LoadTasksDescriptions()
        ds = s.GetTasksDescriptions()
        models = []
        for d in ds:
            models.extend(d.GetModelsDescriptions())

        model = models[0]

        self.m_user_models.Bind(wx.EVT_TREE_ITEM_ACTIVATED,
            self.OnModelActivated)
        self.m_params.Bind(wxpg.EVT_PG_CHANGING,
            self.OnParamChanging)

        self.Bind(wx.EVT_MENU, self.OnTest, id = forms.ID_TEST)
        self.Bind(wx.EVT_MENU, self.OnDuplicate, id = forms.ID_DUPLICATE)

        self.m_params.AddPage('fp')

        self.NewProject(model)

    def NewProject(self, project):
        # 1. загрузить спецификации модели
        # 2. создать одну модель по умолчанию
        model   = project
        um      = self.m_user_models
        root    = um.AddRoot('')
        data    = task.DataDefinition(model)

        child   = um.AppendItem(root, u'Обычная')
        um.SetPyData(child, data)

    def SelectUserModel(self, model_def):
        msg = model_def.PackParams()
        pg = self.m_params
        pg.ClearPage(0)
        #pg.Append(wxpg.PropertyCategory('Model properties'))
        for k, v in model_def.params.iteritems():
            p = model_def.DD[k]
            title = p.GetTitle() or k
            pid = pg.Append(wxpg.StringProperty(title, value=str(v)))
            pg.SetPropertyClientData(pid, k)
            pg.SetPropertyHelpString(pid, p.GetComment())

    def OnModelActivated(self, event):
        item = event.GetItem()
        data = self.m_user_models.GetPyData(item)
        self.SelectUserModel(data)

    def OnParamChanging(self, event):
        value = event.GetValue()
        print repr(value)
        #wx.MessageBox(value, 'changing')
        #event.Veto()

    def OnTest(self, event):
        um = self.m_user_models
        id = um.GetSelection()
        md = um.GetItemPyData(id)
        wx.MessageBox(md.PackParams())
        md.Flush()
        #wx.MessageBox('test')

    def OnDuplicate(self, event):
        um = self.m_user_models
        id = um.GetSelection()
        title = um.GetItemText(id)
        parent = um.GetItemParent(id)
        md = um.GetItemPyData(id)
        child = um.AppendItem(parent, title + ' Copy')
        um.SetPyData(child, md.Copy())



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