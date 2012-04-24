# -*- coding: utf-8 -*-

import wx
import wx.gizmos
import wx.grid
import wx.propgrid as wxpg
import wx.lib.plot as wxplot

ID_TEST                 = wx.NewId()
ID_ADD_MODEL_ROOT       = wx.NewId()
ID_ADD_MODEL_SELECTED   = wx.NewId()
ID_DUPLICATE_MODEL      = wx.NewId()
ID_DUPLICATE_TREE       = wx.NewId()
ID_DELETE_MODEL         = wx.NewId()
ID_PROCESS_MODEL        = wx.NewId()
ID_SHOW_RESULT          = wx.NewId()
ID_SHOW_PLOT            = wx.NewId()

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


class MainFrame (wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__ (self, parent, title = 'Opal', size = wx.Size(873,594))

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        bSizer3 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_specs = wx.TreeCtrl(self, style = wx.TR_DEFAULT_STYLE)
        self.m_specs.SetMinSize(wx.Size(200,-1))

        bSizer3.Add(self.m_specs, 0, wx.ALL|wx.EXPAND, 1)

        bSizer4 = wx.BoxSizer(wx.VERTICAL)

        self.m_user_models = TreeListCtrl(self,
            style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT
                    | wx.TR_EDIT_LABELS | wx.TR_ROW_LINES | wx.TR_MULTIPLE)
        self.m_user_models.SetMinSize(wx.Size(-1, 300))
        self.m_user_models.AddColumn("Model name")
        self.m_user_models.AddColumn("Status")
        self.m_user_models.AddColumn("Progress")
        self.m_user_models.AddColumn("Comment")

        bSizer4.Add(self.m_user_models, 0, wx.ALL | wx.EXPAND, 1)

        # WARNING: wxPython code generation isn't supported for this widget yet.
        self.m_params = wxpg.PropertyGridManager(self)
        self.m_params.AddPage('fp')
        bSizer4.Add(self.m_params, 1, wx.EXPAND | wx.ALL, 1)

        bSizer3.Add(bSizer4, 1, wx.EXPAND, 5)

        bSizer5 = wx.BoxSizer(wx.VERTICAL)

        self.m_quick_result = wxpg.PropertyGridManager(self)
        self.m_quick_result.AddPage('fp')
        self.m_quick_result.SetMinSize(wx.Size(200, -1))
        bSizer5.Add(self.m_quick_result, 1, wx.EXPAND | wx.ALL, 1)

        self.m_plots = wx.TreeCtrl(self, style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        bSizer5.Add(self.m_plots, 1, wx.EXPAND | wx.ALL, 1)        

        bSizer3.Add(bSizer5, 0, wx.ALL | wx.EXPAND, 1)

        sbar = wx.StatusBar(self)
        self.SetStatusBar(sbar)

        mbar = self.BuildMenu()
        self.SetMenuBar(mbar)
        self.BuildContextMenu()

        self.SetSizer(bSizer3)
        self.Layout()

        self.Centre(wx.BOTH)

    def __del__(self):
        pass

    def BuildMenu(self):
        menubar = wx.MenuBar()

        menu = wx.Menu()
        menu.Append(1, "&Open\tCtrl+O")
        menubar.Append(menu, '&File')

        menu = wx.Menu()
        menu.Append(ID_PROCESS_MODEL, 'Process\tCtrl+R')
        menu.Append(ID_SHOW_RESULT, 'Show result\tCtrl+S')
        menu.Append(ID_SHOW_PLOT, 'Show plot\tCtrl+G')
        menu.AppendSeparator()
        menu.Append(ID_ADD_MODEL_ROOT, 'Add model to root')
        menu.Append(ID_ADD_MODEL_SELECTED, 'Append model to selected')
        menu.AppendSeparator()
        menu.Append(ID_DUPLICATE_MODEL, "&Duplicate\tCtrl+D")
        menu.Append(ID_DUPLICATE_TREE, "&Duplicate with subitems\tCtrl+Shift+D")
        menu.Append(ID_DELETE_MODEL, 'Delete\tCtrl+E')
        menu.AppendSeparator()
        menu.Append(ID_TEST, "&Test\tCtrl+T")
        menubar.Append(menu, '&Model')

        menu = wx.Menu()
        menu.Append(3, "&Log In\tCtrl+L")
        menu.Append(2, "&Options\tCtrl+P")
        menubar.Append(menu, '&Help')

        return menubar

    def BuildContextMenu(self):

        menu = wx.Menu()
        menu.Append(ID_ADD_MODEL_ROOT, 'Add model to root')
        menu.Append(ID_ADD_MODEL_SELECTED, 'Add model to selected')
        self.m_specs.Bind(wx.EVT_CONTEXT_MENU,
            lambda x: self.m_specs.PopupMenu(menu))

class ResultFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__ (self, parent, -1, title, size = wx.Size(500, 500),
                style = wx.DEFAULT_FRAME_STYLE)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.scalar = wxpg.PropertyGridManager(self)
        self.scalar.AddPage('fp')

        self.table = wx.grid.Grid(self)
        self.table.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)

        sizer.Add(self.scalar, 0, wx.EXPAND | wx.ALL, 1)
        sizer.Add(self.table,  1, wx.EXPAND | wx.ALL, 1)

        self.SetSizer(sizer)
        self.Layout()
        self.Centre(wx.BOTH)

class PlotFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__ (self, parent, -1, title, size = wx.Size(600, 400))

        self.plot = wxplot.PlotCanvas(self)