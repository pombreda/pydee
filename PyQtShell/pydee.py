#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This file is part of PyQtShell.
#
#    PyQtShell is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    PyQtShell is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PyQtShell; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
Pydee
"""

import sys, os, platform

# For debugging purpose only
STDOUT = sys.stdout

from PyQt4.QtGui import (QApplication, QMainWindow, QSplashScreen, QPixmap,
                         QMessageBox, QMenu, QIcon, QLabel, QCursor, QColor)
from PyQt4.QtCore import (SIGNAL, PYQT_VERSION_STR, QT_VERSION_STR, QPoint, Qt,
                          QLibraryInfo, QLocale, QTranslator, QSize, QByteArray,
                          QObject, QVariant)

# Local imports
from PyQtShell import __version__
from PyQtShell import encoding
from PyQtShell.plugins.console import Console
from PyQtShell.plugins.workdir import WorkingDirectory
from PyQtShell.plugins.editor import Editor, HistoryLog, DocViewer
from PyQtShell.plugins.workspace import Workspace
from PyQtShell.plugins.explorer import Explorer
from PyQtShell.qthelpers import (create_action, add_actions, get_std_icon,
                                 keybinding, translate, get_filetype_icon)
from PyQtShell.config import get_icon, get_image_path, CONF

WIDGET_LIST = ['console', 'editor', 'docviewer', 'historylog']

class MainWindow(QMainWindow):
    """Console QDialog"""
    def __init__(self, commands=None, intitle="", message="", options=None):
        super(MainWindow, self).__init__()
        
        # Area occupied by a dock widget can be split in either direction
        # to contain more dock widgets:
        self.setDockNestingEnabled(True)
        
        self.commands = commands
        self.message = message
        self.init_workdir = options.working_directory
        self.debug = options.debug
        self.profile = options.profile
        self.light = options.light
        
        # Widgets
        self.console = None
        self.editor = None
        self.workspace = None
        self.explorer = None
        self.docviewer = None
        self.historylog = None
        
        # Set Window title and icon
        title = "Pydee"
        if intitle:
            title += " (%s)" % intitle
        self.setWindowTitle(title)
        self.setWindowIcon(get_icon('pydee.png'))
        
        # Showing splash screen
        self.splash = QSplashScreen(QPixmap(get_image_path('splash.png'),
                                            'png'))
        self.splash.show()
        
        # List of satellite widgets (registered in add_dockwidget):
        self.widgetlist = []
        
        # Flag used if closing() is called by the exit() shell command
        self.already_closed = False
        
        self.window_size = None
                       
    def setup(self):
        """Setup main window"""
        if not self.light:
            # Toolbar
            self.toolbar = self.addToolBar(self.tr("Toolbar"))
            self.toolbar.setObjectName("MainToolbar")
            self.toolbar.setIconSize( QSize(24, 24) )
            
            _text = translate("FindReplace", "Find text")
            self.find_action = create_action(self, _text,"Ctrl+F", 'find.png',
                                             _text, triggered = self.find)
            _text = translate("FindReplace", "Replace text")
            self.replace_action = create_action(self, _text, "Ctrl+H",
                                                'replace.png', _text,
                                                triggered = self.replace)
            def create_edit_action(text, icon_name):
                return create_action(self, translate("SimpleEditor", text),
                                     shortcut=keybinding(text),
                                     icon=get_icon(icon_name),
                                     triggered=self.global_callback,
                                     data=text.lower())
            self.undo_action = create_edit_action("Undo",'undo.png')
            self.redo_action = create_edit_action("Redo", 'redo.png')
            self.copy_action = create_edit_action("Copy", 'editcopy.png')
            self.cut_action = create_edit_action("Cut", 'editcut.png')
            self.paste_action = create_edit_action("Paste", 'editpaste.png')
            self.delete_action = create_action(self,
                                       translate("SimpleEditor", "Delete"),
                                       icon=get_icon('editdelete.png'),
                                       triggered=self.global_callback,
                                       data="removeSelectedText")
            self.alwayscopyselection_action = create_action(self,
                           translate("SimpleEditor", "Always copy selection"),
                           toggled=self.toggle_alwayscopyselection,
                           tip=translate("SimpleEditor", "Always copy selected "
                                         "text (with mouse) to clipboard"))
            self.selectall_action = create_action(self,
                                       translate("SimpleEditor", "Select all"),
                                       shortcut=keybinding('SelectAll'),
                                       icon=get_icon('selectall.png'),
                                       triggered=self.global_callback,
                                       data="selectAll")
            self.edit_menu_actions = [self.undo_action, self.redo_action,
                                      None, self.cut_action, self.copy_action,
                                      self.paste_action, self.delete_action,
                                      self.alwayscopyselection_action, None,
                                      self.selectall_action, None,
                                      self.find_action, self.replace_action,
                                      ]

        namespace = None
        if not self.light:
            # File menu
            self.file_menu = self.menuBar().addMenu(self.tr("&File"))
            self.connect(self.file_menu, SIGNAL("aboutToShow()"),
                         self.update_file_menu)
            
            # Edit menu
            self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
            add_actions(self.edit_menu, self.edit_menu_actions)
            self.connect(self.edit_menu, SIGNAL("aboutToShow()"),
                         self.update_edit_menu)
                    
            # View menu
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
                
        # Console widget: window's central widget
        self.console = Console(self, namespace, self.commands, self.message,
                               self.debug, self.closing, self.profile)
        if self.light:
            self.setCentralWidget(self.console)
            self.widgetlist.append(self.console)
        else:
            self.add_dockwidget(self.console)
        
        # Working directory changer widget
        self.workdir = WorkingDirectory( self, self.init_workdir )
        self.addToolBar(self.workdir) # new mainwindow toolbar
        self.connect(self.console.shell, SIGNAL("refresh()"),
                     self.workdir.refresh)
        if not self.light:
            self.view_menu.addAction(self.workdir.toggleViewAction())
        
        if not self.light:
            # Console widget (...)
            self.connect(self.console.shell, SIGNAL("status(QString)"), 
                         self.send_to_statusbar)

            # Editor widget
            self.set_splash(self.tr("Loading editor widget..."))
            self.editor = Editor( self )
            self.connect(self.editor, SIGNAL("open_dir(QString)"),
                         self.workdir.chdir)
            self.add_dockwidget(self.editor)
            self.add_to_menubar(self.editor, self.tr("&Source"))
            self.add_to_toolbar(self.editor)
        
            # Workspace
            if self.workspace is not None:
                self.set_splash(self.tr("Loading workspace widget..."))
                self.add_dockwidget(self.workspace)
                self.toolbar.addSeparator()
                self.add_to_toolbar(self.workspace)
                self.workspace.set_interpreter(self.console.shell.interpreter)
                self.connect(self.console.shell, SIGNAL("refresh()"),
                             self.workspace.refresh)

            # Explorer
            if CONF.get('explorer', 'enable'):
                self.explorer = Explorer(self)
                self.add_dockwidget(self.explorer)
                self.connect(self.workdir, SIGNAL("set_previous_enabled(bool)"),
                             self.explorer.previous_button.setEnabled)
                self.connect(self.workdir, SIGNAL("set_next_enabled(bool)"),
                             self.explorer.next_button.setEnabled)
                self.connect(self.explorer, SIGNAL("open_dir(QString)"),
                             self.workdir.chdir)
                self.connect(self.explorer, SIGNAL("open_previous_dir()"),
                             self.workdir.previous_directory)
                self.connect(self.explorer, SIGNAL("open_next_dir()"),
                             self.workdir.next_directory)
                self.connect(self.explorer, SIGNAL("open_parent_dir()"),
                             self.workdir.parent_directory)
                self.connect(self.explorer, SIGNAL("edit(QString)"),
                             self.editor.load)
                self.connect(self.explorer, SIGNAL("open_workspace(QString)"),
                             self.workspace.load)
                self.connect(self.explorer, SIGNAL("run(QString)"),
                             lambda filename: \
                             self.console.run_script(filename=filename,
                                                     silent=True,
                                                     set_focus=True))
                self.connect(self.console.shell, SIGNAL("refresh()"),
                             self.explorer.refresh)
                self.connect(self.workdir, SIGNAL("chdir()"),
                             self.explorer.refresh)

            # History log widget
            if CONF.get('historylog', 'enable'):
                self.set_splash(self.tr("Loading history widget..."))
                self.historylog = HistoryLog( self )
                self.add_dockwidget(self.historylog)
                self.historylog.set_interpreter(self.console.shell.interpreter)
                self.connect(self.console.shell, SIGNAL("refresh()"),
                             self.historylog.refresh)
        
            # Doc viewer widget
            if CONF.get('docviewer', 'enable'):
                self.set_splash(self.tr("Loading docviewer widget..."))
                self.docviewer = DocViewer( self )
                self.docviewer.set_interpreter(self.console.shell.interpreter)
                self.add_dockwidget(self.docviewer)
                self.console.shell.set_docviewer(self.docviewer)
        
        if not self.light:
            # File menu
            self.file_menu_actions = [self.editor.new_action,
                                      self.editor.open_action,
                                      self.editor.save_action,
                                      self.editor.save_as_action, None,
                                      self.editor.close_action,
                                      self.editor.close_all_action, None,
                                      self.console.quit_action,
                                      ]

            # Console menu
            self.console.menu_actions = self.console.menu_actions[:-2]
            restart_action = create_action(self,
               self.tr("Restart Python interpreter"),
               tip=self.tr("Start a new Python shell: this will remove all current session objects, except for the workspace data which may be transferred from one session to another"),
               icon=get_icon('restart.png'),
               triggered=self.restart_interpreter)
            self.console.menu_actions += [None, restart_action]
            self.add_to_menubar(self.console)
            
            # Workspace menu
            self.add_to_menubar(self.workspace)
            
            # View menu
            self.menuBar().addMenu(self.view_menu)
        
            # ? menu
            help_menu = self.menuBar().addMenu("?")
            help_menu.addAction(create_action(self,
                self.tr("About %1...").arg("Pydee"),
                icon=get_std_icon('MessageBoxInformation'),
                triggered=self.about))
            if self.console.shell.help_action is not None:
                help_menu.addAction(self.console.shell.help_action)
                
        # Window set-up
        section = 'lightwindow' if self.light else 'window'
        width, height = CONF.get(section, 'size')
        self.resize( QSize(width, height) )
        self.window_size = self.size()
        posx, posy = CONF.get(section, 'position')
        self.move( QPoint(posx, posy) )
        
        if not self.light:
            # Always copy selection feature
            state = CONF.get('global', 'copy_selection', False)
            self.alwayscopyselection_action.setChecked(state)
            self.toggle_alwayscopyselection(state)
            # Window layout
            hexstate = CONF.get(section, 'state')
            self.restoreState( QByteArray().fromHex(hexstate) )
            # Is maximized?
            if CONF.get(section, 'is_maximized'):
                self.setWindowState(Qt.WindowMaximized)
            
        self.splash.hide()
        
        # Enabling tear off for all menus except help menu
        for child in self.menuBar().children():
            if isinstance(child, QMenu) and child != help_menu:
                child.setTearOffEnabled(True)
        
        # Give focus to shell widget
        self.console.shell.setFocus()
        
    def update_file_menu(self):
        """Update file menu to show recent files"""
        self.file_menu.clear()
        add_actions(self.file_menu, self.file_menu_actions[:-1])
        recent_files = []
        for fname in self.editor.recent_files:
            if (fname not in self.editor.filenames) and os.path.isfile(fname):
                recent_files.append(fname)
        if recent_files:
            self.file_menu.addSeparator()
            for i, fname in enumerate(recent_files):
                action = create_action(self,
                                       "&%d %s" % (i+1,
                                                   os.path.basename(fname)),
                                       icon=get_filetype_icon(fname),
                                       triggered=self.editor.load)
                action.setData(QVariant(fname))
                self.file_menu.addAction(action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.file_menu_actions[-1])
        
    def update_edit_menu(self):
        """Update edit menu"""
        #FIXME: Update the edit actions by another mean
        #       -> currently, when clicking on a plugin, these actions aren't
        #          updated (the problem is: they are also in app toolbar!)
        widget = self.which_has_focus()        
        not_readonly = widget in [self.editor, self.console]
        
        # Editor has focus and there is no file opened in it
        no_file = (widget == self.editor) and not self.editor.tabwidget.count()
        for child in self.edit_menu.actions():
            child.setEnabled(not no_file)
        if no_file:
            return

        self.replace_action.setEnabled(not_readonly and widget != self.console)
        editor = self.get_editor(widget)
        
        undoredo = (editor is not None) and not_readonly \
                              and widget != self.console
        self.undo_action.setEnabled( undoredo and editor.isUndoAvailable() )
        self.redo_action.setEnabled( undoredo and editor.isRedoAvailable() )
        
        has_selection = (editor is not None) and editor.hasSelectedText()
        self.copy_action.setEnabled(has_selection)
        self.cut_action.setEnabled(has_selection and not_readonly)
        self.paste_action.setEnabled(not_readonly)    
        self.delete_action.setEnabled(has_selection and not_readonly)
        
        # Disable the following actions for non-editor-based widgets
        if widget is None:
            self.selectall_action.setEnabled(False)
            self.find_action.setEnabled(False)
            if self.workspace.hasFocus():
                self.paste_action.setEnabled(True)
        
    def set_splash(self, message):
        """Set splash message"""
        self.splash.show()
        self.splash.showMessage(message,
                    Qt.AlignBottom | Qt.AlignRight | Qt.AlignAbsolute,
                    QColor(Qt.gray))
        QApplication.processEvents()
        
    def closeEvent(self, event):
        """closeEvent reimplementation"""
        if self.closing(True):
            event.accept()
        else:
            event.ignore()
            
    def resizeEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized():
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)
        
    def closing(self, cancelable=False):
        """Exit tasks"""
        if self.already_closed:
            return True
        size = self.window_size
        section = 'lightwindow' if self.light else 'window'
        CONF.set(section, 'size', (size.width(), size.height()))
        CONF.set(section, 'is_maximized', self.isMaximized())
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
        
        # Matplotlib figures
        from PyQtShell.plugins.figure import MatplotlibFigure
        if isinstance(child, MatplotlibFigure):
            dockwidget.setVisible(True)
            # Tabifying
            if self.widgetlist:
                last_object = self.widgetlist[-1]
                if (last_object.dockwidget is None) \
                   or last_object.dockwidget.isWindow():
                    # last_object is floating
                    dockwidget.setFloating(True)
                    size = QSize(*CONF.get('figure', 'size'))
                    if isinstance(last_object, MatplotlibFigure):
                        size = last_object.size()
                    dockwidget.resize(size)
                else:
                    # last_object is docked
                    self.tabifyDockWidget(last_object.dockwidget, dockwidget)
        else:
            # Matplotlib figures are not added to view menu
            # because closing a figure will not hide it but delete it
            self.view_menu.addAction(dockwidget.toggleViewAction())
                
        self.widgetlist.append(child)
    
    def add_to_menubar(self, widget, title=None):
        """Add menu and actions to menubar"""
        actions = widget.menu_actions
        if actions is not None:
            if not title:
                title = widget.get_widget_title()
            menu = self.menuBar().addMenu(title)
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
            self.tr("About %1").arg("Pydee"),
            self.tr("""<b>%1</b> v %2
            <br>PYthon Development EnvironmEnt
            <p>Copyright &copy; 2009 Pierre Raybaut
            <br>Licensed under the terms of the  
            <a href="http://www.fsf.org/licensing/">GNU GPL v2</a>
            <p><i>Project manager and main developer:</i> Pierre Raybaut
            <br><i>Contributors:</i> Christopher Brown, Alexandre Radicchi, Brian Clowers
            <p>Most of the icons are coming from the <i>Crystal Project</i>:
            <br>Copyright &copy; 2006-2007 Everaldo Coelho
            <p>Pydee is based on PyQtShell module v %2
            <br>Bug reports and feature requests: 
            <a href="http://code.google.com/p/pyqtshell/">Google Code</a><br>
            Discussions around the project: 
            <a href="http://groups.google.com/group/pyqtshell">Google Group</a>
            <p>This project is part of 
            <a href="http://www.pythonxy.com">Python(x,y) distribution</a>
            <p>Python %3, Qt %4, PyQt %5%6 on %7""") \
            .arg("Pydee").arg(__version__) \
            .arg(platform.python_version()).arg(QT_VERSION_STR) \
            .arg(PYQT_VERSION_STR).arg(qsci).arg(platform.system()))
            
    def send_to_statusbar(self, message):
        """Show a message in the status bar"""
        self.statusBar().showMessage(message)
        
    def which_has_focus(self, widget_list=WIDGET_LIST,
                        default_widget = 'editor'):
        """Which widget has focus?"""
        def children_has_focus(widget, iter=0):
            iter += 1
            for child in widget.children():
                if hasattr(child, "hasFocus"):
                    if child.hasFocus():
                        return True
                if children_has_focus(child, iter):
                    return True
            return False
        for widget_name in widget_list:
            widget = getattr(self, widget_name)
            callback = getattr( widget, "hasFocus" )
            has_focus = callback() or children_has_focus(widget)
            if has_focus:
                return getattr(self, widget_name)
    
    def find(self):
        """Global find callback"""
        widget = self.which_has_focus()
        if widget:
            widget.find_widget.show()
            widget.find_widget.edit.setFocus()
            return widget
        
    def replace(self):
        """Global replace callback"""
        widget = self.find()
        if widget:
            widget.find_widget.show_replace()
    
    def get_editor(self, widget):
        """Return editor for given widget"""
        if widget == self.console:
            return self.console.shell
        elif widget in [self.docviewer, self.historylog]:
            return widget.editor
        elif widget == self.editor:
            if self.editor.tabwidget.count():
                return self.editor.editors[self.editor.tabwidget.currentIndex()]

    def global_callback(self):
        """Global callback"""
        widget = self.which_has_focus()
        action = self.sender()
        callback = unicode(action.data().toString())
        if widget:
            getattr( self.get_editor(widget), callback )()
        elif self.workspace.hasFocus():
            if hasattr(self.workspace, callback):
                getattr(self.workspace, callback)()
            
    def toggle_alwayscopyselection(self, state):
        """Toggle always copy selection feature"""
        for widget_name in WIDGET_LIST:
            if hasattr(self, widget_name):
                editor = self.get_editor( getattr(self, widget_name))
                editor.always_copy_selection = state
                
    def restart_interpreter(self):
        """Restart Python interpreter"""
        answer = QMessageBox.warning(self, self.tr("Restart Python interpreter"),
                    self.tr("Python interpreter will be restarted: all the objects created during this session will be lost (that includes imported modules which will have to be imported again).\n\nDo you want to continue?"),
                    QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.No:
            return
        namespace = self.workspace.get_namespace()
        if namespace:
            answer = QMessageBox.question(self, self.tr("Workspace"),
                        self.tr("Do you want to keep workspace data available?"),
                        QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                namespace = None
        interpreter = self.console.shell.start_interpreter(namespace)
        self.workspace.set_interpreter(interpreter)
        self.historylog.set_interpreter(interpreter)
        self.docviewer.set_interpreter(interpreter)

        
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
    parser.add_option('-a', '--all', dest="all", action='store_true',
                      default=False,
                      help="Import all optional modules (options below)")
    parser.add_option('-p', '--pylab', dest="pylab", action='store_true',
                      default=False,
                      help="Import pylab in interactive mode"
                           " and add option --numpy")
    parser.add_option('-o', '--os', dest="os", action='store_true',
                      default=False,
                      help="Import os and os.path as osp")
    parser.add_option('--numpy', dest="numpy", action='store_true',
                      default=False,
                      help="Import numpy as N")
    parser.add_option('--scipy', dest="scipy", action='store_true',
                      default=False,
                      help="Import numpy as N, scipy as S")
    parser.add_option('-d', '--debug', dest="debug", action='store_true',
                      default=False,
                      help="Debug mode (stds are not redirected)")
    parser.add_option('--profile', dest="profile", action='store_true',
                      default=False,
                      help="Profile mode (internal test, "
                           "not related with Python profiling)")
    options, _args = parser.parse_args()
    
    messagelist = []
    intitlelist = []
    commands = []
    
    # Option --all
    if options.all:
        intitlelist.append('all')
        messagelist.append('import all optional modules')
        commands.extend(['import sys',
                         'import time',
                         'import re'])
        options.os = True
        options.pylab = True
        options.scipy = True
    
    # Option --modules (import modules)
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

    # Option --os
    if options.os:
        commands.extend(['import os',
                         'import os.path as osp'])
        if not options.all:
            messagelist.append('os')
    
    # Options --pylab, --numpy, --scipy
    def addoption(name, command):
        commands.append(command)
        if not options.all:
            messagelist.append('%s (%s)' % (name, command))
            intitlelist.append(name)
    if options.pylab:
        options.numpy = True
        addoption('pylab', 'from pylab import *')
    if options.scipy:
        options.numpy = True
        addoption('scipy', 'import scipy as S')
    if options.numpy:
        addoption('numpy', 'import numpy as N')
        
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
        
    # Options shown in console
    message = ""
    if messagelist:
        message = 'Option%s: ' % ('s' if len(messagelist)>1 else '')
        message += ", ".join(messagelist)
        
    # Options shown in Pydee's application title bar
    intitle = ""
    if intitlelist:
        intitle = ", ".join(intitlelist)

    return commands, intitle, message, options


def main():
    """Pydee application"""
    app = QApplication(sys.argv)
    
    #----Monkey patching PyQt4.QtGui.QApplication
    class FakeQApplication(QApplication):
        """Pydee's fake QApplication"""
        def __init__(self, args):
            self = app
        def exec_(self):
            """Do nothing because the Qt mainloop is already running"""
            pass
    from PyQt4 import QtGui
    QtGui.QApplication = FakeQApplication
    
    #----Monkey patching sys.exit
    def fake_sys_exit(arg=[]):
        pass
    sys.exit = fake_sys_exit
    
    # Translation
    locale = QLocale.system().name()
    qt_translator = QTranslator()
    if qt_translator.load("qt_" + locale,
                          QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        app.installTranslator(qt_translator)
    app_translator = QTranslator()
    app_path = os.path.dirname(__file__)
    if app_translator.load("pydee_" + locale, app_path):
        app.installTranslator(app_translator)
    
    # Options
    commands, intitle, message, options = get_options()
    
    # Main window
    main = MainWindow(commands, intitle, message, options)
    
    #----Patching matplotlib's FigureManager
    if options.pylab:
        # Customizing matplotlib's parameters
        from matplotlib import rcParams
        rcParams['font.size'] = CONF.get('figure', 'font/size')
        rcParams["interactive"]=True # interactive mode
        rcParams["backend"]="Qt4Agg" # using Qt4 to render figures
        bgcolor = unicode( \
                    QLabel().palette().color(QLabel().backgroundRole()).name() )
        rcParams['figure.facecolor'] = CONF.get('figure', 'facecolor', bgcolor)
        
        # Monkey patching matplotlib's figure manager for better integration
        from matplotlib.backends import backend_qt4
        from PyQtShell.plugins.figure import MatplotlibFigure
        import matplotlib
        
        # ****************************************************************
        # *  FigureManagerQT
        # ****************************************************************
        class FigureManagerQT( backend_qt4.FigureManagerQT ):
            """
            Patching matplotlib...
            """
            def __init__( self, canvas, num ):
                if backend_qt4.DEBUG: print 'FigureManagerQT.%s' % backend_qt4.fn_name()
                backend_qt4.FigureManagerBase.__init__( self, canvas, num )
                self.canvas = canvas
                self.window = MatplotlibFigure(main, canvas, num)
                self.window.setAttribute(Qt.WA_DeleteOnClose)
        
                image = os.path.join( matplotlib.rcParams['datapath'],'images','matplotlib.png' )
                self.window.setWindowIcon(QIcon( image ))
        
                # Give the keyboard focus to the figure instead of the manager
                self.canvas.setFocusPolicy( Qt.ClickFocus )
                self.canvas.setFocus()
        
                QObject.connect( self.window, SIGNAL( 'destroyed()' ),
                                    self._widgetclosed )
                self.window._destroying = False
        
                self.toolbar = self._get_toolbar(self.canvas, self.window)
                self.window.addToolBar(self.toolbar)
                QObject.connect(self.toolbar, SIGNAL("message"),
                        self.window.statusBar().showMessage)
        
        #        self.window.setCentralWidget(self.canvas)
        
                if matplotlib.is_interactive():
                    main.add_dockwidget(self.window)
                    main.console.shell.setFocus()
        
                # attach a show method to the figure for pylab ease of use
                self.canvas.figure.show = lambda *args: self.window.show()
                
                self.canvas.axes = self.canvas.figure.add_subplot(111)
        
                def notify_axes_change( fig ):
                    # This will be called whenever the current axes is changed
                    if self.toolbar != None: self.toolbar.update()
                self.canvas.figure.add_axobserver( notify_axes_change )
        # ****************************************************************
        backend_qt4.FigureManagerQT = FigureManagerQT
        
        # ****************************************************************
        # *  NavigationToolbar2QT
        # ****************************************************************
        from PyQtShell.widgets.figureoptions import figure_edit
        class NavigationToolbar2QT( backend_qt4.NavigationToolbar2QT ):
            def _init_toolbar(self):
                super(NavigationToolbar2QT, self)._init_toolbar()
                a = self.addAction(get_icon("customize.png"),
                                   'Customize', self.edit_parameters)
                a.setToolTip('Edit curves line and axes parameters')
            def edit_parameters(self):
                figure_edit(self.canvas, self)
            def save_figure( self ):
                main.console.shell.restore_stds()
                super(NavigationToolbar2QT, self).save_figure()
                main.console.shell.redirect_stds()
            def set_cursor( self, cursor ):
                if backend_qt4.DEBUG: print 'Set cursor' , cursor
                self.parent().setCursor( QCursor(backend_qt4.cursord[cursor]) )
        # ****************************************************************
        backend_qt4.NavigationToolbar2QT = NavigationToolbar2QT
        
    main.setup()
    main.show()
    app.exec_()


if __name__ == "__main__":
    main()