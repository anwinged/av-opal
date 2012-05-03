# -*- coding: utf-8 -*-

import wx
import wx.gizmos
import wx.grid
import wx.propgrid as wxpg
import wx.lib.plot as wxplot
import wx.lib.agw.aui as aui
# import wx.aui as aui

ID_NEW                  = wx.NewId()
ID_SAVE                 = wx.NewId()
ID_OPEN                 = wx.NewId()

ID_TEST                 = wx.NewId()
ID_ADD_MODEL_ROOT       = wx.NewId()
ID_ADD_MODEL_SELECTED   = wx.NewId()
ID_DUPLICATE_MODEL      = wx.NewId()
ID_DUPLICATE_TREE       = wx.NewId()
ID_DELETE_MODEL         = wx.NewId()
ID_PROCESS_MODEL        = wx.NewId()

ID_SHOW_RESULT          = wx.NewId()

ID_SHOW_PLOT            = wx.NewId()
ID_ADD_PLOT             = wx.NewId()
ID_ADD_CURVES           = wx.NewId()
ID_ADD_MARKERS          = wx.NewId()

ID_ABOUT                = wx.NewId()

class TreeListCtrl(wx.gizmos.TreeListCtrl):
    def __iter__(self):
        return TreeListCtrlIterator(self)

class TreeListCtrlIterator:
    def __init__(self, owner):
        self.owner = owner
        self.item = self.owner.GetRootItem()

    def __iter__(self):
        return self

    def next(self):
        if not self.item.IsOk():
            raise StopIteration
        item = self.item
        self.item = self.owner.GetNext(self.item)
        return item

class Icons:
    """
    Пустой класс для хранения идентификаторов иконок, чтобы к ним можно было
    удобно обращаться:
    icons = Icons()
    icons.open = wxIcon(...)
    """
    pass

class PropertyCtrl(wxpg.PropertyGrid):

    def GetPosition(self):
        return self.GetPanel().GetPosition()

    def Clear(self):
        wxpg.PropertyGrid.Clear(self)

class MainFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__ (self, parent, title = 'Opal', size = wx.Size(873,594))

        self.auimgr = aui.AuiManager()
        self.auimgr.SetManagedWindow(self)
        self.auimgr.GetArtProvider().SetMetric(aui.AUI_DOCKART_SASH_SIZE, 3)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        self.ilist, self.icons = self.LoadIcons()

        # Спецификации

        self.m_specs = wx.TreeCtrl(self, size = (200, -1), style = wx.TR_DEFAULT_STYLE)
        # self.m_specs.SetMinSize(wx.Size(200,-1))

        self.auimgr.AddPane(self.m_specs,
            aui.AuiPaneInfo().Name("m_specs").Caption("Templates").
            Left().Layer(1).CloseButton(False))

        # Пользовательские модели

        self.m_user_models = TreeListCtrl(self, size = (200, -1),
            style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT
                    | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_ROW_LINES | wx.TR_MULTIPLE)
        self.m_user_models.AddColumn("Model name")
        self.m_user_models.AddColumn("Status")
        self.m_user_models.AddColumn("Progress")
        self.m_user_models.AddColumn("Comment")
        self.m_user_models.SetMainColumn(0)
        self.m_user_models.SetImageList(self.ilist)

        self.auimgr.AddPane(self.m_user_models,
            aui.AuiPaneInfo().Name("m_user_models").Caption("Models").
            CenterPane().Position(1))

        # Параметры модели

        self.m_params = PropertyCtrl(self, size = (-1, 300))

        self.auimgr.AddPane(self.m_params,
            aui.AuiPaneInfo().Name("m_params").Caption("Parameters").CloseButton(False).
            CenterPane().Bottom().Position(2))

        # Быстрые результаты

        self.m_quick_result = PropertyCtrl(self, size = (200, -1))

        self.auimgr.AddPane(self.m_quick_result,
            aui.AuiPaneInfo().Name("m_quick_result").Caption("Quick results").CloseButton(False).
            Right().Position(1).Layer(1))

        # Графики

        self.m_plots = wx.TreeCtrl(self, size = (200, -1),
            style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_EDIT_LABELS)
        self.m_plots.SetImageList(self.ilist)

        self.auimgr.AddPane(self.m_plots,
            aui.AuiPaneInfo().Name("m_plots").Caption("Plots").CloseButton(False).
            Right().Position(2).Layer(1))

        # Меню, панель инструментов и панель статуса

        sbar = wx.StatusBar(self)
        self.SetStatusBar(sbar)

        self.SetMenuBar(self.BuildMenu())

        self.BuildContextMenu()

        # tbar = self.BuildToolBar()
        # self.SetToolBar(tbar)

        self.auimgr.Update()

    def LoadIcons(self):
        icons = Icons()
        ilist = wx.ImageList(16, 16)
        
        icons.mready    = ilist.Add(wx.Bitmap('share/model-ready.png'))
        icons.mrun      = ilist.Add(wx.Bitmap('share/model-run.png'))
        icons.mcomplete = ilist.Add(wx.Bitmap('share/model-complete.png'))

        icons.porg      = ilist.Add(wx.Bitmap('share/plot-org.png'))
        icons.pline     = ilist.Add(wx.Bitmap('share/plot-line.png'))
        icons.pmarker   = ilist.Add(wx.Bitmap('share/plot-marker.png'))
        icons.phist     = ilist.Add(wx.Bitmap('share/plot-histogram.png'))

        return ilist, icons

    def BuildMenu(self):
        menubar = wx.MenuBar()

        menu = wx.Menu()
        menu.Append(ID_NEW, "&New\tCtrl+N")
        menu.Append(ID_OPEN, "&Open\tCtrl+O")
        menu.Append(ID_SAVE, "&Save\tCtrl+S")
        menubar.Append(menu, '&Project')

        menu = wx.Menu()
        menu.Append(ID_ADD_MODEL_ROOT, 'Add model to root')
        menu.Append(ID_ADD_MODEL_SELECTED, 'Append model to selected')
        menu.AppendSeparator()
        menu.Append(ID_DUPLICATE_MODEL, "&Duplicate\tCtrl+D")
        #menu.Append(ID_DUPLICATE_TREE, "&Duplicate with subitems\tCtrl+Shift+D")
        menu.Append(ID_DELETE_MODEL, 'Delete\tCtrl+E')
        menu.AppendSeparator()
        menu.Append(ID_TEST, "&Test\tCtrl+T")
        menubar.Append(menu, '&Model')

        menu = wx.Menu()
        menu.Append(ID_PROCESS_MODEL, 'Process\tF5')
        #menu.AppendSeparator()
        menubar.Append(menu, '&Run')

        menu = wx.Menu()
        menu.Append(ID_SHOW_RESULT, 'Show numbers\tF7')
        menu.AppendSeparator()
        menu.Append(ID_SHOW_PLOT, 'Show plot\tF8')
        menu.Append(ID_ADD_PLOT, 'Add plot')
        #menu.Append(ID_ADD_LINE, 'Add line')
        menubar.Append(menu, '&Result')

        menu = wx.Menu()
        menu.Append(ID_ABOUT, "&About\tF1")
        menubar.Append(menu, '&Help')

        return menubar

    def BuildContextMenu(self):
        menu = wx.Menu()
        menu.Append(ID_ADD_MODEL_ROOT, 'Add model to root')
        menu.Append(ID_ADD_MODEL_SELECTED, 'Add model to selected')
        self.m_specs.Bind(wx.EVT_CONTEXT_MENU,
            lambda x: self.m_specs.PopupMenu(menu))

        menu1 = wx.Menu()
        menu1.Append(ID_ADD_PLOT, 'Add plot')
        menu1.AppendSeparator()
        menu1.Append(ID_ADD_CURVES,  'Add curves')
        menu1.Append(ID_ADD_MARKERS, 'Add markers')
        self.m_plots.Bind(wx.EVT_CONTEXT_MENU,
            lambda x: self.m_plots.PopupMenu(menu1))

    def BuildToolBar(self):
        tbar = wx.ToolBar(self, -1)
        tbar.AddLabelTool(ID_SHOW_PLOT, 'Plot', wx.Bitmap('share/show-plot.png'))
        tbar.Realize()
        return tbar

class SelectModelDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'Select model')

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.mlist = wx.ListCtrl(self, style = wx.LC_ICON | wx.LC_SINGLE_SEL)
        sizer.Add(self.mlist, 1, wx.EXPAND | wx.ALL, 0)

        buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttonsSizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)
        self.Layout()
        self.Centre(wx.BOTH)

class ResultFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__ (self, parent, -1, title, size = wx.Size(500, 500),
                style = wx.DEFAULT_FRAME_STYLE)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.scalar = PropertyCtrl(self)
        self.scalar.SetMinSize((-1, 200))

        self.table = wx.grid.Grid(self)
        self.table.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)

        sizer.Add(self.scalar, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(self.table,  1, wx.EXPAND | wx.ALL, 1)

        self.SetMenuBar(self.BuildMenu())

        self.SetSizer(sizer)
        self.Layout()
        self.Centre(wx.BOTH)

    def BuildMenu(self):

        menubar = wx.MenuBar()

        menu = wx.Menu()
        menu.Append(wx.NewId(), 'CSV\tCtrl+E')
        menu.Append(wx.NewId(), 'TeX')
        menubar.Append(menu, 'Export to')

        return menubar

class LineSelectDialog(wx.Dialog):
    def __init__(self, parent, title):
        wx.Dialog.__init__ (self, parent, -1, title, size = wx.Size(400, 300))

        bSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.left = wx.ListBox(self)
        self.right = wx.ListBox(self, style = wx.LB_EXTENDED)

        bSizer.Add(self.left, 1, wx.EXPAND | wx.ALL, 2)
        bSizer.Add(self.right, 1, wx.EXPAND | wx.ALL, 2)

        buttonsSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(bSizer, 1, wx.EXPAND | wx.ALL, 0)
        sizer.Add(buttonsSizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)
        self.Layout()   
        self.Centre(wx.BOTH)

class PlotFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__ (self, parent, -1, title, size = wx.Size(600, 400))

        self.plot = wxplot.PlotCanvas(self)
        self.plot.SetGridColour(wx.Color(200, 200, 200))
        self.plot.SetEnableGrid(True)
        self.plot.SetEnableAntiAliasing(True)
        self.plot.SetEnableHiRes(True)
        self.plot.SetEnableLegend(True)

        self.Centre(wx.BOTH)
