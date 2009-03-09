#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""
Pydee
"""

__version__ = '0.2.4'

import sys, os, platform
from PyQt4.QtGui import QApplication, QMainWindow, QSplashScreen, QPixmap
from PyQt4.QtGui import QMessageBox, QMenu
from PyQt4.QtCore import SIGNAL, PYQT_VERSION_STR, QT_VERSION_STR, QPoint, Qt
from PyQt4.QtCore import QLibraryInfo, QLocale, QTranslator, QSize, QByteArray

# Local import
import encoding
from widgets import Shell, WorkingDirectory, Editor
from widgets import HistoryLog, Workspace, DocViewer
from qthelpers import create_action, add_actions, get_std_icon
from config import get_icon, get_image_path, CONF


class ConsoleWindow(QMainWindow):
    """Console QDialog"""
    def __init__(self, commands=None, message="",
                 workdir=None, debug=False, light=False):
        super(ConsoleWindow, self).__init__()
        self.light = light
        self.filename = None
        namespace = None
        self.splash = QSplashScreen(QPixmap(get_image_path('splash.png'),
                                            'png'))
        self.splash.show()
        
        # List of satellite widgets (registered in add_dockwidget):
        self.widgetlist = []
        
        # Flag used if closing() is called by the exit() shell command
        self.already_closed = False

        if not light:
            # Toolbar
            self.toolbar = self.addToolBar(self.tr("Toolbar"))
            self.toolbar.setObjectName("MainToolbar")
            self.toolbar.setIconSize( QSize(24, 24) )
        
            # Window menu
            self.view_menu = QMenu(self.tr("&View"))
            
            # Toolbar (...)
            self.view_menu.addAction(self.toolbar.toggleViewAction())

            # Status bar
            status = self.statusBar()
            status.setObjectName("StatusBar")
            status.showMessage(self.tr("Welcome to Pydee!"), 5000)
            action = create_action(self, self.tr("Status bar"),
                                   toggled=self.toggle_statusbar)
            self.view_menu.addAction(action)
            checked = CONF.get('window', 'statusbar')
            action.setChecked(checked)
            self.toggle_statusbar(checked)
            
            # Workspace init
            if CONF.get('workspace', 'enable'):
                self.set_splash(self.tr("Loading workspace..."))
                self.workspace = Workspace(self)
                namespace = self.workspace.namespace
        
        # Shell widget: window's central widget
        self.shell = Shell(self, namespace, commands, message,
                           debug, self.closing)
        self.setCentralWidget(self.shell)
        self.widgetlist.append(self.shell)
        
        # Working directory changer widget
        self.workdir = WorkingDirectory( self, workdir )
        self.connect(self.shell, SIGNAL("refresh()"),
                     self.workdir.refresh)
        self.add_toolbar(self.workdir)
        
        if not light:
            # Shell widget (...)
            self.add_to_menubar(self.shell)
            self.add_to_toolbar(self.shell)
            self.toolbar.addSeparator()
            self.connect(self.shell, SIGNAL("status(QString)"), 
                         self.send_to_statusbar)

            # Editor widget
            if CONF.get('editor', 'enable'):
                self.set_splash(self.tr("Loading editor widget..."))
                self.editor = Editor( self )
                self.add_dockwidget(self.editor)
                self.add_to_menubar(self.editor)
                self.add_to_toolbar(self.editor)
        
            # Workspace
            if CONF.get('workspace', 'enable'):
                self.set_splash(self.tr("Loading workspace widget..."))
                self.workspace.set_shell(self.shell)
                self.add_dockwidget(self.workspace)
                self.add_to_menubar(self.workspace)
                self.add_to_toolbar(self.workspace)
                self.connect(self.shell, SIGNAL("refresh()"),
                             self.workspace.refresh)

            # History log widget
            if CONF.get('history', 'enable'):
                self.set_splash(self.tr("Loading history widget..."))
                self.historylog = HistoryLog( self )
                self.add_dockwidget(self.historylog)
                self.connect(self.shell, SIGNAL("refresh()"),
                             self.historylog.refresh)
        
            # Doc viewer widget
            if CONF.get('docviewer', 'enable'):
                self.set_splash(self.tr("Loading docviewer widget..."))
                self.docviewer = DocViewer( self )
                self.add_dockwidget(self.docviewer)
                self.shell.set_docviewer(self.docviewer)
        
        if not light:
            # View menu
            self.menuBar().addMenu(self.view_menu)
        
            # ? menu
            help_menu = self.menuBar().addMenu("?")
            help_menu.addAction(create_action(self, self.tr("About..."),
                icon=get_std_icon('MessageBoxInformation'),
                triggered=self.about))
            if self.shell.help_action is not None:
                help_menu.addAction(self.shell.help_action)
        
        # Window set-up
        self.setWindowIcon(get_icon('pydee.png'))
        self.setWindowTitle(self.tr('Pydee'))
        section = 'lightwindow' if self.light else 'window'
        width, height = CONF.get(section, 'size')
        self.resize( QSize(width, height) )
        posx, posy = CONF.get(section, 'position')
        self.move( QPoint(posx, posy) )
        if not light:
            hexstate = CONF.get(section, 'state')
            self.restoreState( QByteArray().fromHex(hexstate) )
            
        self.splash.hide()
        # Give focus to shell widget
        self.shell.setFocus()
        
    def set_splash(self, message):
        """Set splash message"""
        self.splash.show()
        self.splash.showMessage(message+'\n', Qt.AlignBottom | Qt.AlignHCenter)
        
    def closeEvent(self, event):
        """closeEvent reimplementation"""
        if self.closing(True):
            event.accept()
        else:
            event.ignore()
        
    def closing(self, cancelable=False):
        """Exit tasks"""
        if self.already_closed:
            return True
        size = self.size()
        section = 'lightwindow' if self.light else 'window'
        CONF.set(section, 'size', (size.width(), size.height()))
        pos = self.pos()
        CONF.set(section, 'position', (pos.x(), pos.y()))
        if not self.light:
            qba = self.saveState()
            CONF.set(section, 'state', str(qba.toHex()))
            CONF.set(section, 'statusbar',
                      not self.statusBar().isHidden())
        for widget in self.widgetlist:
            if not widget.closing(cancelable):
                return False
        self.already_closed = True
        return True
        
    def toggle_statusbar(self, checked):
        """Toggle status bar"""
        if checked:
            self.statusBar().show()
        else:
            self.statusBar().hide()
        
    def add_dockwidget(self, child):
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.create_dockwidget()
        self.addDockWidget(location, dockwidget)
        self.view_menu.addAction(dockwidget.toggleViewAction())
        self.connect(dockwidget, SIGNAL('visibilityChanged(bool)'),
                     child.visibility_changed)
        self.widgetlist.append(child)
    
    def add_toolbar(self, widget):
        """Add toolbar including a widget"""
        toolbar = self.addToolBar(widget.get_name())
        toolbar.addWidget(widget)
        toolbar.setObjectName(widget.get_name())
        toolbar.setToolTip(widget.get_name())
        if not self.light:
            self.view_menu.addAction(toolbar.toggleViewAction())
        
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
        """About Pydee"""
        try:
            from PyQt4.Qsci import QSCINTILLA_VERSION_STR as qsci
            qsci = ", QScintilla "+ qsci
        except ImportError:
            qsci = ""
        QMessageBox.about(self,
            self.tr("About %1").arg(self.tr('Pydee')),
            self.tr("""<b>%1</b> v %2
            <br>PYthon Development EnvironmEnt
            <p>Copyright &copy; 2009 Pierre Raybaut - GPLv2
            <p>Pydee is based on PyQtShell module v %2
            <br>Bug reports and feature requests: <a href="http://code.google.com/p/pyqtshell/">Google Code</a><br>
            Discussions around the project: <a href="http://groups.google.com/group/pyqtshell">Google Group</a>
            <p>This project will soon be part of <a href="http://www.pythonxy.com">Python(x,y) distribution</a>
            <p>Python %3, Qt %4, PyQt %5%6 on %7""") \
            .arg(self.tr('Pydee')).arg(__version__) \
            .arg(platform.python_version()).arg(QT_VERSION_STR) \
            .arg(PYQT_VERSION_STR).arg(qsci).arg(platform.system()))
            
    def send_to_statusbar(self, message):
        """Show a message in the status bar"""
        self.statusBar().showMessage(message)
        
        
def get_options():
    """
    Convert options into commands
    return commands, message
    """
    import optparse
    parser = optparse.OptionParser("Pydee")
    parser.add_option('-l', '--light', dest="light", action='store_true',
                      default=False,
                      help="Light version (all add-ons are disabled)")
    parser.add_option('-w', '--workdir', dest="working_directory", default=None,
                      help="Default working directory")
    parser.add_option('-s', '--startup', dest="startup", default=None,
                      help="Startup script (overrides PYTHONSTARTUP)")
    parser.add_option('-m', '--modules', dest="module_list", default='',
                      help="Modules to import (comma separated)")
    parser.add_option('-p', '--pylab', dest="pylab", action='store_true',
                      default=False,
                      help="Import pylab in interactive mode")
    parser.add_option('-o', '--os', dest="os", action='store_true',
                      default=False,
                      help="Import os and os.path as osp")
    parser.add_option('--numpy', dest="numpy", action='store_true',
                      default=False,
                      help="Import numpy as np (and *)")
    parser.add_option('--scipy', dest="scipy", action='store_true',
                      default=False,
                      help="Import numpy as np, scipy as sp (and *)")
    parser.add_option('-d', '--debug', dest="debug", action='store_true',
                      default=False,
                      help="Debug mode (stds are not redirected)")
    options, _args = parser.parse_args()
    messagelist = []
    commands = []
    if options.module_list:
        for mod in options.module_list.split(','):
            mod = mod.strip()
            try:
                __import__(mod)
                messagelist.append(mod)
                commands.append('import '+mod)
            except ImportError:
                print "Warning: module '%s' was not found" % mod
                continue
    if options.pylab:
        commands.extend([
                         'from matplotlib import rcParams',
                         'rcParams["interactive"]=True',
                         'rcParams["backend"]="Qt4Agg"',
                         'from pylab import *',
                         ])
        messagelist.append('pylab')
    if options.os:
        commands.extend(['import os',
                         'import os.path as osp'])
        messagelist.append('os')
    if options.numpy:
        commands.extend(['from numpy import *',
                         'import numpy as np'])
        messagelist.append('numpy')
    if options.scipy:
        commands.extend(['from numpy import *',
                         'import numpy as np',
                         'from scipy import *',
                         'import scipy as sp'])
        messagelist.append('numpy/scipy')
        
    # Adding PYTHONSTARTUP file to initial commands
    if options.startup is not None:
        filename = options.startup
        msg = 'Startup script'
    else:
        filename = os.environ.get('PYTHONSTARTUP')
        msg = 'PYTHONSTARTUP'
    if filename and os.path.isfile(filename):
        lines, _ = encoding.readlines(filename)
        commands.extend( lines )
        messagelist.append(msg+' (%s)' % os.path.basename(filename))
        
    if messagelist:
        message = 'Option%s: ' % ('s' if len(messagelist)>1 else '')
        message += ", ".join(messagelist)
    else:
        message = ""

    return commands, message, options


def main():
    """
    Pydee
    """
    app = QApplication(sys.argv)
    locale = QLocale.system().name()
    qt_translator = QTranslator()
    qt_trpath = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load("qt_" + locale, qt_trpath):
        app.installTranslator(qt_translator)
    app_translator = QTranslator()
    app_path = os.path.dirname(__file__)
    if app_translator.load("pydee_" + locale, app_path):
        app.installTranslator(app_translator)
    commands, message, options = get_options()
    window = ConsoleWindow(commands, message, workdir=options.working_directory,
                           light=options.light, debug=options.debug)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()