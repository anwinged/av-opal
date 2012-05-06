from distutils.core import setup
import py2exe


excludes = ['_gtkagg', '_tkagg', 'bsddb', 'curses', 'email', 'pywin.debugger',
            'pywin.debugger.dbgcon', 'pywin.dialogs', 'tcl',
            'Tkconstants', 'Tkinter']
setup(
    name = 'Opal',
    windows = ['opal.pyw'],
    options = { "py2exe": {
        "compressed": 2, 
        "optimize": 2, 
        "bundle_files": 1,
        "excludes": excludes,
    } },
    zipfile = None,
)