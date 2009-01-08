# -*- coding: utf-8 -*-
"""
PyQtShell demo
"""

import sys
from PyQt4.QtGui import QDialog, QApplication, QVBoxLayout
from PyQt4.QtCore import Qt, QObject, SIGNAL

# Local import
from widgets import QShell, CurrentDirChanger
import config

OPTIONS = {
           '-os': ['import os',
                   'import os.path as osp'],
           '-pylab': ['from pylab import *',
                      'from matplotlib import rcParams',
                      'rcParams["interactive"]=True'],
           '-numpy': ['from numpy import *',
                      'import numpy'],
           '-scipy': ['from scipy import *',
                      'import scipy'],
           }

def get_initcommands(options):
    """
    Return init commands depending on options
    """
    commands = []
    message = ''
    optnb = 0
    for arg in options:
        if OPTIONS.has_key(arg):
            optnb += 1
            commands.extend(OPTIONS[arg])
            message += ' '+arg
    if optnb>0:
        prefix = 'Option%s:' % ('s' if optnb>1 else '')
        message = prefix + message
    return (commands, message)


class ConsoleDialog(QDialog):
    """Console QDialog"""
    def __init__(self, parent=None, options=[]):
        QDialog.__init__(self, parent)
        layout = QVBoxLayout()
        initcommands, message = get_initcommands(options)
        self.shell = QShell( initcommands=initcommands,
                             message=message )
        self.curdir = CurrentDirChanger( self.shell )
        layout.addWidget(self.shell)
        layout.addWidget(self.curdir)
        QObject.connect(self.shell, SIGNAL("refresh()"), self.curdir.refresh)
        self.setLayout(layout)
        self.setWindowIcon(config.icon('qtshell.png'))
        self.setWindowTitle('PyQtShell demo')
        self.setWindowFlags(Qt.Window)
        self.setModal(False)
        self.resize(700, 450)
        
    def refresh(self):
        pass

        
def main(*argv):
    """
    PyQtShell demo
    """
    app = QApplication([])
    dialog = ConsoleDialog( options = argv )
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main(*sys.argv)