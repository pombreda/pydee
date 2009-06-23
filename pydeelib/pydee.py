# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
Pydee
"""

#TODO: Explorer: add regexp options to define included/excluded files (formlayout)
#TODO: External console: add history length option (or move the interactive console option?)

import sys, os, platform, re, webbrowser
import os.path as osp

# Force Python to search modules in the current directory first:
sys.path[0] = ''

# For debugging purpose only
STDOUT = sys.stdout

from PyQt4.QtGui import (QApplication, QMainWindow, QSplashScreen, QPixmap,
                         QMessageBox, QMenu, QIcon, QLabel, QCursor, QColor)
from PyQt4.QtCore import (SIGNAL, PYQT_VERSION_STR, QT_VERSION_STR, QPoint, Qt,
                          QLibraryInfo, QLocale, QTranslator, QSize, QByteArray,
                          QObject, QVariant)

# Local imports
from pydeelib import __version__, encoding
from pydeelib.widgets.pathmanager import PathManager
from pydeelib.plugins.console import Console
from pydeelib.plugins.workdir import WorkingDirectory
from pydeelib.plugins.editor import Editor
from pydeelib.plugins.history import HistoryLog
from pydeelib.plugins.docviewer import DocViewer
from pydeelib.plugins.workspace import Workspace
from pydeelib.plugins.explorer import Explorer
from pydeelib.plugins.externalconsole import ExternalConsole
from pydeelib.plugins.findinfiles import FindInFiles
from pydeelib.qthelpers import (create_action, add_actions, get_std_icon,
                                 keybinding, translate, get_filetype_icon,
                                 add_module_dependent_bookmarks)
from pydeelib.config import get_icon, get_image_path, CONF, get_conf_path


def get_python_doc_path():
    """
    Return Python documentation path
    (Windows: return the PythonXX.chm path if available)
    """
    python_doc = ''
    doc_path = osp.join(sys.prefix, "Doc")
    if osp.isdir(doc_path):
        if os.name == 'nt':
            python_chm = [ path for path in  os.listdir(doc_path) \
                           if re.match(r"Python[0-9]{2}.chm", path) ]
            if python_chm:
                python_doc = osp.join(doc_path, python_chm[0])
        if not python_doc:
            python_doc = osp.join(doc_path, "index.html")
    if osp.isfile(python_doc):
        return python_doc
    
def open_python_doc():
    """
    Open Python documentation
    (Windows: open .chm documentation if found)
    """
    python_doc = get_python_doc_path()
    if os.name == 'nt':
        os.startfile(python_doc)
    else:
        webbrowser.open(python_doc)


#TODO: Improve the stylesheet below for separator handles to be visible
#      (in Qt, these handles are by default not visible!)
STYLESHEET="""
QSplitter::handle {
    margin-left: 4px;
    margin-right: 4px;
}

QSplitter::handle:horizontal {
    width: 1px;
    border-width: 0px;
    background-color: lightgray;
}

QSplitter::handle:vertical {
    border-top: 2px ridge lightgray;
    border-bottom: 2px;
}

QMainWindow::separator:vertical {
    margin-left: 1px;
    margin-top: 25px;
    margin-bottom: 25px;
    border-left: 2px groove lightgray;
    border-right: 1px;
}

QMainWindow::separator:horizontal {
    margin-top: 1px;
    margin-left: 5px;
    margin-right: 5px;
    border-top: 2px groove lightgray;
    border-bottom: 2px;
}
"""

class MainWindow(QMainWindow):
    """Pydee main window"""
    
    pydee_path = get_conf_path('.path')
    BOOKMARKS = (
         ('PyQt4',
          "http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/pyqt4ref.html",
          translate("MainWindow", "PyQt4 Reference Guide")),
         ('PyQt4',
          "http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/classes.html",
          translate("MainWindow", "PyQt4 API Reference")),
         ('xy', "http://www.pythonxy.com",
          translate("MainWindow", "Python(x,y)")),
         ('numpy', "http://docs.scipy.org/doc/",
          translate("MainWindow", "Numpy and Scipy documentation")),
         ('matplotlib', "http://matplotlib.sourceforge.net/contents.html",
          translate("MainWindow", "Matplotlib documentation")),
                ) 
    
    def __init__(self, commands=None, intitle="", message="", options=None):
        super(MainWindow, self).__init__()
        
#        self.setStyleSheet(STYLESHEET)
        
        # Area occupied by a dock widget can be split in either direction
        # to contain more dock widgets:
        self.setDockNestingEnabled(True)
        
        # Loading Pydee path
        self.path = []
        if osp.isfile(self.pydee_path):
            self.path, _ = encoding.readlines(self.pydee_path)
            self.path = [name for name in self.path if os.path.isdir(name)]
        self.remove_path_from_sys_path()
        self.add_path_to_sys_path()
        self.pydee_path_action = create_action(self,
                                        self.tr("Path manager..."),
                                        None, 'folder_new.png',
                                        triggered=self.path_manager_callback,
                                        tip=self.tr("Open Pydee path manager"))
        
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
        self.extconsole = None
        self.findinfiles = None
        
        # Set Window title and icon
        title = "Pydee"
        if intitle:
            title += " (%s)" % intitle
        self.setWindowTitle(title)
        self.setWindowIcon(get_icon('pydee.png'))
        
        # Showing splash screen
        pixmap = QPixmap(get_image_path('splash.png'), 'png')
        self.splash = QSplashScreen(pixmap)
        if not self.light:
            self.splash.show()
            self.set_splash(self.tr("Initializing..."))
        
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
            self.findinfiles_action = create_action(self,
                                self.tr("&Find in files"),
                                "Ctrl+Shift+F", 'findf.png',
                                triggered=self.findinfiles_callback,
                                tip=self.tr("Search text in multiple files"))        
            def create_edit_action(text, icon_name):
                return create_action(self, translate("SimpleEditor", text),
                                     shortcut=keybinding(text),
                                     icon=get_icon(icon_name),
                                     triggered=self.global_callback,
                                     data=text.lower(),
                                     window_context=False)
            self.undo_action = create_edit_action("Undo",'undo.png')
            self.redo_action = create_edit_action("Redo", 'redo.png')
            self.copy_action = create_edit_action("Copy", 'editcopy.png')
            self.cut_action = create_edit_action("Cut", 'editcut.png')
            self.paste_action = create_edit_action("Paste", 'editpaste.png')
            self.delete_action = create_action(self,
                                       translate("SimpleEditor", "Delete"),
                                       icon=get_icon('editdelete.png'),
                                       triggered=self.global_callback,
                                       data="delete")
            self.selectall_action = create_action(self,
                                       translate("SimpleEditor", "Select all"),
                                       shortcut=keybinding('SelectAll'),
                                       icon=get_icon('selectall.png'),
                                       triggered=self.global_callback,
                                       data="selectAll")
            self.edit_menu_actions = [self.undo_action, self.redo_action,
                                      None, self.cut_action, self.copy_action,
                                      self.paste_action, self.delete_action,
                                      None, self.selectall_action]
            self.search_menu_actions = [self.find_action, self.replace_action]

        namespace = None
        if not self.light:
            # File menu
            self.file_menu = self.menuBar().addMenu(self.tr("&File"))
            self.connect(self.file_menu, SIGNAL("aboutToShow()"),
                         self.update_file_menu)
            
            # Edit menu
            self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
            add_actions(self.edit_menu, self.edit_menu_actions)
            
            # Search menu
            self.search_menu = self.menuBar().addMenu(self.tr("&Search"))
            add_actions(self.search_menu, self.search_menu_actions)
                    
            # Status bar
            status = self.statusBar()
            status.setObjectName("StatusBar")
            status.showMessage(self.tr("Welcome to Pydee!"), 5000)
            
            # Workspace init
            if CONF.get('workspace', 'enable'):
                self.set_splash(self.tr("Loading workspace..."))
                self.workspace = Workspace(self)
                self.connect(self.workspace, SIGNAL('focus_changed()'),
                             self.plugin_focus_changed)
                self.connect(self.workspace, SIGNAL('redirect_stdio(bool)'),
                             self.redirect_interactiveshell_stdio)
                namespace = self.workspace.namespace
                
        # Console widget: window's central widget
        self.console = Console(self, namespace, self.commands, self.message,
                               self.debug, self.closing, self.profile)
        if self.light:
            self.setCentralWidget(self.console)
            self.widgetlist.append(self.console)
        else:
            self.connect(self.console, SIGNAL('focus_changed()'),
                         self.plugin_focus_changed)
            self.add_dockwidget(self.console)
        
        # Working directory changer widget
        self.workdir = WorkingDirectory( self, self.init_workdir )
        self.addToolBar(self.workdir) # new mainwindow toolbar
        self.connect(self.workdir, SIGNAL('redirect_stdio(bool)'),
                     self.redirect_interactiveshell_stdio)
        self.connect(self.console.shell, SIGNAL("refresh()"),
                     self.workdir.refresh)
        
        if not self.light:
            # Console widget (...)
            self.connect(self.console.shell, SIGNAL("status(QString)"), 
                         self.send_to_statusbar)

            # Editor widget
            self.set_splash(self.tr("Loading editor widget..."))
            self.editor = Editor( self )
            self.connect(self.editor, SIGNAL('focus_changed()'),
                         self.plugin_focus_changed)
            self.connect(self.console, SIGNAL("edit_goto(QString,int)"),
                         self.editor.load)            
            self.connect(self.editor, SIGNAL("open_dir(QString)"),
                         self.workdir.chdir)
            self.connect(self.editor,
                         SIGNAL("open_external_console(QString,QString,bool,bool,bool)"),
                         self.open_external_console)
            self.connect(self.editor, SIGNAL('redirect_stdio(bool)'),
                         self.redirect_interactiveshell_stdio)
            self.add_dockwidget(self.editor)
            self.add_to_menubar(self.editor, self.tr("&Source"))
            self.add_to_toolbar(self.editor)
        
            # Seach actions in toolbar
            toolbar_search_actions = [self.find_action, self.replace_action]
        
            # Find in files
            if CONF.get('find_in_files', 'enable'):
                self.findinfiles = FindInFiles(self)
                self.add_dockwidget(self.findinfiles)
                self.connect(self.findinfiles, SIGNAL("edit_goto(QString,int)"),
                             self.editor.load)
                self.connect(self.findinfiles, SIGNAL('redirect_stdio(bool)'),
                             self.redirect_interactiveshell_stdio)
                self.connect(self, SIGNAL('find_files(QString)'),
                             self.findinfiles.set_search_text)
                self.connect(self.workdir, SIGNAL("chdir()"),
                             self.findinfiles.refreshdir)
                self.search_menu.addSeparator()
                self.search_menu.addAction(self.findinfiles_action)
                toolbar_search_actions.append(self.findinfiles_action)
                
            self.toolbar.addSeparator()
            for action in toolbar_search_actions:
                self.toolbar.addAction(action)
            
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
                self.connect(self.editor, SIGNAL("refresh_explorer()"),
                             self.explorer.refresh)

            # History log widget
            if CONF.get('historylog', 'enable'):
                self.set_splash(self.tr("Loading history widget..."))
                self.historylog = HistoryLog( self )
                self.connect(self.historylog, SIGNAL('focus_changed()'),
                             self.plugin_focus_changed)
                self.add_dockwidget(self.historylog)
                self.historylog.set_rawhistory(self.console.shell.rawhistory)
                self.connect(self.console.shell, SIGNAL("refresh()"),
                             self.historylog.refresh)
        
            # Doc viewer widget
            if CONF.get('docviewer', 'enable'):
                self.set_splash(self.tr("Loading docviewer widget..."))
                self.docviewer = DocViewer( self )
                self.connect(self.docviewer, SIGNAL('focus_changed()'),
                             self.plugin_focus_changed)
                self.docviewer.set_interpreter(self.console.shell.interpreter)
                self.add_dockwidget(self.docviewer)
                self.console.set_docviewer(self.docviewer)
        
        if not self.light:
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
            
            # External console menu
            self.extconsole = ExternalConsole(self, self.commands)
            self.extconsole.set_docviewer(self.docviewer)
            self.connect(self.extconsole, SIGNAL("edit_goto(QString,int)"),
                         self.editor.load)
            self.connect(self.extconsole, SIGNAL('redirect_stdio(bool)'),
                         self.redirect_interactiveshell_stdio)
            self.add_dockwidget(self.extconsole)
            self.add_to_menubar(self.extconsole)
            
            # View menu
            self.view_menu = self.createPopupMenu()
            self.view_menu.setTitle(self.tr("&View"))
            self.menuBar().addMenu(self.view_menu)
        
            # ? menu
            help_menu = self.menuBar().addMenu("?")
            help_menu.addAction(create_action(self,
                self.tr("About %1...").arg("Pydee"),
                icon=get_std_icon('MessageBoxInformation'),
                triggered=self.about))
            if self.console.shell.help_action is not None:
                help_menu.addAction(self.console.shell.help_action)
            if get_python_doc_path() is not None:
                pydoc_act = create_action(self, self.tr("Python documentation"),
                                          icon=get_icon('python.png'),
                                          triggered=open_python_doc)
                help_menu.addSeparator()
                help_menu.addAction(pydoc_act)
            if os.name == 'nt':
                # Qt assistant link: Windows only
                import PyQt4
                qta = osp.join(osp.dirname(PyQt4.__file__), "assistant.exe")
                if osp.isfile(qta):
                    qta_act = create_action(self, self.tr("Qt Assistant"),
                                            icon=get_icon('qtassistant.png'),
                                            triggered=lambda: os.startfile(qta))
                    help_menu.addAction(qta_act)
            add_module_dependent_bookmarks(self, help_menu, self.BOOKMARKS)
                
        # Window set-up
        section = 'lightwindow' if self.light else 'window'
        width, height = CONF.get(section, 'size')
        self.resize( QSize(width, height) )
        self.window_size = self.size()
        posx, posy = CONF.get(section, 'position')
        self.move( QPoint(posx, posy) )
        
        if not self.light:
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
        
        # Menu about to show
        for child in self.menuBar().children():
            if isinstance(child, QMenu):
                self.connect(child, SIGNAL("aboutToShow()"),
                             self.update_edit_menu)

    def give_focus_to_interactive_console(self):
        """Give focus to interactive shell widget"""
        self.console.shell.setFocus()
        
    def plugin_focus_changed(self):
        """Focus has changed from one plugin to another"""
        self.update_edit_menu()
        self.update_search_menu()
        
    def update_file_menu(self):
        """Update file menu to show recent files"""
        self.file_menu.clear()
        add_actions(self.file_menu, self.editor.file_menu_actions)
        add_actions(self.file_menu, [self.pydee_path_action])
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
        self.file_menu.addAction(self.console.quit_action)
        
    def __focus_widget_properties(self):
        widget = QApplication.focusWidget()
        from pydeelib.widgets.qscishell import QsciShell
        from pydeelib.widgets.qscibase import QsciBase
        scintilla_properties = None
        if isinstance(widget, QsciBase):
            console = isinstance(widget, QsciShell)
            not_readonly = not widget.isReadOnly()
            readwrite_editor = not_readonly and not console
            scintilla_properties = (console, not_readonly, readwrite_editor)
        return widget, scintilla_properties
        
    def update_edit_menu(self):
        """Update edit menu"""
        if self.menuBar().hasFocus():
            return
        # Disabling all actions to begin with
        for child in self.edit_menu.actions():
            child.setEnabled(False)        
        
        widget, scintilla_properties = self.__focus_widget_properties()
        if isinstance(widget, Workspace):
            self.paste_action.setEnabled(True)
            return
        elif scintilla_properties is None: # widget is not an editor/console
            return
        #!!! Below this line, widget is expected to be a QsciScintilla instance
        console, not_readonly, readwrite_editor = scintilla_properties
        
        # Editor has focus and there is no file opened in it
        if not console and not_readonly and not self.editor.tabwidget.count():
            return
        
        self.selectall_action.setEnabled(True)
        
        # Undo, redo
        self.undo_action.setEnabled( readwrite_editor \
                                     and widget.isUndoAvailable() )
        self.redo_action.setEnabled( readwrite_editor \
                                     and widget.isRedoAvailable() )

        # Copy, cut, paste, delete
        has_selection = widget.hasSelectedText()
        self.copy_action.setEnabled(has_selection)
        self.cut_action.setEnabled(has_selection and not_readonly)
        self.paste_action.setEnabled(not_readonly)
        self.delete_action.setEnabled(has_selection and not_readonly)
        
    def update_search_menu(self):
        """Update search menu"""
        if self.menuBar().hasFocus():
            return        
        # Disabling all actions to begin with
        for child in [self.find_action, self.replace_action]:
            child.setEnabled(False)
        
        _, scintilla_properties = self.__focus_widget_properties()
        if scintilla_properties is None: # widget is not an editor/console
            return
        #!!! Below this line, widget is expected to be a QsciScintilla instance
        _, _, readwrite_editor = scintilla_properties
        self.find_action.setEnabled(True)
        self.replace_action.setEnabled(readwrite_editor)
        self.replace_action.setEnabled(readwrite_editor)
        
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
        encoding.writelines(self.path, self.pydee_path) # Saving path
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
        
    def add_dockwidget(self, child):
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.create_dockwidget()
        self.addDockWidget(location, dockwidget)
        
        # Matplotlib figures
        from pydeelib.plugins.figure import MatplotlibFigure
        if isinstance(child, MatplotlibFigure):
            # Tabifying
            if self.widgetlist:
                last_object = self.widgetlist[-1]
                if isinstance(last_object, MatplotlibFigure):
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
                        self.tabifyDockWidget(last_object.dockwidget,
                                              dockwidget)
            dockwidget.setVisible(True)
            dockwidget.raise_()
                
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
            <br>Licensed under the terms of the MIT License
            <p><i>Project manager and main developer:</i> Pierre Raybaut
            <br><i>Contributors:</i> Christopher Brown, Alexandre Radicchi, Brian Clowers
            <p>Python code analysis powered by <i>pyflakes</i>:
            <br>Copyright (c) 2005 Divmod, Inc., http://www.divmod.com/
            <p>Most of the icons are coming from the <i>Crystal Project</i>:
            <br>Copyright &copy; 2006-2007 Everaldo Coelho
            <p>Pydee is based on pydeelib module v %2
            <br>Bug reports and feature requests: 
            <a href="http://code.google.com/p/pydee/">Google Code</a><br>
            Discussions around the project: 
            <a href="http://groups.google.com/group/pydee">Google Group</a>
            <p>This project is part of 
            <a href="http://www.pythonxy.com">Python(x,y) distribution</a>
            <p>Python %3, Qt %4, PyQt %5%6 on %7""") \
            .arg("Pydee").arg(__version__) \
            .arg(platform.python_version()).arg(QT_VERSION_STR) \
            .arg(PYQT_VERSION_STR).arg(qsci).arg(platform.system()))
            
    def send_to_statusbar(self, message):
        """Show a message in the status bar"""
        self.statusBar().showMessage(message)
    
    def get_current_editor_plugin(self):
        """Return editor plugin which has focus:
        console, extconsole, editor, docviewer or historylog"""
        widget = QApplication.focusWidget()
        from pydeelib.widgets.qscishell import QsciShell
        from pydeelib.widgets.qscibase import QsciBase
        if not isinstance(widget, QsciBase):
            return
        if widget is self.console.shell:
            plugin = self.console
        elif widget is self.historylog.editor:
            plugin = self.historylog
        elif widget is self.docviewer.editor:
            plugin = self.docviewer
        elif isinstance(widget, QsciShell):
            plugin = self.extconsole
        else:
            plugin = self.editor
        return plugin
    
    def find(self):
        """Global find callback"""
        plugin = self.get_current_editor_plugin()
        if plugin is not None:
            plugin.find_widget.show()
            plugin.find_widget.edit.setFocus()
            return plugin
        
    def replace(self):
        """Global replace callback"""
        plugin = self.find()
        if plugin is not None:
            plugin.find_widget.show_replace()
            
    def findinfiles_callback(self):
        """Find in files callback"""
        widget = QApplication.focusWidget()
        self.findinfiles.dockwidget.setVisible(True)
        self.findinfiles.dockwidget.raise_()
        from pydeelib.widgets.qscibase import QsciBase
        text = ''
        if isinstance(widget, QsciBase) and widget.hasSelectedText():
            text = widget.selectedText()
        self.emit(SIGNAL('find_files(QString)'), text)
    
    def global_callback(self):
        """Global callback"""
        widget = QApplication.focusWidget()
        action = self.sender()
        callback = unicode(action.data().toString())
        from pydeelib.widgets.qscibase import QsciBase
        if isinstance(widget, QsciBase):
            getattr(widget, callback)()
        elif isinstance(widget, Workspace):
            if hasattr(self.workspace, callback):
                getattr(self.workspace, callback)()
                
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
        self.docviewer.set_interpreter(interpreter)
        self.console.dockwidget.raise_()
        
    def redirect_interactiveshell_stdio(self, state):
        if state:
            self.console.shell.redirect_stds()
        else:
            self.console.shell.restore_stds()
        
    def open_external_console(self, fname, wdir,
                              ask_for_arguments, interact, debug):
        """Open external console"""
        self.extconsole.setVisible(True)
        self.extconsole.raise_()
        self.extconsole.start(unicode(fname), wdir,
                              ask_for_arguments, interact, debug)
        
    def add_path_to_sys_path(self):
        """Add Pydee path to sys.path"""
        for path in reversed(self.path):
            sys.path.insert(1, path)

    def remove_path_from_sys_path(self):
        """Remove Pydee path from sys.path"""
        sys_path = sys.path
        while sys_path[1] in self.path:
            sys_path.pop(1)
        
    def path_manager_callback(self):
        """Pydee path manager"""
        self.remove_path_from_sys_path()
        dialog = PathManager(self, self.path)
        self.connect(dialog, SIGNAL('redirect_stdio(bool)'),
                     self.redirect_interactiveshell_stdio)
        dialog.exec_()
        self.add_path_to_sys_path()
        #TODO: implement path manager in the rest of the application!!!
        #      -> external shell + update sys.path for interactive console

        
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
        messagelist += ['import (sys, time, re, os)', 'import os.path as osp',
                        'import numpy as N', 'import scipy as S',
                        'from pylab import *']
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
        commands.append('execfile(r"%s")' % filename)
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
    if CONF.get('main', 'translation'):
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
        from pydeelib.plugins.figure import MatplotlibFigure
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
        try:
            from pydeelib.widgets.figureoptions import figure_edit
        except ImportError, error:
            print >> STDOUT, error
            figure_edit = None
        class NavigationToolbar2QT( backend_qt4.NavigationToolbar2QT ):
            def _init_toolbar(self):
                super(NavigationToolbar2QT, self)._init_toolbar()
                if figure_edit:
                    a = self.addAction(get_icon("customize.png"),
                                       'Customize', self.edit_parameters)
                    a.setToolTip('Edit curves line and axes parameters')
            def edit_parameters(self):
                if figure_edit:
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
    main.give_focus_to_interactive_console()
    app.exec_()


if __name__ == "__main__":
    main()