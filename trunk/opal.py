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
import forms
wxpg = forms.wxpg
wxplot = forms.wxplot   
from wx.lib.embeddedimage import PyEmbeddedImage

import time
import threading
import re
import json
import zlib
from pprint import pprint

# состояния модели, унаследованные от состояния задачи
MODEL_READY = server.JOB_READY
MODEL_RUNNING = server.JOB_RUNNING
MODEL_STOPPED = server.JOB_STOPPED
MODEL_COMPLETED = server.JOB_COMPLETED
# собственные состояния модели
MODEL_NO_EXEC = 101

# --------------------------------------------------------------------------
# Данные о пользовательской модели
# --------------------------------------------------------------------------

class ModelData:
    def __init__(self, server, model, parent_data = None):
        # если мы создаем новый набор данных из описания модели
        if isinstance(model, task.DataDescription):
            self.mdef = task.DataDefinition(model, parent_data)
            self.jid = server.CreateJob() if model.IsExecutable() else None
        # если мы создаем набор данных из другого набора данных
        elif isinstance(model, ModelData):
            self.mdef = model.mdef.Copy()
            self.jid = server.CreateJob() if model.jid else None
        else:
            self.mdef = None
            self.jid = None

        assert self.mdef

        self.res  = None            # результаты выполнения работы
        if self.jid:
            self.state = MODEL_READY    # состояние модели
        else:
            self.state = MODEL_NO_EXEC  # состояние модели

# --------------------------------------------------------------------------
# Данные о линии в графике
# --------------------------------------------------------------------------

LINE_CURVE     = 1
LINE_MARKER    = 2
LINE_HISTOGRAM = 3

class LineData:
    """
    Данные одной линии для графика

    Предназначен для использования совместно с графическим компонентом,
    поэтому не имеет собственного значения названия. Вместо этого
    название берется из графического компонента.
    """
    def __init__(self, ums_ptr, plots_ptr,
        type, columns, colour = None, style = None):

        self.ums_ptr = ums_ptr      # (ptr, item) указатель на компонент с моделями
                                    # и индекс в этом компоненте
        self.plots_ptr = plots_ptr  # (ptr, item) указатель на компонент с графиками
                                    # и индекс в этом компоненте

        self.type = type            # тип графика
        self.columns = columns      # пара (x, y)
        self.colour = colour        # цвет: если не задан выбирается из списка
        self.style = style          # стиль: если не задан, еспользуется по умолчанию

    def GetModelTitle(self):
        container, item = self.ums_ptr
        return container.GetItemText(item)

    def GetTitle(self):
        # если есть указатель на компонент с графиками,
        # извлекаем оттуда название
        if self.plots_ptr:
            container, item = self.plots_ptr
            return container.GetItemText(item)
        # иначе формируем название на основе имени модели и
        # имен выбранных столбцов
        else:
            container, item = self.ums_ptr
            title = container.GetItemText(item)
            data = container.GetPyData(item)
            assert data.res # если результата нет, то а-та-та
            colx, coly = self.columns
            title_x = data.res.columns[colx].GetTitle()
            title_y = data.res.columns[coly].GetTitle()
            return "{}: {}({})".format(title, title_y, title_x)

    def GetPoints(self):
        container, item = self.ums_ptr
        data = container.GetPyData(item)
        assert data.res # если результата нет, то а-та-та
        return data.res.Zip(*self.columns)

# --------------------------------------------------------------------------
# Ошибки доступа к элементам в контейнерах
# --------------------------------------------------------------------------

class ItemError(Exception):
    pass

#-----------------------------------------------------------------------------
# Главная форма
#-----------------------------------------------------------------------------

class MainFrame(forms.MainFrame):
    def __init__(self):
        forms.MainFrame.__init__(self, None)

        self.model = None
        self.name_id = 1

        s = server.LocalServer()
        s.LoadModels()
        self.models = s.GetModels()
        s.Start()
        self.server = s

        # События компонентов

        self.m_user_models.Bind(wx.EVT_TREE_SEL_CHANGED,
            self.OnModelSelected)
        self.m_user_models.Bind(wx.EVT_TREE_DELETE_ITEM,
            self.OnDeleteModelsItem)
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
        self.m_plots.Bind(wx.EVT_CHAR,
            self.OnPlotsKeyPressed)

        # События меню

        self.Bind(wx.EVT_MENU, self.OnNewProject,
            id = forms.ID_NEW)
        self.Bind(wx.EVT_MENU, self.OnOpenProject,
            id = forms.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnSaveProject,
            id = forms.ID_SAVE)

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
        self.Bind(wx.EVT_MENU, self.OnModelStop,
            id = forms.ID_STOP_MODEL)

        self.Bind(wx.EVT_MENU, self.OnShowResult,
            id = forms.ID_SHOW_RESULT)

        self.Bind(wx.EVT_MENU, self.OnQuickShowPlot,
            id = forms.ID_SHOW_PLOT)
        self.Bind(wx.EVT_MENU, self.OnAddPlot,
            id = forms.ID_ADD_PLOT)
        self.Bind(wx.EVT_MENU, self.OnAddCurves,
            id = forms.ID_ADD_CURVES)
        self.Bind(wx.EVT_MENU, self.OnAddMarkers,
            id = forms.ID_ADD_MARKERS)

        self.Bind(wx.EVT_MENU, self.OnAbout,
            id = forms.ID_ABOUT)

        # События приложения

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

        #   self.NewProject(self.models[0])

    # Функции приложения и обработки сервера

    def OnClose(self, event):
        self.server.Stop()
        self.Destroy()

    def OnAbout(self, event):
        self.do_nothing = True
        forms.AboutDialog(self).ShowModal()
        self.do_nothing = False

    def OnIdle(self, event):
        pass

    def Overseer(self):
        """
        Функция-надсмотрщик, которая периодически проверяет состояние
        всех пользовательских моделей, в зависимости от этого изменяет
        состояние окружения, выводит информацию, подгружает результаты
        выполнения работ и др.
        """
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
                        if jid and self.server.IsJobChanged(jid):
                            # таким образом, тут мы обрабатываем новое состояние
                            # работы (модели)

                            state, percent, comment = self.server.GetJobState(jid)

                            data.state = state
                            self.SetModelState(item, data.state)

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

    def item_protector(func):
        """
        Защитный механизм, который ловит исключения при неправильном
        обращении к элементам деревьев (компоненты TreeCtrl, TreeListCtrl)

        Возвращает None, если было поймано исключение.
        Использование с функциями, которые не являются обработчиками событий
        не желательно
        """
        def Checker(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ItemError:
                print 'Oops'

        return Checker

    # Функции создания модели, сохранения и загрузки

    def BuildSpecs(self, model):
        """
        Выстраивает иерархию спецификаций для выбранной модели
        """
        def DoItem(item, model):
            sp.SetPyData(item, model)
            for label, spec in model.GetSpecs().iteritems():
                child = sp.AppendItem(item, spec.GetTitle())
                DoItem(child, spec)

        sp = self.m_specs
        sp.DeleteAllItems()
        root = sp.AddRoot(model.GetTitle())
        DoItem(root, model)
        sp.ExpandAll()
        sp.SortChildren(root)

    def NewProject(self, model, create_default = True):
        """
        Начать новый проект:
        0. Очичтить все компоненты
        1. Построить дерево спецификаций
        2. Создать одну пользовательскую модель (по умолчанию)
        3. Сделать заготовки для графиков/отчетов/прочего
        """
        self.m_specs.DeleteAllItems()
        self.m_user_models.DeleteAllItems()
        self.m_params.Clear()
        self.m_quick_result.Clear()
        self.m_plots.DeleteAllItems()
        # фиксируем выбранную модель
        self.model = model
        # Строим спецификации
        self.BuildSpecs(model)
        # Очищаем окно пользовательских моделей
        # и создаем там одну
        um = self.m_user_models
        um.DeleteAllItems()
        um.AddRoot('root')
        if create_default:
            self.AddModelToRoot(model)
        # Создаем корневой элемент для окна с графиками
        self.m_plots.AddRoot('root')

        self.SetStatusText('Model "{}" selected'.format(model.GetTitle()), 0)

        return True # Project(model)

    def OnNewProject(self, event):
        self.do_nothing = True
        f = SelectModelDialog(self, self.models)
        if f.ShowModal() == wx.ID_OK:
            model = f.GetSelectedModel()
            if model:
                self.NewProject(model)

        self.do_nothing = False

    def OnOpenProject(self, event):

        def WalkModels(source, root, models, model_def = None):
            # for имя-модели, параметры-модели
            for mname, value in source.iteritems():
                label = value['model']

                if label not in models:
                    raise KeyError, 'no "{}"'.format(label)

                data = ModelData(self.server, models[label], model_def)
                data.mdef.params = value['data']
                data.state = value['state']
                if 'result' in value:
                    data.res = task.ResultData(value['result'])
                # тут надо проверить все добавленные параметры

                item = self.AddModel(root, mname, data)
                model_items[mname] = item

                WalkModels(value['um'], item, models[label].GetSpecs(), data)

        def WalkPlots(source, root):
            for plot in source:
                item = self.m_plots.AppendItem(root, plot[0])
                self.m_plots.SetPyData(item, 'plot')
                self.m_plots.SetItemImage(item, self.icons.porg)
                for line in plot[1]:
                    model_label = line['model']
                    data = LineData(
                        ums_ptr = (um, model_items[model_label]),
                        plots_ptr = None,
                        type = line['type'],
                        columns = (line['colx'], line['coly'])
                    )
                    self.AddLine(item, line['title'], data)

        try:
            wx.BeginBusyCursor()
            self.do_nothing = True

            selector = wx.FileDialog(
                self,
                'Select file to load project',
                '',
                '',
                'Opal files (*.opl)|*.opl|Text files (*.txt)|*.txt',
                wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

            if selector.ShowModal() == wx.ID_OK:

                filename = selector.GetPath()
                data = {}

                if selector.GetFilterIndex() == 0:
                    with open(filename, 'rb') as f:
                        data = json.loads(zlib.decompress(f.read()))
                else:
                    with open(filename, 'r') as f:
                        data = json.loads(f.read())
                        

                tid = data['tid']
                model_label = data['model']
                model = self.server.CheckModel(tid, model_label) 
                if not model:
                    raise ValueError

                self.NewProject(model, False)

                um = self.m_user_models
                model_items = {}

                root = um.GetRootItem()
                WalkModels(data['um'], root, {model.GetLabel(): model})
                um.ExpandAll(root)

                root = self.m_plots.GetRootItem()
                WalkPlots(data['plots'], root)
                self.m_plots.ExpandAll()

        except Exception, e:
            wx.MessageBox("Can't load saved file", 'Error', wx.ICON_ERROR | wx.OK)
            print 'Oops', type(e), e
        finally:
            wx.EndBusyCursor()
            self.do_nothing = False

    def OnSaveProject(self, event):

        def WalkModels(item, dest):
            """
            Сохраняем информацию о каждой модели
            """
            if item != um.GetRootItem():
                data = um.GetPyData(item)
                title = um.GetItemText(item)
                mdef = data.mdef
                dest[title] = {
                    'model': mdef.DD.GetLabel(),
                    'data': mdef.params,
                    'um': {},
                    'state': data.state,
                }
                if data.res:
                    dest[title]['result'] = data.res.DumpData()
                dest = dest[title]['um']

            child, _ = um.GetFirstChild(item)
            while child.IsOk():
                WalkModels(child, dest)
                child = um.GetNextSibling(child)

        def WalkPlots(root, dest):
            """
            Сохраняем информацию о каждом графике
            """
            # по всеи элементам первого уровня
            item1, _ = self.m_plots.GetFirstChild(root)
            while item1.IsOk():
                # по всем элементам второго уровня
                item2, _ = self.m_plots.GetFirstChild(item1)
                lines = []
                while item2.IsOk():
                    line = self.m_plots.GetPyData(item2)
                    data = {
                        'title': self.m_plots.GetItemText(item2),
                        'colx': line.columns[0],
                        'coly': line.columns[1],
                        'model': line.GetModelTitle(),
                        'type': line.type,
                    }
                    lines.append(data)
                    item2 = self.m_plots.GetNextSibling(item2)
                title = self.m_plots.GetItemText(item1)
                dest.append([title, lines])
                item1 = self.m_plots.GetNextSibling(item1)

        try:
            wx.BeginBusyCursor()
            self.do_nothing = True

            selector = wx.FileDialog(
                self,
                'Select file to save project',
                '',
                self.model.GetTitle() + ' project',
                'Opal files (*.opl)|*.opl|Text files (*.txt)|*.txt',
                wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

            if selector.ShowModal() == wx.ID_OK:

                data = {}

                data['tid'] = self.model.GetTaskId()
                data['model'] = self.model.GetLabel()

                um = self.m_user_models
                data['um'] = {}
                WalkModels(um.GetRootItem(), data['um'])

                data['plots'] = []
                WalkPlots(self.m_plots.GetRootItem(), data['plots'])

                # pprint(data)
                dump = json.dumps(data, indent = 2)

                filename = selector.GetPath()
                # сохраняем в упакованный бинарный формат
                if selector.GetFilterIndex() == 0:
                    with open(filename, 'wb') as f:
                        f.write(zlib.compress(dump, 9))

                # сохраняем в простой текстовый формат
                else:
                    with open(filename, 'w') as f:
                        f.write(dump)
                        
        except Exception as e:
            wx.MessageBox("Can't save the project", 'Error', wx.ICON_ERROR | wx.OK)
            print e
        finally:
            wx.EndBusyCursor()
            self.do_nothing = False

    # Функции непосредственной работы с моделями:
    # создание, изменение, дублирование и прочее

    # Работа с именами моделей

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

    # Добавление новых моделей

    def SetModelState(self, item, state):
        if state == MODEL_READY:
            icon = self.icons.mready
            text = 'Ready'

        elif state == MODEL_RUNNING:
            icon = self.icons.mrun
            text = 'Running'

        elif state == MODEL_COMPLETED:
            icon = self.icons.mcomplete
            text = 'Completed'

        elif state == MODEL_STOPPED:
            icon = self.icons.mstopped
            text = 'Stopped'

        else:
            icon = self.icons.mnoexec
            text = 'No executable'

        self.m_user_models.SetItemImage(item, icon)
        self.m_user_models.SetItemText(item, text, 1)

    def AddModel(self, item, title, model_data):
        """
        Добавляет модель к указанной,
        устанавливает имя, данные, состояние, иконку
        """
        um = self.m_user_models
        item = um.AppendItem(item, title)
        um.SetPyData(item, model_data)
        self.SetModelState(item, model_data.state)
        return item

    def AddModelToRoot(self, model):
        """
        Добавляет пользовательскую модель или спецификацию
        в корень дерева моделей.
        """
        # строим список моделей, которые будут добавлены
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
            if not i:
                root = item
            data = ModelData(self.server, m, defparent)
            item = self.AddModel(item, name, data)
            defparent = data.mdef
        if root:
            um.Expand(root)
        um.SelectItem(item)
        um.SetFocus()

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
            new_data = ModelData(self.server, model, pmdef)
            child = self.AddModel(item, name, new_data)
            um.SetFocus()
            um.Expand(item)
            um.SelectItem(child)
        else:
            wx.MessageBox('It\'s impossible to append model', 'Error')

    # Реакция на выбор модели

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

        pg = self.m_params
        pg.Clear()
        for label, value in model_def.params.iteritems():
            param   = model_def.DD[label]
            title   = param.GetTitle()
            prop    = SelectProperty(param.GetType())
            pid     = pg.Append(prop(title, value = value))
            pg.SetPropertyClientData(pid, label)
            pg.SetPropertyHelpString(pid, param.GetComment())

    def ShowQuickResult(self, result):
        if not result:
            return
        pg = self.m_quick_result
        pg.Clear()
        for label, param in result.data.iteritems():
            pg.Append(wxpg.StringProperty(label, value = str(param.GetValue())))
        pg.SetSplitterLeft()

    def OnModelSelected(self, event):
        item = event.GetItem()
        data = self.m_user_models.GetPyData(item)
        if data:
            self.SelectUserModel(data.mdef)
            self.ShowQuickResult(data.res)

    # Изменение параметров модели

    def OnParamChanging(self, event):
        #value = event.GetValue()
        #print repr(value)
        #wx.MessageBox(value, 'changing')
        #event.Veto()
        pass

    def OnParamChanged(self, event):

        def Walk(item):
            data = um.GetPyData(item)
            if data.state != MODEL_NO_EXEC:
                data.state = MODEL_READY
                self.SetModelState(item, data.state)

            child, _ = um.GetFirstChild(item)
            while child.IsOk():
                Walk(child)
                child = um.GetNextSibling(child)

        um = self.m_user_models
        prop = event.GetProperty()
        if not prop:
            return
        value = prop.GetValue()
        param = prop.GetClientData()
        item, data = self.GetSelectedItemData(um)
        data.mdef[param] = value
        # так как значение параметра изменилось,
        # то все субмодели должны быть пересчитаны
        Walk(item)

    def OnTest(self, event):
        pass

    # Получение данных выбранной модели

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

    # Дублирование модели

    def Duplicate(self, item_src, item_dst):
        um = self.m_user_models
        data     = um.GetPyData(item_src)
        title    = um.GetItemText(item_src)
        new_data = ModelData(self.server, data)
        um.SetItemText(item_dst, self.GenerateName(title))
        um.SetPyData(item_dst, new_data)
        self.SetModelState(item_dst, new_data.state)

    def OnDuplicate(self, event):
        """
        Обработчик события "дублирование модели"

        Когда модель дублируется, ее параметры копируются в новую модель,
        при неоходимости выделяется слот для работ на сервере.
        Результаты модели-оригинала не копируются.
        """
        um = self.m_user_models
        item_src = self.GetSelectedItem(um)
        parent   = um.GetItemParent(item_src)
        item_dst = um.AppendItem(parent, 'new-item')
        self.Duplicate(item_src, item_dst)
        # self.SetStatusText('Copy for "{}" created'.format(title), 0)

    def OnDuplicateTree(self, event):

        def Walk(item_src, item_dst):
            self.Duplicate(item_src, item_dst)

            child_src, _ = um.GetFirstChild(item_src)
            while child_src.IsOk():
                child_dst = um.AppendItem(item_dst, 'new-item')
                Walk(child_src, child_dst)
                child_src = um.GetNextSibling(child_src)

        um = self.m_user_models
        item_src = self.GetSelectedItem(um)
        parent   = um.GetItemParent(item_src)
        item_dst = um.AppendItem(parent, 'new-item')
        Walk(item_src, item_dst)
        um.Expand(item_dst)

    # Удаление модели

    def OnDeleteModelsItem(self, event):
        item = event.GetItem()
        data = self.m_user_models.GetPyData(item)
        if data:
            self.server.DeleteJob(data.jid)

    def OnDeleteModel(self, event):
        item = self.GetSelectedItem(self.m_user_models)
        self.m_user_models.Delete(item)

    # Функции запуска модели на выполнение и управления очередью

    def OnModelProcess(self, event):
        um = self.m_user_models
        for i in um.GetSelections():
            data = um.GetItemPyData(i)
            if data.jid:
                self.server.LaunchJob(data.jid, data.mdef)

    def OnModelStop(self, event):
        um = self.m_user_models
        for i in um.GetSelections():
            data = um.GetItemPyData(i)
            if data.jid:
                self.server.StopJob(data.jid)

    # Функции управления таблицами и отчетами

    def OnShowResult(self, event):
        item, data = self.GetSelectedItemData(self.m_user_models)
        title = self.m_user_models.GetItemText(item)
        title = 'Result for model "{}"'.format(title)
        rframe = ResultFrame(self, title, data.res)
        rframe.Show()

    # Функции управления графиками

    def OnAddPlot(self, event):
        root = self.m_plots.GetRootItem()
        child = self.m_plots.AppendItem(root, 'New plot')
        self.m_plots.SetPyData(child, 'plot')
        self.m_plots.SetItemImage(child, self.icons.porg)
        self.m_plots.SelectItem(child)

    def GetLines(self, line_type):
        """
        Возвращает набор линий, которые пользователь указал для
        построения графика к выбранной модели.

        Возвращает список экземпляров LineData
        """

        def CreateLineSelectDialog(parent, title, model_data):
            f = LineSelectDialog(parent, title)
            for index, col in enumerate(model_data.res.columns):
                row_title = col.GetTitle()
                row_data  = index
                f.Add(row_title, row_data)
            f.SetSelections()
            return f

        def GetLinesFromUser(select_dialog):
            lines = []
            self.do_nothing = True
            try:
                if select_dialog.ShowModal() == wx.ID_OK:
                    for xy in select_dialog.GetLineColumns():
                        line_data = LineData(
                            (um, item), # указатель на модель
                            None,       # указатель на график
                            line_type, xy) # тип линии, колонки и прочее
                        lines.append(line_data)
                f.Destroy()
            finally:
                self.do_nothing = False
            return lines

        um = self.m_user_models
        lines = []
        items = um.GetSelections()
        count = len(items)
        for index, item in enumerate(items, 1):
            data = um.GetPyData(item)
            title = um.GetItemText(item)

            msg = 'Line(s) for "{}" ({}/{})'.format(title, index, count)

            if not data.res:
                wx.MessageBox(
                    'There is no any result data for model!', 
                    msg, wx.OK | wx.ICON_EXCLAMATION)
            else:
                f = CreateLineSelectDialog(self, msg, data)
                lines += GetLinesFromUser(f)

        return lines

    @item_protector
    def AddLines(self, line_type):
        """
        Добавляет линии в выделенный график
        (компонента с графиками m_plots)
        """
        # получаем указатель на индекс и данные элемента, который выделен
        item, data = self.GetSelectedItemData(self.m_plots)
        # если это на контейнер с графиками, то выходим
        if data != 'plot':
            return
        # получаем указанные пользователем линии
        lines = self.GetLines(line_type)
        for line in lines:
            self.AddLine(item, line.GetTitle(), line)

    def AddLine(self, root, title, line_data):
        item = self.m_plots.AppendItem(root, title)
        self.m_plots.SetPyData(item, line_data)
        line_data.plots_ptr = (self.m_plots, item)
        if line_data.type == LINE_MARKER:
            self.m_plots.SetItemImage(item, self.icons.pmarker)
        else:
            self.m_plots.SetItemImage(item, self.icons.pline)
        self.m_plots.Expand(root)
        return item

    def OnAddCurves(self, event):
        self.AddLines(LINE_CURVE)

    def OnAddMarkers(self, event):
        self.AddLines(LINE_MARKER)

    def ShowPlot(self, lines, plot_title = ''):
        if lines:
            p = PlotFrame(self, 'Plot', lines)
            wx.FutureCall(20, p.Show)
            # p.Show()

    def OnQuickShowPlot(self, event):
        lines = self.GetLines(LINE_CURVE)
        um = self.m_user_models
        item = self.GetSelectedItem(um)
        title = um.GetItemText(item)
        self.ShowPlot(lines, title)

    def OnPlotProcess(self, event):
        item = self.m_plots.GetSelection()
        data = self.m_plots.GetItemPyData(item)
        lines = []
        if data == 'plot':
            child, cookie = self.m_plots.GetFirstChild(item)
            while child.IsOk():
                title = self.m_plots.GetItemText(child)
                line_data = self.m_plots.GetItemPyData(child)
                line_data.title = title
                lines.append(line_data)
                child, cookie = self.m_plots.GetNextChild(item, cookie)
        else:
            title = self.m_plots.GetItemText(item)
            data.title = title
            lines = [ data ] 

        self.ShowPlot(lines)

    def OnPlotsKeyPressed(self, event):
        keycode = event.GetKeyCode()
        item = self.GetSelectedItem(self.m_plots)
        if keycode == wx.WXK_DELETE:
            self.m_plots.Delete(item)
        event.Skip()

#-----------------------------------------------------------------------------
# Форма с выбором модели из представленного списка
#-----------------------------------------------------------------------------

class SelectModelDialog(forms.SelectModelDialog):
    def __init__(self, parent, models):
        forms.SelectModelDialog.__init__(self, parent)

        self.ilist = wx.ImageList(32, 32)
        self.mlist.SetImageList(self.ilist, wx.IMAGE_LIST_NORMAL)
        self.data_list = {}

        for model in models:
            item = wx.ListItem()
            item.SetText(model.GetTitle())
            #item.Data = model
            img_data = model.GetImage()
            if img_data:
                img = PyEmbeddedImage(img_data)
                index = self.ilist.Add(img.GetBitmap())
                item.SetImage(index)
            index = self.mlist.InsertItem(item)
            self.data_list[index] = model

    def GetSelectedModel(self):
        index = self.mlist.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        return self.data_list.get(index)


#-----------------------------------------------------------------------------
# Форма с результатами выполнения работы
#-----------------------------------------------------------------------------

class ResultFrame(forms.ResultFrame):
    def __init__(self, parent, title, result):
        forms.ResultFrame.__init__(self, parent, title)
        self.result = result
        self.UpdateResults()

        self.Bind(wx.EVT_MENU, self.OnExportToCSV,
            id = forms.ID_EXPORT_CSV)

    def UpdateResults(self):
        self.scalar.Clear()
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
        data = self.result.data
        if not data:
            pg.Show(0)
        else:
            for label, param in data.iteritems():
                pg.Append(wxpg.StringProperty(label, 
                    value = str(param.GetValue())))

    def OnExportToCSV(self, event):

        if not self.result or not self.result.table:
            return

        text_file = wx.FileSelector('Save table to CSV',
            default_filename = 'table.csv',
            wildcard = 'PNG files (*.csv)|*.csv|Text files (*.txt)|*.txt',
            flags = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if not text_file:
            return

        tl = self.table.GetSelectionBlockTopLeft() # [(t, l)]
        br = self.table.GetSelectionBlockBottomRight() # [(b, r)]

        if not tl:
            tl = (0, 0)
        else:
            tl = tl[0]

        if not br:
            br = (len(self.result.rows), len(self.result.columns))
        else:
            x, y = br[0]
            br = x + 1, y + 1

        with open(text_file, 'w') as f:
            for i in xrange(tl[0], br[0]):
                s = []
                for j in xrange(tl[1], br[1]):
                    s.append(repr(self.result.GetCell(i, j)))
                f.write('; '.join(s) + '\n')

#-----------------------------------------------------------------------------
# Форма с выбором наборов значений для построения графика
#-----------------------------------------------------------------------------

class LineSelectDialog(forms.LineSelectDialog):
    def __init__(self, parent, title):
        forms.LineSelectDialog.__init__(self, parent, title)

    def Add(self, title, data):
        self.left.Append(title, data)
        self.right.Append(title, data)

    def SetSelections(self):
        """
        Выделяет первую строку в левом столбце колонок
        и все, кроме первой, во втором.

        Таким образом по умолчанию предлагается построить зависимость
        каждого значения от первого. Это логично, поскольку первым
        обычно идет независимый параметр.
        """
        # выделяем первую строку слева
        # (первый столбец результата)
        if self.left.GetCount():
            self.left.Select(0)
        # выделяем все, кроме первой, строки справа
        # (второй столбец результата)
        for i in xrange(1, self.right.GetCount()):
            self.right.Select(i)

    def GetLineColumns(self):
        """
        Возвращает список пар колонок, которые были выбраны
        """
        item = self.left.GetSelection()
        x = self.left.GetClientData(item)

        items = self.right.GetSelections()
        ys = [ self.right.GetClientData(i) for i in items ]

        return [ (x, y) for y in ys ]

#-----------------------------------------------------------------------------
# Форма с изображением графика
#-----------------------------------------------------------------------------

class PlotFrame(forms.PlotFrame):
    def __init__(self, parent, title, lines):
        forms.PlotFrame.__init__(self, parent, title)
        self.lines = lines      # список объектор LineData

        self.Bind(wx.EVT_MENU, self.OnSaveImage,
            id = forms.ID_SAVE_PLOT)

        colours = ['red', 'blue', 'green', 'magenta', 'purple', 'brown', 'yellow']
        plot_lines = []
        for i, line in enumerate(lines):
            attr = {}
            if line.type == LINE_MARKER:
                handle = wxplot.PolyMarker
                attr['size'] = 1
            else:
                handle = wxplot.PolyLine
            points = line.GetPoints()
            attr['colour'] = line.colour or colours[i % len(colours)]
            attr['legend'] = line.GetTitle() or 'Unknown line'
            plot_lines.append(handle(points, **attr))

        graph = wxplot.PlotGraphics(plot_lines)
        self.plot.Draw(graph)

    def OnSaveImage(self, event):
        img_file = wx.FileSelector('Save plot',
            default_filename = 'plot.png',
            default_extension = 'png',
            wildcard = 'PNG files (*.png)|*.png',
            flags = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        size_sel = forms.SizeSelector(self)
        if img_file and size_sel.ShowModal() == wx.ID_OK:
            self.plot.Freeze()
            w, h = size_sel.GetValues()
            old_size = self.plot.GetSize()
            self.plot.SetSize((w, h))
            self.plot.SaveFile(img_file)
            self.plot.SetSize(old_size)
            self.plot.Thaw()

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

def main():
    app = ThisApp(redirect = False)
    app.MainLoop()    

if __name__ == "__main__":
    main()