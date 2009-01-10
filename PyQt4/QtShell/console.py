# -*- coding: utf-8 -*-
"""
PyQtShell demo
"""

#TODO: Toolbar: 'start logging' and 'stop logging' buttons

import sys, os
from PyQt4.QtGui import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt4.QtGui import QMessageBox, QFrame, QLabel
from PyQt4.QtCore import QObject, SIGNAL
from PyQt4.QtCore import QLibraryInfo, QLocale, QTranslator

# Local import
from widgets import QShell, CurrentDirChanger
from widgets import add_actions
import config
CONFIG = config.CONFIG

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


class ConsoleWindow(QMainWindow):
    """Console QDialog"""
    def __init__(self, parent=None, options=[]):
        super(ConsoleWindow, self).__init__(parent)

        self.filename = None

        # Main window's central widget
        layout = QVBoxLayout()
        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(layout)
        
        # Status bar
        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.showMessage(self.tr("Welcome to PyQtShell demo!"), 5000)
        
        # Toolbar
        self.toolbar = self.addToolBar("Console")
        # Hiding toolbar until the day there will be more than 1 icon to show :)
        self.toolbar.hide()
        
        # Shell widget
        self.initcommands, self.message = get_initcommands(options)
        self.shell = QShell( initcommands = self.initcommands,
                             message = self.message,
                             parent = self )
        layout.addWidget(self.shell)
        self.shell.set_menu(parent = self)
        add_actions( self.toolbar,
                     self.shell.get_actions(toolbar=True))
        QObject.connect(self.shell, SIGNAL("status(QString)"), self.send_to_statusbar)
        
        # Current directory changer widget
        self.curdir = CurrentDirChanger( self )
        QObject.connect(self.shell, SIGNAL("refresh()"), self.curdir.refresh)
        layout.addWidget(self.curdir)
#        status.addPermanentWidget(self.curdir)
        
        # Window set-up
        self.setWindowIcon(config.icon('qtshell.png'))
        self.setWindowTitle(self.tr('PyQtShell Console'))
        self.resize(700, 450)
        
    def closeEvent(self, event):
        """Exit confirmation"""
        if QMessageBox.question(self, self.tr("Quit"),
                                       self.tr("Are you sure you want to quit?"),
                                       QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
            #TODO: make the children widget handle their own destruction
            # instead of doing the following tasks here:
            self.shell.save_history()
            # Closing...
            event.accept()
        else:
            event.ignore()
            
    def send_to_statusbar(self, message):
        """Show a message in the status bar"""
        self.statusBar().showMessage(message)
        
        
def main(*args):
    """
    PyQtShell demo
    """
    app = QApplication(sys.argv)
    locale = QLocale.system().name()
    qtTranslator = QTranslator()
    qt_trpath = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qtTranslator.load("qt_" + locale, qt_trpath):
        app.installTranslator(qtTranslator)
    appTranslator = QTranslator()
    app_path = os.path.dirname(__file__)
    if appTranslator.load("console_" + locale, app_path):
        app.installTranslator(appTranslator)
    dialog = ConsoleWindow( options = args )
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main(*sys.argv)