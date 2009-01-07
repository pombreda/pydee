# -*- coding: utf-8 -*-

#TODO: satellite widgets which refresh when shell widget
# emits a signal (e.g. when it executes a command)

#TODO: multiple line QTextEdit/QScintilla editor
#TODO: current directory changer widget
#TODO: globals explorer widget

# from PyQt4.QtGui import QLineEdit
# from PyQt4.QtCore import Qt

# Local import
# import config

try:
    from qsciwidgets import QsciShell as QShell
    # from qsciwidgets import QsciEditor as QEditor
except ImportError:
    from qtwidgets import QSimpleShell as QShell
    # from qtwidgets import QSimpleEditor as QEditor
