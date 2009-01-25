# -*- coding: utf-8 -*-
"""PyQtShell widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os, cPickle
import os.path as osp
from PyQt4.QtGui import QWidget, QHBoxLayout, QFileDialog, QMessageBox, QFont
from PyQt4.QtGui import QLabel, QComboBox, QPushButton, QVBoxLayout, QLineEdit
from PyQt4.QtGui import QFontDialog, QInputDialog, QDockWidget, QSizePolicy
from PyQt4.QtGui import QToolTip, QCheckBox
from PyQt4.QtCore import Qt, SIGNAL

# Local import
import encoding
from dochelpers import getdoc, getsource
from qthelpers import create_action, get_std_icon
from config import get_font, set_font
from config import CONF, str2type

def toggle_actions(actions, enable):
    """Enable/disable actions"""
    if actions is not None:
        for action in actions:
            if action is not None:
                action.setEnabled(enable)

class WidgetMixin(object):
    """Useful methods to bind widgets to the main window"""
    def __init__(self, mainwindow):
        """Bind widget to a QMainWindow instance"""
        super(WidgetMixin, self).__init__()
        self.mainwindow = mainwindow
        if mainwindow is not None:
            mainwindow.connect(mainwindow, SIGNAL("closing()"), self.closing)
        self.menu_actions, self.toolbar_actions = self.set_actions()
        self.dockwidget = None
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        raise NotImplementedError
        
    def get_name(self, raw=True):
        """Return widget name"""
        raise NotImplementedError
    
    def set_actions(self):
        """Setup actions"""
        # Return menu and toolbar actions
        raise NotImplementedError
        
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        raise NotImplementedError
        
    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        allowed_areas, location = self.get_dockwidget_properties()
        dock = QDockWidget(self.get_name(raw=False), self.mainwindow)
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(self)
        self.dockwidget = dock
        return (dock, location)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        toggle_actions(self.menu_actions, enable)
        toggle_actions(self.toolbar_actions, enable)
    
    def chdir(self, dirname):
        """Change working directory"""
        self.mainwindow.workdir.chdir(dirname)


try:
    from qsciwidgets import QsciShell as ShellBaseWidget
    from qsciwidgets import QsciEditor as EditorBaseWidget
except ImportError:
    from qtwidgets import QtShell as ShellBaseWidget
    from qtwidgets import QtEditor as EditorBaseWidget


class Shell(ShellBaseWidget, WidgetMixin):
    """
    Shell widget
    """
    def __init__(self, namespace=None, commands=None, message="",
                 parent=None, debug=False):
        ShellBaseWidget.__init__(self, namespace, commands,
                                 message, parent, debug)
        WidgetMixin.__init__(self, parent)
        # Parameters
        self.set_font( get_font('shell') )
        self.set_wrap_mode( CONF.get('shell', 'wrap') )

    def get_banner(self):
        """Return interpreter banner and a one-line message"""
        return (self.tr('Type "copyright", "credits" or "license" for more information.'),
                self.tr('Type "object?" for details on "object"'))
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr("&Console")
        if raw:
            return name
        else:
            return name.replace("&", "")
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_history()
    
    def set_actions(self):
        """Setup actions"""
        run_action = create_action(self, self.tr("&Run..."), self.tr("Ctrl+R"),
            'run.png', self.tr("Run a Python script"),
            triggered=self.run_script)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set shell font style"),
            triggered=self.change_font)
        history_action = create_action(self, self.tr("History..."), None,
            'history.png', self.tr("Set history max entries"),
            triggered=self.change_history_depth)
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get('shell', 'wrap') )
        menu_actions = (run_action, None,
                        font_action, history_action, wrap_action)
        toolbar_actions = (run_action,)
        return menu_actions, toolbar_actions
        
    def run_script(self, filename=None, silent=False):
        """Run a Python script"""
        if filename is None:
            self.restore_stds()
            filename = QFileDialog.getOpenFileName(self,
                          self.tr("Run Python script"), os.getcwd(),
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.redirect_stds()
            if filename:
                filename = unicode(filename)
                os.chdir( os.path.dirname(filename) )
                filename = os.path.basename(filename)
                self.emit(SIGNAL("refresh()"))
            else:
                return
        command = "execfile('%s')" % filename
        self.setFocus()
        if silent:
            self.write(command+'\n')
            self.interpreter.runsource(command)
            self.write(self.prompt)
        else:
            self.write(command)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font('shell'),
                       self, self.tr("Select a new font"))
        if valid:
            self.set_font(font)
            set_font(font, 'shell')

    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInteger(self, self.tr('History'),
                           self.tr('Maximum entries'),
                           CONF.get('history', 'max_entries'), 10, 10000)
        if valid:
            CONF.set('history', 'max_entries', depth)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.set_wrap_mode(checked)


class PathComboBox(QComboBox):
    """
    QComboBox handling path locations
    """
    def __init__(self, parent):
        super(PathComboBox, self).__init__(parent)
        self.font = QFont()
        self.setEditable(True)
        self.connect(self, SIGNAL("editTextChanged(QString)"), self.validate)
        self.set_default_style()
        
    def show_tip(self, tip=""):
        """Show tip"""
        QToolTip.showText(self.mapToGlobal(self.pos()), tip, self)
        
    def set_default_style(self):
        """Set widget style to default"""
        self.font.setBold(False)
        self.setFont(self.font)
        self.setStyleSheet("")
        self.show_tip()
        
    def validate(self, qstr):
        """Validate entered path"""
        if self.hasFocus():
            self.font.setBold(True)
            self.setFont(self.font)
            if osp.isdir( unicode(qstr) ):
                self.setStyleSheet("color:rgb(50, 155, 50);")
                self.show_tip(self.tr("Press enter to validate this path"))
            else:
                self.setStyleSheet("color:rgb(200, 50, 50);")
                self.show_tip(self.tr('This path is incorrect.\nEnter a correct directory path.\nThen press enter to validate'))
        else:
            self.set_default_style()

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            directory = unicode(self.currentText())
            if osp.isdir( directory ):
                self.parent().chdir(directory)
                self.set_default_style()
                if hasattr(self.parent(), 'mainwindow'):
                    if self.parent().mainwindow is not None:
                        self.parent().mainwindow.shell.setFocus()
        else:
            QComboBox.keyPressEvent(self, event)
    

class WorkingDirectory(QWidget, WidgetMixin):
    """
    Working directory changer widget
    """
    log_path = osp.join(osp.expanduser('~'), '.workingdir')
    def __init__(self, parent, workdir=None):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        
        layout = QHBoxLayout()
        if self.mainwindow is None:
            # Not a dock widget
            layout.addWidget( QLabel(self.get_name()+':') )
        
        # Path combo box
        self.max_wdhistory_entries = CONF.get('shell', 'working_dir_history')
        self.pathedit = PathComboBox(self)
        wdhistory = self.load_wdhistory( workdir )
        if workdir is None:
            workdir = wdhistory[0]
        self.chdir( workdir )
        self.pathedit.addItems( wdhistory )
        self.refresh()
        layout.addWidget(self.pathedit)
        
        # Browse button
        self.browse_btn = QPushButton(get_std_icon('DirOpenIcon'), '')
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.setToolTip(self.tr('Browse a working directory'))
        self.connect(self.browse_btn, SIGNAL('clicked()'),
                     self.select_directory)
        layout.addWidget(self.browse_btn)
        
        # Parent dir button
        self.parent_btn = QPushButton(get_std_icon('FileDialogToParent'), '')
        self.parent_btn.setFixedWidth(30)
        self.parent_btn.setToolTip(self.tr('Change to parent directory'))
        self.connect(self.parent_btn, SIGNAL('clicked()'),
                     self.parent_directory)
        layout.addWidget(self.parent_btn)
        
        self.setLayout(layout)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
    def get_name(self, raw=True):
        """Return widget name"""
        return self.tr('Working directory')
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea,
                Qt.BottomDockWidgetArea)
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_wdhistory()
        
    def load_wdhistory(self, workdir=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.log_path):
            wdhistory = [line.replace('\n','')
                         for line in file(self.log_path, 'r').readlines()]
        else:
            if workdir is None:
                workdir = os.getcwd()
            wdhistory = [ workdir ]
        return wdhistory
    
    def save_wdhistory(self):
        """Save history to a text file in user home directory"""
        file(self.log_path, 'w').write("\n".join( \
            [ unicode( self.pathedit.itemText(index) )
                for index in range(self.pathedit.count()) ] ))
        
    def refresh(self):
        """Refresh widget"""
        curdir = os.getcwd()
        index = self.pathedit.findText(curdir)
        while index!=-1:
            self.pathedit.removeItem(index)
            index = self.pathedit.findText(curdir)
        self.pathedit.insertItem(0, curdir)
        self.pathedit.setCurrentIndex(0)
        
    def select_directory(self):
        """Select directory"""
        self.mainwindow.shell.restore_stds()
        directory = QFileDialog.getExistingDirectory(self.mainwindow,
                    self.tr("Select directory"), os.getcwd())
        if not directory.isEmpty():
            self.chdir(directory)
        self.mainwindow.shell.redirect_stds()
        
    def parent_directory(self):
        """Change working directory to parent directory"""
        os.chdir(os.path.join(os.getcwd(), os.path.pardir))
        self.refresh()
        
    def chdir(self, directory):
        """Set directory as working directory"""
        os.chdir( unicode(directory) )
        sys.path.append(os.getcwd())
        self.refresh()


#TODO: TabWidget to open more than one script at a time
#TODO: Link: edit with external editor
class Editor(EditorBaseWidget, WidgetMixin):
    """
    Editor widget
    """
    file_path = osp.join(osp.expanduser('~'), '.temp.py')
    def __init__(self, parent):
        EditorBaseWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        self.filename = None
        self.encoding = 'utf-8'
        self.load_temp_file()
        # Parameters
        self.set_font( get_font('editor') )
        self.set_wrap_mode( CONF.get('editor', 'wrap') )
        self.setup_margin( get_font('editor', 'margin') )
        self.connect(self, SIGNAL('modificationChanged(bool)'), self.change)

    def change(self, state=None):
        """Change DockWidget title depending on modified state"""
        if self.dockwidget is None:
            return
        if state is None:
            state = self.isModified()
        title = unicode( self.dockwidget.windowTitle() )
        if state:
            title += "*"
        elif title.endswith('*'):
            title = title[:-1]
        self.dockwidget.setWindowTitle(title)
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&Editor')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)

    def set_actions(self):
        """Setup actions"""
        open_action = create_action(self, self.tr("Open..."), None,
            'py_open.png', self.tr("Open a Python script"),
            triggered = self.load)
        save_action = create_action(self, self.tr("Save"), "Ctrl+S",
            'py_save.png', self.tr("Save current script"),
            triggered = self.save)
        save_as_action = create_action(self, self.tr("Save as..."), None,
            'py_save_as.png', self.tr("Save current script as..."),
            triggered = self.save_as)
        exec_action = create_action(self, self.tr("&Execute"), "F5",
            'execute.png', self.tr("Execute current script"),
            triggered=self.exec_script)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set editor font style"),
            triggered=self.change_font)
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get('editor', 'wrap') )
        menu_actions = (open_action, save_action, save_as_action, exec_action,
                        None, font_action, wrap_action)
        toolbar_actions = (open_action, save_action, exec_action,)
        return (menu_actions, toolbar_actions)                
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_if_changed()
        
    def load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        self.filename = self.file_path
        if not osp.isfile(self.filename):
            # Creating temporary file
            default = ['# -*- coding: utf-8 -*-',
                       '"""',
                       self.tr("PyQtShell Editor"),
                       '',
                       self.tr("This temporary script file is located here:"),
                       self.file_path,
                       '"""',
                       '',
                       '',
                       ]
            self.set_text("\r\n".join([unicode(qstr) for qstr in default]))
            self.save()
        self.load(self.filename)
    
    def exec_script(self):
        """Execute current script"""
        if self.save():
            self.mainwindow.shell.run_script(self.file_path, silent=True)

    def save_if_changed(self):
        """Ask user to save file if modified"""
        if self.filename == self.file_path or \
           self.isModified() and QMessageBox.question(self,
                self.get_name(raw=False),
                osp.basename(self.filename)+' '+ \
                self.tr(" has been modified.\nDo you want to save changes?"),
                QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
            self.save()
        
    def load(self, filename=None):
        """Load a Python script file"""
        if filename is None:
            self.save_if_changed()
            self.mainwindow.shell.restore_stds()
            basedir = os.getcwd()
            if self.filename != self.file_path:
                basedir = osp.dirname(self.filename)
            filename = QFileDialog.getOpenFileName(self,
                          self.tr("Open Python script"), basedir,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.mainwindow.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
                self.chdir( os.path.dirname(filename) )
                filename = os.path.basename(filename)
            else:
                return
        self.filename = filename
        text, self.encoding = encoding.read(self.filename)
        self.set_text( text )
        
        self.setModified(False)
        self.refresh_title()
        
    def refresh_title(self):
        """Refresh DockWidget title (+filename)"""
        if self.dockwidget is None:
            return
        title = self.get_name(raw=False)
        if self.filename != self.file_path:
            title += ' - ' + osp.basename(self.filename)
        else:
            title += ' (' + self.tr("temporary file") + ')'
        self.dockwidget.setWindowTitle(title)
        self.change()
        self.setFocus()

    def save_as(self):
        """Save the currently edited Python script file"""
        self.mainwindow.shell.restore_stds()
        filename = QFileDialog.getSaveFileName(self,
                      self.tr("Save Python script"), self.filename,
                      self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.mainwindow.shell.redirect_stds()
        if filename:
            self.filename = unicode(filename)
            self.chdir( os.path.dirname(self.filename) )
        else:
            return False
        self.save()
        self.refresh_title()
    
    def save(self):
        """Save the currently edited Python script file"""
        if self.filename is None:
            return self.save_as()
        self.encoding = encoding.write(unicode(self.get_text()),
                                       self.filename, self.encoding)
        self.setModified(False)
        self.change()
        return True
        
    def change_font(self):
        """Change editor font"""
        font, valid = QFontDialog.getFont(get_font('editor'),
                          self, self.tr("Select a new font"))
        if valid:
            self.set_font(font)
            set_font(font, 'editor')
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.set_wrap_mode(checked)


class HistoryLog(EditorBaseWidget, WidgetMixin):
    """
    History log widget
    """
    def __init__(self, parent):
        EditorBaseWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        self.setReadOnly(True)
        self.set_font( get_font('history') )
        self.set_wrap_mode( CONF.get('history', 'wrap') )
        self.setup_margin( get_font('history', 'margin'), 3 )
        self.history = self.mainwindow.shell.rawhistory
        self.refresh()
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&History log')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def refresh(self):
        """Refresh widget"""
        self.set_text("\n".join(self.history))
        self.setCursorPosition(self.lines() - 1, 0)
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        pass


class DocViewer(QWidget, WidgetMixin):
    """
    Docstrings viewer widget
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)

        # Read-only editor
        self.editor = EditorBaseWidget(self)
        self.editor.setReadOnly(True)
        self.editor.set_font( get_font('docviewer') )
        self.editor.set_wrap_mode( CONF.get('docviewer', 'wrap') )
        self.editor.setup_margin(None)
        
        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.addWidget(QLabel(self.tr("Object")))
        self.edit = QLineEdit()
        self.edit.setToolTip( \
            self.tr("Enter an object name to view the associated help"))
        self.connect(self.edit, SIGNAL("textChanged(QString)"), self.set_help)
        layout_edit.addWidget(self.edit)
        
        self.help_or_doc = QCheckBox(self.tr("Show source"))
        self.connect(self.help_or_doc, SIGNAL("stateChanged(int)"),
                     self.toggle_help)
        layout_edit.addWidget(self.help_or_doc)
        self.docstring = None
        self.autosource = False
        self.toggle_help(Qt.Unchecked)

        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(layout_edit)
        layout.addWidget(self.editor)
        self.setLayout(layout)
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&Doc')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def toggle_help(self, state):
        """Toggle between docstring and help()"""
        self.docstring = (state == Qt.Unchecked)
        self.refresh()
        
    def refresh(self, text=None):
        """Refresh widget"""
        if text is None:
            text = self.edit.text()
        else:
            self.edit.setText(text)
        self.set_help(text)
        
    def set_help(self, obj_text):
        """Show help"""
        obj_text = unicode(obj_text)
        hlp_text = None
        try:
            obj = eval(obj_text, globals(),
                       self.mainwindow.shell.interpreter.locals)
            if self.docstring:
                hlp_text = getdoc(obj)
                if hlp_text is None:
                    self.help_or_doc.setChecked(True)
                    return
            else:
                hlp_text = getsource(obj)
        except:
            pass
        if hlp_text is None:
            hlp_text = self.tr("No documentation available.")
        self.editor.set_text(hlp_text)
        self.editor.setCursorPosition(0, 0)
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        pass


class NoValue(object):
    """Dummy class used by wsfilter"""
    pass

def wsfilter(obj_in, rec=0):
    """Keep only objects that can be saved"""
    filters = tuple(str2type(CONF.get('workspace', 'filters')))
    exclude_private = CONF.get('workspace', 'exclude_private')
    exclude_upper = CONF.get('workspace', 'exclude_upper')
    if rec == 2:
        return NoValue
    obj_out = obj_in
    if isinstance(obj_in, dict):
        obj_out = {}
        for key in obj_in:
            value = obj_in[key]
            if rec == 0:
                # Excluded references for namespace to be saved without error
                if key in CONF.get('workspace', 'excluded'):
                    continue
                if exclude_private and key.startswith('_'):
                    continue
                if exclude_upper and key[0].isupper():
                    continue
                if isinstance(value, filters):
                    value = wsfilter(value, rec+1)
                    if value is not NoValue:
                        obj_out[key] = value
            elif not isinstance(value, filters) or not isinstance(key, filters):
                return NoValue
#    elif isinstance(obj_in, (list, tuple)):
#        obj_out = []
#        for value in obj_in:
#            if isinstance(value, filters):
#                value = wsfilter(value, rec+1)
#                if value is not NoValue:
#                    obj_out.append(value)
#        if isinstance(obj_in, tuple):
#            obj_out = tuple(obj_out)
    return obj_out            

from dicteditor import DictEditor

#TODO: Add action "Save workspace as..."
#TODO: Add action "Load workspace"
#TODO: Add splash screen during loading/saving
class Workspace(DictEditor, WidgetMixin):
    """
    Workspace widget (namespace explorer)
    """
    file_path = osp.join(osp.expanduser('~'), '.temp.ws')
    def __init__(self, parent):
        self.shell = None
        self.namespace = None
        self.filename = None
        DictEditor.__init__(self, parent, None)
        WidgetMixin.__init__(self, parent)
        self.load_temp_namespace()
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&Workspace')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def set_shell(self, shell):
        """Bind to shell widget"""
        self.shell = shell
        self.refresh()

    def refresh(self):
        """Refresh widget"""
        if self.shell is not None:
            self.namespace = self.shell.namespace
        self.set_data( self.namespace, wsfilter )
        
    def set_actions(self):
        """Setup actions"""
        open_action = create_action(self, self.tr("Open..."), None,
            'ws_open.png', self.tr("Open a workspace"), triggered = self.load)
        save_action = create_action(self, self.tr("Save"), None, 'ws_save.png',
            self.tr("Save current workspace"), triggered = self.save)
        save_as_action = create_action(self, self.tr("Save as..."), None,
            'ws_save_as.png',  self.tr("Save current workspace as..."),
            triggered = self.save_as)
        sort_action = create_action(self, self.tr("Sort columns"),
            toggled=self.setSortingEnabled)
        inplace_action = create_action(self, self.tr("Always edit in-place"),
            toggled=self.set_inplace_editor)
        
        exclude_private_action = create_action(self,
            self.tr("Exclude private references"),
            toggled=self.toggle_exclude_private)
        checked = CONF.get('workspace', 'exclude_private')
        exclude_private_action.setChecked(checked)
        
        autosave_action = create_action(self, self.tr("Auto save"),
            toggled=self.toggle_autosave,
            tip=self.tr("Automatically save workspace in a temporary file when quitting"))
        checked = CONF.get('workspace', 'autosave')
        save_action.setChecked(checked)
        menu_actions = (sort_action, inplace_action, None,
                        exclude_private_action, None, open_action, save_action,
                        save_as_action, autosave_action)
        toolbar_actions = (open_action, save_action, None)
        return (menu_actions, toolbar_actions)                
        
    def toggle_autosave(self, checked):
        """Toggle autosave mode"""
        CONF.set('workspace', 'autosave', checked)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        if CONF.get('workspace', 'autosave'):
            # Saving workspace
            self.save()
        else:
            workspace = wsfilter(self.namespace)
            refnb = len(workspace)
            if refnb > 1:
                srefnb = str(refnb)
                s_or_not = 's'
                it_or_them = self.tr('them')
            else:
                srefnb = self.tr('one')
                s_or_not = ''
                it_or_them = self.tr('it')
            if refnb and QMessageBox.question(self, self.get_name(raw=False),
               self.tr("Workspace is currently keeping reference to %1 object%2.\n\nDo you want to save %3?") \
               .arg(srefnb).arg(s_or_not).arg(it_or_them),
               QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
                # Saving workspace
                self.save()
            elif osp.isfile(self.file_path):
                # Removing last saved workspace
                os.remove(self.file_path)
    
    def load_temp_namespace(self):
        """Attempt to load last session namespace"""
        self.filename = self.file_path
        if osp.isfile(self.filename):
            self.load(self.filename)
        else:
            self.namespace = None
            
    def load(self, filename=None):
        """Attempt to load namespace"""
        if filename is None:
            self.mainwindow.shell.restore_stds()
            basedir = osp.dirname(self.filename)
            filename = QFileDialog.getOpenFileName(self,
                          self.tr("Open workspace"), basedir,
                          self.tr("Workspaces")+" (*.ws)")
            self.mainwindow.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
            else:
                return
        self.filename = filename
        try:
            namespace = cPickle.load(file(self.filename))
            if self.namespace is None:
                self.namespace = namespace
            else:
                for key in namespace:
                    self.shell.namespace[key] = namespace[key]
        except (EOFError, ValueError):
            os.remove(self.filename)
            return
        self.refresh()        

    def save_as(self):
        """Save current workspace as"""
        self.mainwindow.shell.restore_stds()
        filename = QFileDialog.getSaveFileName(self,
                      self.tr("Save workspace"), self.filename,
                      self.tr("Workspaces")+" (*.ws)")
        self.mainwindow.shell.redirect_stds()
        if filename:
            self.filename = unicode(filename)
        else:
            return False
        self.save()
    
    def save(self):
        """Save current workspace"""
        if self.filename is None:
            return self.save_as()
        try:
            cPickle.dump(wsfilter(self.namespace), file(self.filename, 'w'))
        except RuntimeError, error:
            raise RuntimeError(self.tr("Unable to save current workspace:") + \
                               '\n\r' + error)
        else:
            return True
        
    def toggle_exclude_private(self, checked):
        """Toggle exclude private references"""
        CONF.set('workspace', 'exclude_private', checked)
        self.refresh()


def tests():
    """
    Testing Working Directory Widget
    """
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    # Working directory changer test:
    dialog = WorkingDirectory(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    tests()
        