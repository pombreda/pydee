# -*- coding: utf-8 -*-
"""
PyQtShell demo
"""

#TODO: Toolbar: 'start logging' and 'stop logging' buttons

__version__ = '0.0.1'

import sys, os, platform
from PyQt4.QtGui import QApplication, QMainWindow
from PyQt4.QtGui import QMessageBox, QMenu
from PyQt4.QtCore import SIGNAL, PYQT_VERSION_STR, QT_VERSION_STR
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
           '-np': ['from numpy import *',
                   'import numpy as np'],
           '-sp': ['from scipy import *',
                   'import scipy as sp'],
           }

def get_initcommands(options):
    """
    Return init commands depending on options
    """
    commands = []
    message = ''
    optnb = 0
    for arg in options:
        if not OPTIONS.has_key(arg):
            importcommand = 'import %s' % arg[1:]
            try:
                exec importcommand
            except:
                print "Warning: option '%s' is not supported" % arg
                continue
        optnb += 1
        if OPTIONS.has_key(arg):
            commands.extend(OPTIONS[arg])
        else:
            commands.append(importcommand)
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

        # Window menu
        self.view_menu = QMenu(self.tr("&View"))

        # Toolbar
        self.toolbar = self.addToolBar(self.tr("Toolbar"))
        self.toolbar.setObjectName("MainToolbar")
        self.view_menu.addAction(self.toolbar.toggleViewAction())

        # Status bar
        status = self.statusBar()
        status.setObjectName("StatusBar")
        status.showMessage(self.tr("Welcome to PyQtShell demo!"), 5000)
        action = create_action(self, self.tr("Status bar"),
                               toggled=self.toggle_statusbar)
        self.view_menu.addAction(action)
        checked = CONF.get('shell', 'window/statusbar', True)
        action.setChecked(checked)
        self.toggle_statusbar(checked)
        
        # Shell widget: window's central widget
        self.initcommands, self.message = get_initcommands(options)
        self.shell = QShell( initcommands = self.initcommands,
                             message = self.message,
                             parent = self )
        self.setCentralWidget(self.shell)
        self.add_to_menubar(self.shell)
        self.add_to_toolbar(self.shell)
        self.connect(self.shell, SIGNAL("status(QString)"), 
                     self.send_to_statusbar)
        
        # Working directory changer widget
        self.workdir = WorkingDirChanger( self )
        self.add_dockwidget(self.workdir)
        self.connect(self.shell, SIGNAL("refresh()"), self.workdir.refresh)
        
        # View menu
        self.menuBar().addMenu(self.view_menu)
        
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
        
    def toggle_statusbar(self, checked):
        """Toggle status bar"""
        if checked:
            self.statusBar().show()
        else:
            self.statusBar().hide()
        
    def add_dockwidget(self, child):
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.get_dockwidget()
        self.addDockWidget(location, dockwidget)
        self.view_menu.addAction(dockwidget.toggleViewAction())        
    
    def add_to_menubar(self, widget):
        """Add menu and actions to menubar"""
        menu = self.menuBar().addMenu(widget.get_name())
        add_actions(menu, widget.get_actions())

    def add_to_toolbar(self, widget):
        """Add actions to toolbar"""
        add_actions(self.toolbar, widget.get_actions(toolbar=True))
        
    def about(self):
        """About PyQtShell console"""
        QMessageBox.about(self,
                self.tr("About %1").arg(self.tr('PyQtShell Console')),
                self.tr("""<b>%1</b> v %2
                <p>Copyright &copy; 2009 Pierre Raybaut - GPLv3
                <p>Interactive console demo.
                <p>Python %3 - Qt %4 - PyQt %5 on %6""").arg(self.tr('PyQtShell Console')).arg(__version__) \
                .arg(platform.python_version()).arg(QT_VERSION_STR) \
                .arg(PYQT_VERSION_STR).arg(platform.system()))
        
    def closeEvent(self, event):
        """Exit confirmation"""
        if QMessageBox.question(self, self.tr("Quit"),
               self.tr("Are you sure you want to quit?"),
               QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
            # Saving window settings
            CONF.set( 'shell', 'window/size', self.size() )
            CONF.set( 'shell', 'window/position', self.pos() )
            CONF.set( 'shell', 'window/state', self.saveState() )
            CONF.set( 'shell', 'window/statusbar',
                      not self.statusBar().isHidden() )
            # Warning children that their parent is closing:
            self.emit( SIGNAL('closing()') )
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
    main(*sys.argv[1:])