# -*- coding: utf-8 -*-

import wx
import wx.gizmos
import wx.propgrid as wxpg

ID_TEST             = wx.NewId()
ID_DUPLICATE        = wx.NewId()
ID_DUPLICATE_MODEL  = wx.NewId()
ID_DELETE_MODEL     = wx.NewId()
ID_PROCESS_MODEL    = wx.NewId()

class MyTreeListCtrl(wx.gizmos.TreeListCtrl):
    def Refresh(self, erase, rect):
        wx.gizmos.TreeListCtrl.Refresh(False, rect)

class MainFrame (wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__ (self, parent, title = 'Opal', size = wx.Size(873,594))

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        bSizer3 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_specs = wx.TreeCtrl(self, style = wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT)
        self.m_specs.SetMinSize(wx.Size(150,-1))

        bSizer3.Add(self.m_specs, 0, wx.ALL|wx.EXPAND, 1)

        bSizer4 = wx.BoxSizer(wx.VERTICAL)

        self.m_user_models = wx.gizmos.TreeListCtrl(self,
        #self.m_user_models = MyTreeListCtrl(self,
        #self.m_user_models = wx.TreeCtrl(self,
            style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_EDIT_LABELS | wx.TR_ROW_LINES)
        self.m_user_models.SetMinSize(wx.Size(-1, 200))
        self.m_user_models.AddColumn("Model name")
        self.m_user_models.AddColumn("Status")
        self.m_user_models.AddColumn("Progress")

        bSizer4.Add(self.m_user_models, 0, wx.ALL|wx.EXPAND, 1)

        # WARNING: wxPython code generation isn't supported for this widget yet.
        self.m_params = wxpg.PropertyGridManager(self,
            style = wxpg.PG_TOOLBAR)
        self.m_params.AddPage('fp')
        bSizer4.Add(self.m_params, 1, wx.EXPAND |wx.ALL, 1)

        bSizer3.Add(bSizer4, 1, wx.EXPAND, 5)

        self.m_job_list = wx.ListBox(self)#, style = wx.LC_LIST)
        self.m_job_list.SetMinSize(wx.Size(200,-1))

        bSizer3.Add(self.m_job_list, 0, wx.ALL|wx.EXPAND, 1)

        sbar = wx.StatusBar(self)
        self.SetStatusBar(sbar)

        mbar = self.BuildMenu()
        self.SetMenuBar(mbar)

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
        menu.Append(ID_TEST, "&Test\tCtrl+U")
        menu.Append(ID_DUPLICATE, "&Duplicate\tCtrl+D")
        menubar.Append(menu, '&Model')

        menu = wx.Menu()
        menu.Append(3, "&Log In\tCtrl+L")
        menu.Append(2, "&Options\tCtrl+P")
        menubar.Append(menu, '&Help')

        return menubar
