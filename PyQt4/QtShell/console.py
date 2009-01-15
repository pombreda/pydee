# -*- coding: utf-8 -*-
"""
PyQtShell demo
"""

#TODO: Toolbar: 'start logging' and 'stop logging' buttons

__version__ = '0.0.1'

import sys, os, platform
from PyQt4.QtGui import QApplication, QMainWindow
from PyQt4.QtGui import QMessageBox, QMenu
from PyQt4.QtCore import SIGNAL, PYQT_VERSION_STR, QT_VERSION_STR, QPoint
from PyQt4.QtCore import QLibraryInfo, QLocale, QTranslator, QSize, QByteArray

# Local import
from widgets import Shell, WorkingDirectory, Editor
from qthelpers import create_action, add_actions, get_std_icon
from config import get_icon, CONF


class ConsoleWindow(QMainWindow):
    """Console QDialog"""
    def __init__(self, initcommands=None, message=""):
        super(ConsoleWindow, self).__init__()

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
        self.shell = Shell(initcommands=initcommands,
                           message=message, parent=self)
        self.setCentralWidget(self.shell)
#        self.add_dockwidget(self.shell)
        self.add_to_menubar(self.shell)
        self.add_to_toolbar(self.shell)
        self.connect(self.shell, SIGNAL("status(QString)"), 
                     self.send_to_statusbar)
        
        # Editor widget
        self.editor = Editor( self )
        self.add_dockwidget(self.editor)
        self.add_to_menubar(self.editor)
        self.add_to_toolbar(self.editor)
        
        # Working directory changer widget
        self.workdir = WorkingDirectory( self )
        self.add_dockwidget(self.workdir)
        self.connect(self.shell, SIGNAL("refresh()"), self.workdir.refresh)
        
        # View menu
        self.menuBar().addMenu(self.view_menu)
        
        # ? menu
        about = self.menuBar().addMenu("?")
        about.addAction(create_action(self, self.tr("About..."),
            icon=get_std_icon('MessageBoxInformation'),
            triggered=self.about))
        
        # Window set-up
        self.setWindowIcon(get_icon('qtshell.png'))
        self.setWindowTitle(self.tr('PyQtShell Console'))
        width, height = CONF.get('shell', 'window/size')
        self.resize( QSize(width, height) )
        posx, posy = CONF.get('shell', 'window/position')
        self.move( QPoint(posx, posy) )
        hexstate = CONF.get('shell', 'window/state')
        self.restoreState( QByteArray().fromHex(hexstate) )
        
    def closeEvent(self, event):
        """Exit confirmation"""
        if QMessageBox.question(self, self.tr("Quit"),
               self.tr("Are you sure you want to quit?"),
               QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
            # Saving window settings
            size = self.size()
            CONF.set('shell', 'window/size', (size.width(), size.height()))
            pos = self.pos()
            CONF.set('shell', 'window/position', (pos.x(), pos.y()))
            qba = self.saveState()
            CONF.set('shell', 'window/state', str(qba.toHex()))
            CONF.set('shell', 'window/statusbar',
                      not self.statusBar().isHidden())
            # Warning children that their parent is closing:
            self.emit( SIGNAL('closing()') )
            # Closing...
            event.accept()
        else:
            event.ignore()
        
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
            <p>Python %3 - Qt %4 - PyQt %5 on %6""") \
            .arg(self.tr('PyQtShell Console')).arg(__version__) \
            .arg(platform.python_version()).arg(QT_VERSION_STR) \
            .arg(PYQT_VERSION_STR).arg(platform.system()))
            
    def send_to_statusbar(self, message):
        """Show a message in the status bar"""
        self.statusBar().showMessage(message)
        
        
def get_initcommands_message():
    """
    Convert options into initcommands
    """
    import optparse
    parser = optparse.OptionParser("PyQtShell Console")
    parser.add_option('-m', '--modules', dest="modules", default='',
                      help="Modules to import (comma separated)")
    parser.add_option('-p', '--pylab', dest="pylab", action='store_true',
                      default=False,
                      help="Import pylab in interactive mode")
    parser.add_option('-o', '--os', dest="os", action='store_true',
                      default=False,
                      help="Import os and os.path as osp")
    parser.add_option('-n', '--np', dest="np", action='store_true',
                      default=False,
                      help="Import numpy as np (and * from numpy)")
    parser.add_option('-s', '--sp', dest="sp", action='store_true',
                      default=False,
                      help="Import scipy as sp (and * from scipy)")
    options, _args = parser.parse_args()
    messagelist = []
    if options.modules:
        for mod in options.modules.split(','):
            mod = mod.strip()
            try:
                __import__(mod)
                messagelist.append(mod)
            except ImportError:
                print "Warning: module '%s' was not found" % mod
                continue
    initcommands = []
    if options.pylab:
        initcommands.extend(['from pylab import *',
                             'from matplotlib import rcParams',
                             'rcParams["interactive"]=True'])
        messagelist.append('pylab')
    if options.os:
        initcommands.extend(['import os',
                             'import os.path as osp'])
        messagelist.append('os')
    if options.np:
        initcommands.extend(['from numpy import *',
                             'import numpy as np'])
        messagelist.append('np')
    if options.sp:
        initcommands.extend(['from scipy import *',
                             'import scipy as sp'])
        messagelist.append('sp')
    message = 'Option%s:' % ('s' if len(messagelist)>1 else '')
    message += ", ".join(messagelist)
    return initcommands, message


def main():
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
    initcommands, message = get_initcommands_message()
    dialog = ConsoleWindow(initcommands, message)
    dialog.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()