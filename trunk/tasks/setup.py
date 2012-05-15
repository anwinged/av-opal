from distutils.core import setup
import py2exe

setup(
    name = 'testt',
    console = ['testt.py'],
    options = { "py2exe": {
        "compressed": 2,
        "optimize": 2,
        "bundle_files": 1,
    } },
    zipfile = None,
)