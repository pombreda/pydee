# -*- coding: utf-8 -*-
"""
PyQtShell demo
"""

#TODO: Toolbar: 'start logging' and 'stop logging' buttons

import sys, os
from PyQt4.QtGui import QApplication, QMainWindow
from PyQt4.QtGui import QMessageBox, QMenu
from PyQt4.QtCore import Qt, QObject, SIGNAL
from PyQt4.QtCore import QLibraryInfo, QLocale, QTranslator

# Local import
from widgets import QShell, WorkingDirChanger
from widgets import create_action, add_actions
from config import icon, CONF

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
    if optnb > 0:
        prefix = 'Option%s:' % ('s' if optnb>1 else '')
        message = prefix + message
    return (commands, message)


class ConsoleWindow(QMainWindow):
    """Console QDialog"""
    def __init__(self, parent=None, options=[]):
        super(ConsoleWindow, self).__init__(parent)

        self.filename = None

        # Status bar
        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.showMessage(self.tr("Welcome to PyQtShell demo!"), 5000)
        
        # Toolbar
        self.toolbar = self.addToolBar("Console")
        self.toolbar.setObjectName('toolbar')
        # Hiding toolbar until the day there will be more than 1 icon to show :)
        self.toolbar.hide()
        
        # Shell widget: window's central widget
        self.initcommands, self.message = get_initcommands(options)
        self.shell = QShell( initcommands = self.initcommands,
                             message = self.message,
                             parent = self )
        self.setCentralWidget(self.shell)
        self.shell.set_menu(parent = self)
        add_actions( self.toolbar,
                     self.shell.get_actions(toolbar=True))
        QObject.connect(self.shell, SIGNAL("status(QString)"),
                        self.send_to_statusbar)
        
        # Working directory changer widget
        self.workdir = WorkingDirChanger( self )
        self.workdir.add_dockwidget()
        QObject.connect(self.shell, SIGNAL("refresh()"), self.workdir.refresh)
        
        # ? menu
        about = self.menuBar().addMenu("?")
        about.addAction(create_action(self, self.tr("About..."),
                                      triggered=self.about))
        
        # Window set-up
        self.setWindowIcon(icon('qtshell.png'))
        self.setWindowTitle(self.tr('PyQtShell Console'))
        import PyQt4 # in order to eval the following settings:
        self.resize( eval(CONF.get('shell', 'window/size')) )
        self.move( eval(CONF.get('shell', 'window/position')) )
        self.restoreState( eval(CONF.get('shell', 'window/state')) )
        
    def about(self):
        pass
        
    def closeEvent(self, event):
        """Exit confirmation"""
        if QMessageBox.question(self, self.tr("Quit"),
               self.tr("Are you sure you want to quit?"),
               QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
            # Saving window settings
            CONF.set( 'shell', 'window/size', self.size() )
            CONF.set( 'shell', 'window/position', self.pos() )
            CONF.set( 'shell', 'window/state', self.saveState() )
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
    qt_translator = QTranslator()
    qt_trpath = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load("qt_" + locale, qt_trpath):
        app.installTranslator(qt_translator)
    app_translator = QTranslator()
    app_path = os.path.dirname(__file__)
    if app_translator.load("console_" + locale, app_path):
        app.installTranslator(app_translator)
    dialog = ConsoleWindow( options = args )
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main(*sys.argv)