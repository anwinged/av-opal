﻿#-------------------------------------------------------------------------------
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
import wx.lib.plot as wxplot
import forms
import time
import datetime
import os
import threading
import re

class ModelData:
    def __init__(self, server, model, parent_data = None):
        # если мы создаем новый набор данных из описания модели
        if isinstance(model, task.DataDescription):
            self.mdef = task.DataDefinition(model, parent_data)
            self.jid  = server.CreateJob() if model.IsExecutable() else None
        # если мы создаем набор данных из другого набора данных
        elif isinstance(model, ModelData):
            self.mdef = model.mdef.Copy()
            self.jid  = server.CreateJob() if model.jid != None else None
        else:
            self.mdef = None
            self.jid  = None

        self.res  = None

class ItemError(Exception):
    pass

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
        self.m_specs.Bind(wx.EVT_TREE_ITEM_ACTIVATED,
            self.OnAddModelToSelected)
        self.m_user_models.Bind(wx.EVT_TREE_ITEM_ACTIVATED,
            self.OnModelProcess)
        self.m_plots.Bind(wx.EVT_TREE_ITEM_ACTIVATED,
            self.OnPlotProcess)


        self.Bind(wx.EVT_MENU, self.OnTest,
            id = forms.ID_TEST)
        self.Bind(wx.EVT_MENU, self.OnAddModelToRoot,
            id = forms.ID_ADD_MODEL_ROOT)
        self.Bind(wx.EVT_MENU, self.OnAddModelToSelected,
            id = forms.ID_ADD_MODEL_SELECTED)
        self.Bind(wx.EVT_MENU, self.OnDuplicate,
            id = forms.ID_DUPLICATE_MODEL)
        self.Bind(wx.EVT_MENU, self.OnDuplicateTree,
            id = forms.ID_DUPLICATE_TREE)
        self.Bind(wx.EVT_MENU, self.OnDeleteModel,
            id = forms.ID_DELETE_MODEL)
        self.Bind(wx.EVT_MENU, self.OnModelProcess,
            id = forms.ID_PROCESS_MODEL)

        self.Bind(wx.EVT_MENU, self.OnShowResult,
            id = forms.ID_SHOW_RESULT)
        self.Bind(wx.EVT_MENU, self.OnShowPlot,
            id = forms.ID_SHOW_PLOT)
        self.Bind(wx.EVT_MENU, self.OnAddPlot,
            id = forms.ID_ADD_PLOT)
        self.Bind(wx.EVT_MENU, self.OnAddLines,
            id = forms.ID_ADD_LINE)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        # если установлен в True, то обработчик состояний работ
        # будет работать вхолостую, чтобы не создать deadlock
        # проблема возникает в том, что при одновременной блокировке
        # GUI и вызова модального диалога, последний весит все приложение напрочь
        # в момент своего закрытия. а так как диалог все равно модальный,
        # форме не обязательно обновляться в тот момент, когда он открыт
        self.do_nothing = False

        ov = threading.Thread(target = self.Overseer)
        ov.daemon = True
        ov.start()

        self.NewProject(model)


    def OnClose(self, event):
        self.server.Stop()
        self.Destroy()

    def Overseer(self):
        """
        Функция-надсмотрщик, которая периодически проверяет состояние
        всех пользовательских моделей, в зависимости от этого изменяет
        состояние окружения, выводит информацию, подгружает результаты
        выполнения работ и др.
        """

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
                time.sleep(0.1)

                # если нужно подождать, то мы подождем
                if self.do_nothing:
                    continue

                wx.MutexGuiEnter()
                try:
                    # print 'cycle{:-8}'.format(cycle_count)
                    cycle_count += 1
                    # просматриваем всю иерархию моделей
                    for item in um:
                        data = um.GetPyData(item)
                        if not data:
                            continue
                        jid = data.jid
                        if jid != None and self.server.IsJobChanged(jid):
                            state, percent, comment = self.server.GetJobState(jid)
                            um.SetItemText(item, StateToStr(state), 1)
                            p = 'Unknown' if percent < 0 else '{:%}'.format(percent)
                            um.SetItemText(item, p, 2)
                            um.SetItemText(item, comment, 3)
                            print 'JID', jid, (state, percent, comment)
                            # завершающие действия по окончанию выполнения работы
                            if state == server.JOB_COMPLETED:
                                # получаем результаты выполнения
                                data.res = self.server.GetJobResult(jid)
                                # если завершившаяся задача в данный момент выделена
                                # то сразу же показываем этот результат
                                if um.IsSelected(item):
                                    self.ShowQuickResult(data.res)
                finally:
                    wx.MutexGuiLeave()
                    pass
        except Exception, e:
            print 'Error in overseer: ', e

    def CheckName(self, name):
        """
        Проверяет имя на уникальность в иерархии пользовательских моделей.
        Возвращает True, если имя уникально, иначе False.
        """
        um = self.m_user_models
        for item in um:
            item_name = um.GetItemText(item)
            if item_name == name:
                return False
        return True

    def GenerateName(self, name):
        """
        На основе переданного имени генерирует новое имя модели таким образом,
        чтобы оно осталось уникальным в рамках существующей иерархии моделей.
        """
        m = re.match(r'^(.+)\s+\d*$', name, re.UNICODE)
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
        root = None
        for i, m in enumerate(ms):
            name = self.GenerateName(m.GetTitle())
            item = um.AppendItem(item, name)
            if not i:
                root = item
            data = ModelData(self.server, m, defparent)
            defparent = data.mdef
            um.SetPyData(item, data)
        if root:
            um.Expand(root)

    def NewProject(self, model):
        """
        Начать новый проект:
        1. Построить дерево спецификаций
        2. Создать одну пользовательскую модель (по умолчанию)
        3. Сделать заготовки для графиков/отчетов/прочего
        """
        # Строим спецификации
        self.BuildSpecs(model)
        # Очищаем окно пользовательских моделей
        # и создаем там одну
        um = self.m_user_models
        um.DeleteAllItems()
        um.AddRoot('root')
        self.AddModelToRoot(model)
        # Создаем корневой элемент для окна с графиками
        self.m_plots.AddRoot('root')

        return True # Project(model)

    def SelectUserModel(self, model_def):

        def SelectProperty(param_type):
            """
            По указанному имени типа возвращает "свойство" для списка "свойств"

            Смотри руководство пользователя для того, чтобы получить полную
            информацию о всех типах данных, используемых в Opal.
            """
            if   param_type == 'bool' or param_type == 'boolean':
                return wxpg.BoolProperty
            elif param_type == 'int':
                return wxpg.IntProperty
            elif param_type == 'float' or param_type == 'double':
                return wxpg.FloatProperty
            elif param_type == 'str' or param_type == 'string':
                return wxpg.StringProperty
            elif param_type == 'list':
                return wxpg.ArrayStringProperty
            else:
                # очень плохо, если это произошло
                raise KeyError()

        msg = model_def.PackParams()
        pg = self.m_params
        pg.ClearPage(0)
        for label, value in model_def.params.iteritems():
            param   = model_def.DD[label]
            title   = param.GetTitle()
            prop    = SelectProperty(param.GetType())
            pid     = pg.Append(prop(title, value = value))
            pg.SetPropertyClientData(pid, label)
            pg.SetPropertyHelpString(pid, param.GetComment())

        self.SetStatusText(model_def.PackParams(), 0)

    def ShowQuickResult(self, result):
        if not result:
            return
        pg = self.m_quick_result
        pg.ClearPage(0)
        for label, param in result.data.iteritems():
            pg.Append(wxpg.StringProperty(label, value = str(param.GetValue())))
        pg.SetSplitterLeft()

    def GetSelectedItem(self, source):
        item = source.GetSelection()
        if not item.IsOk():
            raise ItemError('Invalid item')
        return item

    def GetSelectedData(self, source):
        item = self.GetSelectedItem(source)
        data = source.GetPyData(item)
        if not data:
            raise ItemError('Empty data')
        return data

    def GetSelectedItemData(self, source):
        item = self.GetSelectedItem(source)
        data = source.GetPyData(item)
        if not data:
            raise ItemError('Empty data')
        return (item, data)


    def OnModelActivated(self, event):
        item = event.GetItem()
        data = self.m_user_models.GetPyData(item)
        if data:
            self.SelectUserModel(data.mdef)
            self.ShowQuickResult(data.res)

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
        data  = self.GetSelectedData(self.m_user_models)
        data.mdef[param] = value

    def OnTest(self, event):
        um = self.m_user_models

    def OnAddModelToRoot(self, event):
        model = self.GetSelectedData(self.m_specs)
        self.AddModelToRoot(model)

    def OnAddModelToSelected(self, event):
        """
        Добавляет пользовательскую спецификацию к указанной модели
        """
        # получаем модель, которая будет добавлена к пользовательским
        model = self.GetSelectedData(self.m_specs)
        # получаем пользовательскую модель, к которой хотим присоединить новую
        item, data = self.GetSelectedItemData(self.m_user_models)
        pmdef = data.mdef
        um = self.m_user_models
        # если новая модель может быть присоединена...
        if pmdef.DD == model.parent:
            name     = self.GenerateName(model.GetTitle())
            child    = um.AppendItem(item, name)
            new_data = ModelData(self.server, model, pmdef)
            um.SetPyData(child, new_data)
            um.Expand(item)
        else:
            wx.MessageBox('It\'s impossible to append model', 'Error')

    def OnDuplicate(self, event):
        """
        Обработчик события "дублирование модели"

        Когда модель дублируется, ее параметры копируются в новую модель,
        при неоходимости выделяется слот для работ на сервере.
        Результаты модели-оригинала не копируются.
        """
        um = self.m_user_models
        item, data = self.GetSelectedItemData(self.m_user_models)
        title    = um.GetItemText(item)
        parent   = um.GetItemParent(item)
        child    = um.AppendItem(parent, self.GenerateName(title))
        new_data = ModelData(self.server, data)
        um.SetPyData(child, new_data)
        self.SetStatusText('Copy for "{}" created'.format(title), 0)

    def OnDuplicateTree(self, event):
        pass

    def OnDeleteModel(self, event):
        item, data = self.GetSelectedItemData(self.m_user_models)
        self.server.DeleteJob(data.jid)
        self.m_user_models.Delete(item)

    def OnModelProcess(self, event):
        um = self.m_user_models
        for i in um.GetSelections():
            data = um.GetItemPyData(i)
            self.server.LaunchJob(data.jid, data.mdef)

    def OnShowResult(self, event):
        item, data = self.GetSelectedItemData(self.m_user_models)
        title = self.m_user_models.GetItemText(item)
        title = 'Result for model "{}"'.format(title)
        rframe = ResultFrame(self, title, data.res)
        rframe.Show()

    def GetLines(self):
        """
        Возвращает набор линий, которые пользователь указал для
        построения графика к выбранной модели.

        Линии представляют из себя кортежи из 4х элементов:
        [   внутренний индекс в иерархии моделей,
            данные модели, 
            колонка-х, 
            колонка-у   ]
        """
        um = self.m_user_models
        item, data = self.GetSelectedItemData(um)
        title = um.GetItemText(item)
        if not data.res:
            self.SetStatusText("There is no results in model")
            return []
        f = LineSelectDialog(self, 'Select lines for "{}"'.format(title))
        for index, col in enumerate(data.res.columns):
            row_title = col.GetTitle()
            row_data  = index
            f.Add(row_title, row_data)
        f.SetSelections()

        lines = []
        self.do_nothing = True
        try:
            if f.ShowModal() == wx.ID_OK:
                lines = [ (item, data, x, y) for x, y in f.GetData() ]
        finally:
            self.do_nothing = False

        return lines

    def ShowPlot(self, lines, title = ''):
        if not lines:
            return

        data = []
        for item, moddata, x, y in lines:
            data.append(moddata.res.Zip(x, y))

        p = PlotFrame(self, 'Plot for model "%s"' % title, data)
        p.Show()


    def OnShowPlot(self, event):
        lines = self.GetLines()
        self.ShowPlot(lines)



    def OnAddPlot(self, event):
        root = self.m_plots.GetRootItem()
        child = self.m_plots.AppendItem(root, 'New plot')
        self.m_plots.SetPyData(child, 'plot')

    def OnAddLines(self, event):
        item = self.m_plots.GetSelection()
        data = self.m_plots.GetItemPyData(item)
        if data != 'plot':
            return
        lines = self.GetLines()
        if not lines:
            return
        for line in lines:
            child = self.m_plots.AppendItem(item, 'Line')
            self.m_plots.SetPyData(child, line)

    def OnPlotProcess(self, event):
        item = self.m_plots.GetSelection()
        data = self.m_plots.GetItemPyData(item)
        lines = []
        if data == 'plot':
            child, cookie = self.m_plots.GetFirstChild(item)
            while child.IsOk():
                lines.append(self.m_plots.GetItemPyData(child))
                child, cookie = self.m_plots.GetNextChild(item, cookie)
        else:
            lines = [data]

        self.ShowPlot(lines)

    def OnIdle(self, event):
        pass

#-----------------------------------------------------------------------------
# Форма с результатами выполнения работы
#-----------------------------------------------------------------------------

class ResultFrame(forms.ResultFrame):
    def __init__(self, parent, title, result):
        forms.ResultFrame.__init__(self, parent, title)
        self.result = result
        self.UpdateResults()

    def UpdateResults(self):
        self.scalar.ClearPage(0)
        self.table.ClearGrid()
        if not self.result:
            return

        cols = len(self.result.columns)
        rows = len(self.result.rows)
        self.table.CreateGrid(rows, cols)
        #
        for i, col in enumerate(self.result.columns):
            label = "{} ({} {})".format(col.GetTitle(), col.GetType(), col.GetLabel())
            self.table.SetColLabelValue(i, label)
        #
        for i, row in enumerate(self.result.rows):
            for j, value in enumerate(row):
                self.table.SetCellValue(i, j, str(value))

        self.table.AutoSize()

        pg = self.scalar
        for label, param in self.result.data.iteritems():
            pg.Append(wxpg.StringProperty(label, value = str(param.GetValue())))

#-----------------------------------------------------------------------------
# Форма с выбором наборов значений для построения графика
#-----------------------------------------------------------------------------

class LineSelectDialog(forms.LineSelectDialog):
    def __init__(self, parent, title):
        forms.LineSelectDialog.__init__(self, parent, title)

    def Add(self, title, data = None):
        self.left.Append(title, data)
        self.right.Append(title, data)

    def SetSelections(self):
        if self.left.GetCount():
            self.left.Select(0)
        for i in xrange(1, self.right.GetCount()):
            self.right.Select(i)

    def GetData(self):
        item = self.left.GetSelection()
        x = self.left.GetClientData(item)

        items = self.right.GetSelections()
        ys = [ self.right.GetClientData(i) for i in items ]

        return [ (x, y) for y in ys ]


#-----------------------------------------------------------------------------
# Форма с изображением графика
#-----------------------------------------------------------------------------

class PlotFrame(forms.PlotFrame):
    def __init__(self, parent, title, lines_with_data):
        forms.PlotFrame.__init__(self, parent, title)
        #self.data = data
        data = lines_with_data

        lines = []
        colours = ['red', 'blue', 'green']
        for i, d in enumerate(data):
            lines.append( wxplot.PolyLine(d, colour = colours[i % len(colours)]) )

        graph = wxplot.PlotGraphics(lines)
        self.plot.Draw(graph)

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