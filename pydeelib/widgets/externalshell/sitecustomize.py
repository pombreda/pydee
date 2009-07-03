# -*- coding: utf-8 -*-
# Pydee's ExternalPythonShell sitecustomize


# Set standard outputs encoding:
# (otherwise, for example, print u"é" will fail)
import sys, os
import os.path as osp
encoding = None
try:
    import locale
except ImportError:
    pass
else:
    loc = locale.getdefaultlocale()
    if loc[1]:
        encoding = loc[1]

if encoding is None:
    encoding = "UTF-8"

sys.setdefaultencoding(encoding)

import pydeelib.widgets.externalshell as extsh
scpath = osp.dirname(osp.abspath(extsh.__file__))
sys.path.remove(scpath)

try:
    import sitecustomize #@UnusedImport
except ImportError:
    pass

# Communication between ExternalShell and the QProcess
from pydeelib.widgets.externalshell.monitor import Monitor
monitor = Monitor("127.0.0.1", int(os.environ['PYDEE_PORT']),
                  os.environ['SHELL_ID'])
monitor.start()

# Quite limited feature: notify only when a result is displayed in console
# (does not notify at every prompt)
def displayhook(obj):
    sys.__displayhook__(obj)
    monitor.refresh()

sys.displayhook = displayhook
