# -*- coding: utf-8 -*-
"""
PyQtShell Console
"""

__version__ = '0.0.7'

import sys, os, platform
from PyQt4.QtGui import QApplication, QMainWindow
from PyQt4.QtGui import QMessageBox, QMenu
from PyQt4.QtCore import SIGNAL, PYQT_VERSION_STR, QT_VERSION_STR, QPoint
from PyQt4.QtCore import QLibraryInfo, QLocale, QTranslator, QSize, QByteArray

# Local import
from widgets import Shell, WorkingDirectory, Editor, HistoryLog, Workspace
from qthelpers import create_action, add_actions, get_std_icon
from config import get_icon, CONF


class ConsoleWindow(QMainWindow):
    """Console QDialog"""
    def __init__(self, commands=None, message=""):
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
        checked = CONF.get('window', 'statusbar')
        action.setChecked(checked)
        self.toggle_statusbar(checked)
        
        # Workspace init
        if CONF.get('workspace', 'enable'):
            self.workspace = Workspace(self, None)
            namespace = self.workspace.namespace
        else:
            namespace = None
        
        # Shell widget: window's central widget
        self.shell = Shell(namespace, commands, message, self)
        self.setCentralWidget(self.shell)
#        self.add_dockwidget(self.shell)
        self.add_to_menubar(self.shell)
        self.add_to_toolbar(self.shell)
        self.toolbar.addSeparator()
        self.connect(self.shell, SIGNAL("status(QString)"), 
                     self.send_to_statusbar)
        
        # Workspace
        if CONF.get('workspace', 'enable'):
            self.workspace.set_shell(self.shell)
            self.add_dockwidget(self.workspace)
            self.add_to_menubar(self.workspace)
            self.add_to_toolbar(self.workspace)
            self.connect(self.shell, SIGNAL("refresh()"),
                         self.workspace.refresh)
        
        # Editor widget
        if CONF.get('editor', 'enable'):
            self.editor = Editor( self )
            self.add_dockwidget(self.editor)
            self.add_to_menubar(self.editor)
            self.add_to_toolbar(self.editor)
        
        # History log widget
        if CONF.get('history', 'enable'):
            self.historylog = HistoryLog( self )
            self.add_dockwidget(self.historylog)
            self.connect(self.shell, SIGNAL("refresh()"),
                         self.historylog.refresh)
        
        # Working directory changer widget
        self.workdir = WorkingDirectory( self )
        self.connect(self.shell, SIGNAL("refresh()"),
                     self.workdir.refresh)
#        self.add_dockwidget(self.workdir)
        self.add_toolbar(self.workdir)
            
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
        width, height = CONF.get('window', 'size')
        self.resize( QSize(width, height) )
        posx, posy = CONF.get('window', 'position')
        self.move( QPoint(posx, posy) )
        hexstate = CONF.get('window', 'state')
        self.restoreState( QByteArray().fromHex(hexstate) )
        self.shell.setFocus()
        
    def closeEvent(self, event):
        """Exit confirmation"""
        if QMessageBox.question(self, self.tr("Quit"),
               self.tr("Are you sure you want to quit?"),
               QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
            # Saving window settings
            size = self.size()
            CONF.set('window', 'size', (size.width(), size.height()))
            pos = self.pos()
            CONF.set('window', 'position', (pos.x(), pos.y()))
            qba = self.saveState()
            CONF.set('window', 'state', str(qba.toHex()))
            CONF.set('window', 'statusbar',
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
        dockwidget, location = (child.dockwidget, child.location)
        self.addDockWidget(location, dockwidget)
        self.view_menu.addAction(dockwidget.toggleViewAction())
        self.connect(dockwidget, SIGNAL('visibilityChanged(bool)'),
                     child.visibility_changed)
    
    def add_toolbar(self, widget):
        """Add toolbar including a widget"""
        toolbar = self.addToolBar(widget.get_name())
        toolbar.addWidget(widget)
        toolbar.setObjectName(widget.get_name())
        toolbar.setToolTip(widget.get_name())
        
    def add_to_menubar(self, widget):
        """Add menu and actions to menubar"""
        actions = widget.menu_actions
        if actions is not None:
            menu = self.menuBar().addMenu(widget.get_name())
            add_actions(menu, actions)

    def add_to_toolbar(self, widget):
        """Add actions to toolbar"""
        actions = widget.toolbar_actions
        if actions is not None:
            add_actions(self.toolbar, actions)
        
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
        
        
def get_options():
    """
    Convert options into commands
    return commands, message
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
    commands = []
    if options.pylab:
        commands.extend(['from pylab import *',
                             'from matplotlib import rcParams',
                             'rcParams["interactive"]=True'])
        messagelist.append('pylab')
    if options.os:
        commands.extend(['import os',
                             'import os.path as osp'])
        messagelist.append('os')
    if options.np:
        commands.extend(['from numpy import *',
                             'import numpy as np'])
        messagelist.append('np')
    if options.sp:
        commands.extend(['from scipy import *',
                             'import scipy as sp'])
        messagelist.append('sp')
    if messagelist:
        message = 'Option%s: ' % ('s' if len(messagelist)>1 else '')
        message += ", ".join(messagelist)
    else:
        message = ""
    return commands, message


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
    commands, message = get_options()
    window = ConsoleWindow(commands, message)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()