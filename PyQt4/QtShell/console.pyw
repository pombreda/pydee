# -*- coding: utf-8 -*-
"""
PyQtShell demo
"""

import sys
from PyQt4.QtGui import QDialog, QApplication, QHBoxLayout
from PyQt4.QtCore import Qt

# Local import
from widgets import QShell
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
    for arg in options:
        if OPTIONS.has_key(arg):
            commands.extend(OPTIONS[arg])
            if not message:
                message = 'Options:'
            message += ' '+arg
    return (commands, message)


class ConsoleDialog(QDialog):
    """Console QDialog"""
    def __init__(self, parent=None, options=[]):
        QDialog.__init__(self, parent)
        layout = QHBoxLayout()
        initcommands, message = get_initcommands(options)
        self.console = QShell( initcommands=initcommands,
                                     message=message )
        layout.addWidget(self.console)
        self.setLayout(layout)
        self.setWindowIcon(config.icon('qtshell.png'))
        self.setWindowTitle('PyQtShell demo')
        self.setWindowFlags(Qt.Window)
        self.setModal(False)
        self.resize(700, 450)

        
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