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

"""Editor widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFileDialog,
                         QTabWidget, QMenu, QCheckBox, QMessageBox, QComboBox,
                         QFontDialog, QSizePolicy, QToolBar, QAction)
from PyQt4.QtCore import Qt, SIGNAL

import os, sys, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell import encoding
from PyQtShell.config import CONF, get_conf_path, get_icon, get_font, set_font
from PyQtShell.qthelpers import (get_std_icon, create_action, add_actions,
                                 mimedata2url, keybinding, translate)
from PyQtShell.dochelpers import getdoc, getsource
try:
    from PyQtShell.widgets.qscibase import QsciEditor as EditorBaseWidget
except ImportError:
    from PyQtShell.widgets.qtbase import QtEditor as EditorBaseWidget

# Package local imports
from PyQtShell.widgets.base import WidgetMixin, EditableComboBox, FindReplace


class SimpleEditor(EditorBaseWidget):
    """
    Simple Editor Widget
    QsciEditor/QtEditor -> *SimpleEditor* -> SimpleScriptEditor, DocViewer, ...
    """
    def __init__(self, parent, margin=True):
        super(SimpleEditor, self).__init__(parent, margin=margin)
        # Context menu
        self.undo_action = create_action(self,
                           translate("SimpleEditor", "Undo"),
                           shortcut=keybinding('Undo'),
                           icon=get_icon('undo.png'), triggered=self.undo)
        self.redo_action = create_action(self,
                           translate("SimpleEditor", "Redo"),
                           shortcut=keybinding('Redo'),
                           icon=get_icon('redo.png'), triggered=self.redo)
        self.cut_action = create_action(self,
                           translate("SimpleEditor", "Cut"),
                           shortcut=keybinding('Cut'),
                           icon=get_icon('cut.png'), triggered=self.cut)
        self.copy_action = create_action(self,
                           translate("SimpleEditor", "Copy"),
                           shortcut=keybinding('Copy'),
                           icon=get_icon('copy.png'), triggered=self.copy)
        paste_action = create_action(self,
                           translate("SimpleEditor", "Paste"),
                           shortcut=keybinding('Paste'),
                           icon=get_icon('paste.png'), triggered=self.paste)
        self.delete_action = create_action(self,
                           translate("SimpleEditor", "Delete"),
                           shortcut=keybinding('Delete'),
                           icon=get_icon('close.png'),
                           triggered=self.removeSelectedText)
        selectall_action = create_action(self,
                           translate("SimpleEditor", "Select all"),
                           shortcut=keybinding('SelectAll'),
                           icon=get_icon('selectall.png'),
                           triggered=self.selectAll)
        self.menu = QMenu(self)
        add_actions(self.menu, (self.undo_action, self.redo_action, None,
                                self.cut_action, self.copy_action,
                                paste_action, self.delete_action,
                                None, selectall_action))        
        # Read-only context-menu
        self.readonly_menu = QMenu(self)
        add_actions(self.readonly_menu, (self.copy_action, None, selectall_action))        
        
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        state = self.hasSelectedText()
        self.copy_action.setEnabled(state)
        self.cut_action.setEnabled(state)
        self.delete_action.setEnabled(state)
        self.undo_action.setEnabled( self.isUndoAvailable() )
        self.redo_action.setEnabled( self.isRedoAvailable() )
        menu = self.menu
        if self.isReadOnly():
            menu = self.readonly_menu
        menu.popup(event.globalPos())
        event.accept()

    
class SimpleScriptEditor(SimpleEditor):
    """
    Simple Script Editor Widget
    QsciEditor/QtEditor -> SimpleEditor
                            -> *SimpleScriptEditor* -> Editor's tabwidget
    """
    def __init__(self, parent, text):
        super(SimpleScriptEditor, self).__init__(parent)
        self.setup_editor(text)
        
    def setup_editor(self, text):
        """Setup Editor"""
        self.set_font( get_font('editor') )
        self.set_wrap_mode( CONF.get('editor', 'wrap') )
        self.setup_api()
        self.set_text(text)
        self.setModified(False)
        self.connect( self, SIGNAL('modificationChanged(bool)'),
                      self.parent().change )
        
    def highlight_line(self, linenb):
        """Highlight line number linenb"""
        line = unicode(self.get_text()).splitlines()[linenb-1]
        self.find_text(line)

    def check_syntax(self, filename):
        """Check module syntax"""
        f = open(filename, 'r')
        source = f.read()
        f.close()
        if '\r' in source:
            source = re.sub(r"\r\n", "\n", source)
            source = re.sub(r"\r", "\n", source)
        if source and source[-1] != '\n':
            source = source + '\n'
        try:
            # If successful, return the compiled code
            if compile(source, filename, "exec"):
                return None
        except (SyntaxError, OverflowError), err:
            try:
                msg, (_errorfilename, lineno, _offset, _line) = err
                self.highlight_line(lineno)
            except:
                msg = "*** " + str(err)
            return self.tr("There's an error in your program:") + "\n" + msg

class Tabs(QTabWidget):
    """TabWidget with a context-menu"""
    def __init__(self, parent, actions):
        QTabWidget.__init__(self, parent)
        self.menu = QMenu(self)
        add_actions(self.menu, actions)
        
    def contextMenuEvent(self, event):
        """Override Qt method"""
        if self.menu:
            self.menu.popup(event.globalPos())

class Editor(QWidget, WidgetMixin):
    """
    Multi-file Editor widget
    """
    ID = 'editor'
    file_path = get_conf_path('.temp.py')
    def __init__(self, parent):
        self.file_dependent_actions = []
        self.dock_toolbar_actions = None
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.dock_toolbar = QToolBar(self)
        add_actions(self.dock_toolbar, self.dock_toolbar_actions)
        layout.addWidget(self.dock_toolbar)
        
        self.tabwidget = Tabs(self, self.tab_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh)
        layout.addWidget(self.tabwidget)
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        # Recent files
        self.recent_files = CONF.get('editor', 'recent_files', [])
        # Changing working directory to the most recent file directory
        for filename in self.recent_files:
            dir = os.path.dirname(filename)
            if os.path.isdir(dir):
                os.chdir(dir)
                break

        self.filenames = []
        self.encodings = []
        self.editors = []
        
        filenames = CONF.get(self.ID, 'filenames', [])
        if filenames:
            self.load(filenames)
        else:
            self.load_temp_file()
            
        # Accepting drops
        self.setAcceptDrops(True)

    def add_recent_file(self, fname):
        """Add to recent file list"""
        if fname is None:
            return
        if not fname in self.recent_files:
            self.recent_files.insert(0, fname)
            if len(self.recent_files) > 9:
                self.recent_files.pop(-1)
        
    def refresh(self, index=None):
        """Refresh tabwidget"""
        if index is None:
            index = self.tabwidget.currentIndex()
        # Enable/disable file dependent actions (only if dockwidget is visible)
        if self.dockwidget and self.dockwidget.isVisible():
            enable = index != -1
            for action in self.file_dependent_actions:
                action.setEnabled(enable)
        # Set current editor
        title = self.get_name()
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            editor = self.editors[index]
            title += " - "+osp.basename(self.filenames[index])
        else:
            editor = None
        if self.dockwidget:
            self.dockwidget.setWindowTitle(title)
            
        self.find_widget.set_editor(editor)
        self.change()

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        WidgetMixin.visibility_changed(self, enable)
        if self.dockwidget.isWindow():
            self.dock_toolbar.show()
        else:
            self.dock_toolbar.hide()
        self.refresh()

    def change(self, state=None):
        """Change tab title depending on modified state"""
        index = self.tabwidget.currentIndex()
        if index == -1:
            return
        if state is None:
            state = self.editors[index].isModified()
        title = self.get_title(self.filenames[index])
        if state:
            title += "*"
        elif title.endswith('*'):
            title = title[:-1]
        self.tabwidget.setTabText(index, title)
        self.save_action.setEnabled(state)
        
    def get_name(self):
        """Return widget name"""
        return self.tr('Editor')
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.LeftDockWidgetArea)

    def set_actions(self):
        """Setup actions"""
        self.new_action = create_action(self, self.tr("New..."), "Ctrl+N",
            'new.png', self.tr("Create a new Python script"),
            triggered = self.new)
        self.open_action = create_action(self, self.tr("Open..."), "Ctrl+O",
            'open.png', self.tr("Open a Python script"),
            triggered = self.load)
        self.save_action = create_action(self, self.tr("Save"), "Ctrl+S",
            'save.png', self.tr("Save current script"),
            triggered = self.save)
        self.save_as_action = create_action(self, self.tr("Save as..."), None,
            'saveas.png', self.tr("Save current script as..."),
            triggered = self.save_as)
        self.close_action = create_action(self, self.tr("Close"), "Ctrl+W",
            'close.png', self.tr("Close current script"),
            triggered = self.close)
        self.close_all_action = create_action(self, self.tr("Close all"),
            "Ctrl+Maj+W", 'close_all.png', self.tr("Close all opened scripts"),
            triggered = self.close_all)
        self.check_action = create_action(self, self.tr("&Check syntax"), "F5",
            'check.png', self.tr("Check current script for syntax errors"),
            triggered=self.check_script)
        self.exec_action = create_action(self, self.tr("&Execute"), "F9",
            'execute.png', self.tr("Execute current script"),
            triggered=self.exec_script)
        self.exec_interact_action = create_action(self,
            self.tr("Execute and &interact"), "Shift+F9",
            'execute_interact.png',
            self.tr("Execute current script and set focus to shell"),
            triggered=self.exec_script_and_interact)
        self.exec_selected_action = create_action(self,
            self.tr("Execute selection"), "Ctrl+F9", 'execute_selection.png',
            self.tr("Execute selected text in current script and set focus to shell"),
            triggered=self.exec_selected_text)
        self.comment_action = create_action(self, self.tr("Comment"), "Ctrl+K",
            'comment.png', self.tr("Comment current line or selection"),
            triggered = self.comment)
        self.uncomment_action = create_action(self, self.tr("Uncomment"), "Shift+Ctrl+K",
            'uncomment.png', self.tr("Uncomment current line or selection"),
            triggered = self.uncomment)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set editor font style"),
            triggered=self.change_font)
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        workdir_action = create_action(self, self.tr("Set working directory"),
            tip=self.tr("Change working directory to current script directory"),
            triggered=self.set_workdir)
        menu_actions = (self.comment_action, self.uncomment_action, None,
                self.check_action, self.exec_action, self.exec_interact_action,
                self.exec_selected_action, None, font_action, wrap_action)
        toolbar_actions = [self.new_action, self.open_action, self.save_action,
                None, self.mainwindow.find_action, self.mainwindow.replace_action, None,
                self.check_action, self.exec_action, self.exec_selected_action]
        self.dock_toolbar_actions = toolbar_actions + \
                [self.exec_interact_action, self.comment_action,
                 self.uncomment_action, None, self.close_action]
        self.file_dependent_actions = (self.save_action, self.save_as_action,
                self.check_action, self.exec_action, self.exec_interact_action,
                self.exec_selected_action, workdir_action, self.close_action,
                self.close_all_action,
                self.comment_action, self.uncomment_action)
        self.tab_actions = (self.save_action, self.save_as_action,
                self.check_action, self.exec_action, workdir_action,
                None, self.close_action)
        return (menu_actions, toolbar_actions)        
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        CONF.set(self.ID, 'filenames', self.filenames)
        CONF.set(self.ID, 'recent_files', self.recent_files)
        return self.save_if_changed(cancelable)
    
    def comment(self):
        """Comment current line or selection"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            self.editors[index].comment()

    def uncomment(self):
        """Uncomment current line or selection"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            self.editors[index].uncomment()
        
    def set_workdir(self):
        """Set working directory as current script directory"""
        index = self.tabwidget.currentIndex()
        if index:
            filename = self.filenames[index]
            self.chdir( os.path.dirname(os.path.abspath(filename)) )
            self.emit(SIGNAL("refresh()"))
        
    def load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if not osp.isfile(self.file_path):
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
            text = "\r\n".join([unicode(qstr) for qstr in default])
            encoding.write(unicode(text), self.file_path, 'utf-8')
        self.load(self.file_path)
    
    def new(self):
        """Create a new Python script"""
        gen_name = lambda nb: self.tr("untitled") + ("%d.py" % nb)
        nb = 0
        while osp.isfile(gen_name(nb)):
            nb += 1
        fname = gen_name(nb)
        self.mainwindow.shell.restore_stds()
        fname = QFileDialog.getSaveFileName(self, self.tr("New Python script"),
                    fname, self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.mainwindow.shell.redirect_stds()
        if not fname.isEmpty():
            fname = unicode(fname)
            default = ['# -*- coding: utf-8 -*-',
                       '"""',
                       osp.basename(fname),
                       '"""',
                       '',
                       '',
                       ]
            text = "\r\n".join([unicode(qstr) for qstr in default])
            encoding.write(unicode(text), fname, 'utf-8')
            self.load(fname)
    
    def check_script(self):
        """Check current script for syntax errors"""
        if self.save():
            index = self.tabwidget.currentIndex()
            errors = self.editors[index].check_syntax(self.filenames[index])
            title = self.tr("Check syntax")
            if errors:
                QMessageBox.critical(self, title, errors)
            else:
                QMessageBox.information(self, title,
                                        self.tr("There is no error in your program.")) 
    
    def exec_script(self, set_focus=False):
        """Execute current script"""
        if self.save():
            self.mainwindow.shell.run_script(self.get_current_filename(),
                                             silent=True, set_focus=set_focus)
    
    def exec_script_and_interact(self):
        """Execute current script and set focus to shell"""
        self.exec_script(set_focus=True)
        
    def exec_selected_text(self):
        """Execute selected text in current script and set focus to shell"""
        index = self.tabwidget.currentIndex()
        lines = unicode( self.editors[index].selectedText() )
        self.mainwindow.shell.execute_lines(lines)
        self.mainwindow.shell.setFocus()

    def save_if_changed(self, cancelable=False):
        """Ask user to save file if modified"""
        buttons = QMessageBox.Yes | QMessageBox.No
        if cancelable:
            buttons = buttons | QMessageBox.Cancel
        for index in range(0, self.tabwidget.count()):
            self.tabwidget.setCurrentIndex(index)
            filename = self.filenames[index]
            if filename == self.file_path:
                self.save()
            if self.editors[index].isModified():
                answer = QMessageBox.question(self, self.get_name(),
                    osp.basename(filename)+' '+ \
                    self.tr(" has been modified.\nDo you want to save changes?"),
                    buttons)
                if answer == QMessageBox.Yes:
                    self.save()
                elif answer == QMessageBox.Cancel:
                    return False
        return True
    
    def close(self):
        """Close current Python script file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            is_ok = self.save_if_changed(cancelable=True)
            if is_ok:
                self.tabwidget.removeTab(index)
                self.filenames.pop(index)
                self.encodings.pop(index)
                self.editors.pop(index)
            return is_ok
        else:
            self.find_widget.set_editor(None)
            
    def close_all(self):
        """Close all opened scripts"""
        while self.close():
            pass
        
    def get_title(self, filename):
        """Return tab title"""
        if filename != self.file_path:
            return osp.basename(filename)
        else:
            return unicode(self.tr("Temporary file"))
        
    def load(self, filenames=None, goto=None):
        """Load a Python script file"""
        if not filenames:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filenames = unicode(action.data().toString())
        if not filenames:
            self.mainwindow.shell.restore_stds()
            basedir = os.getcwd()
            if self.filenames:
                index = self.tabwidget.currentIndex()
                if self.filenames[index] != self.file_path:
                    basedir = osp.dirname(self.filenames[index])
            filenames = QFileDialog.getOpenFileNames(self,
                          self.tr("Open Python script"), basedir,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.mainwindow.shell.redirect_stds()
            filenames = list(filenames)
            if len(filenames):
#                self.chdir( os.path.dirname(unicode(filenames[-1])) )
                filenames = [osp.normpath(unicode(fname)) for fname in filenames]
            else:
                return
            
        if self.dockwidget:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            
        if not isinstance(filenames, list):
            filenames = [filenames]
            
        for filename in filenames:
            # -- Do not open an already opened file
            if filename in self.filenames:
                index = self.filenames.index(filename)
                self.tabwidget.setCurrentIndex(index)
                editor = self.editors[index]
                editor.setFocus()
            # --
            elif osp.isfile(filename):
                self.filenames.append(filename)
                txt, enc = encoding.read(filename)
                self.encodings.append(enc)
                
                # Editor widget creation
                editor = SimpleScriptEditor(self, txt)
                self.editors.append(editor)
                
                title = self.get_title(filename)
                index = self.tabwidget.addTab(editor, title)
                self.tabwidget.setTabToolTip(index, filename)
                self.tabwidget.setTabIcon(index, get_icon('python.png'))
                
                self.find_widget.set_editor(editor)
               
                self.change()
                self.tabwidget.setCurrentIndex(index)
                editor.setFocus()
                self.add_recent_file(filename)
            
            if goto is not None:
                editor.highlight_line(goto)

    def save_as(self):
        """Save the currently edited Python script file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            self.mainwindow.shell.restore_stds()
            filename = QFileDialog.getSaveFileName(self,
                          self.tr("Save Python script"), self.filenames[index],
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.mainwindow.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
                self.filenames[index] = filename
#                self.chdir( os.path.dirname(filename) )
            else:
                return False
            self.save()
    
    def save(self):
        """Save the currently edited Python script file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            txt = unicode(self.editors[index].get_text())
            self.encodings[index] = encoding.write(txt,
                                                   self.filenames[index],
                                                   self.encodings[index])
            self.editors[index].setModified(False)
            self.change()
            return True
        
    def change_font(self):
        """Change editor font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                          self, self.tr("Select a new font"))
        if valid:
            for index in range(0, self.tabwidget.count()):
                self.editors[index].set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if hasattr(self, 'tabwidget'):
            for index in range(0, self.tabwidget.count()):
                self.editors[index].set_wrap_mode(checked)
    
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        if source.hasUrls() or source.hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        if source.hasUrls():
            files = mimedata2url(source)
            if files:
                self.load(files)
        elif source.hasText():
            if self.tabwidget.count():
                editor = self.editors[self.tabwidget.currentIndex()]
                editor.insert_text( source.text() )
        event.acceptProposedAction()


class HistoryLog(QWidget, WidgetMixin):
    """
    History log widget
    """
    ID = 'history'
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)

        # Read-only editor
        self.editor = SimpleEditor(self, margin=False)
        self.editor.setReadOnly(True)
        self.editor.set_font( get_font(self.ID) )
        self.editor.set_wrap_mode( CONF.get(self.ID, 'wrap') )
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        self.history = self.mainwindow.shell.shell.interpreter.rawhistory
        self.refresh()
        
    def get_name(self):
        """Return widget name"""
        return self.tr('History log')
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.RightDockWidgetArea)
        
    def refresh(self):
        """Refresh widget"""
        self.editor.set_text("\n".join(self.history))
        self.editor.set_cursor_to("End")
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True


class DocComboBox(EditableComboBox):
    """
    QComboBox handling doc viewer history
    """
    def __init__(self, parent):
        super(DocComboBox, self).__init__(parent)
        self.tips = {True: self.tr("Press enter to validate this object name"),
                     False: self.tr('This object name is incorrect')}
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        try:
            eval(unicode(qstr),
                 self.parent().mainwindow.shell.interpreter.locals)
            return True
        except:
            return False

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            text = self.currentText()
            if self.is_valid(text):
                self.parent().refresh(text)
                self.set_default_style()
        else:
            QComboBox.keyPressEvent(self, event)
    
class DocViewer(QWidget, WidgetMixin):
    """
    Docstrings viewer widget
    """
    ID = 'docviewer'
    log_path = get_conf_path('.docviewer')
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)

        # Read-only editor
        self.editor = SimpleEditor(self, margin=False)
        self.editor.setReadOnly(True)
        self.editor.set_font( get_font(self.ID) )
        self.editor.set_wrap_mode( CONF.get(self.ID, 'wrap') )
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()
        
        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.addWidget(QLabel(self.tr("Object")))
        self.combo = DocComboBox(self)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout_edit.addWidget(self.combo)
        self.combo.setMaxCount(CONF.get(self.ID, 'max_history_entries'))
        dvhistory = self.load_dvhistory()
        self.combo.addItems( dvhistory )
        
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
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
    def get_name(self):
        """Return widget name"""
        return self.tr('Doc')
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.LeftDockWidgetArea)
        
    def load_dvhistory(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.log_path):
            dvhistory = [line.replace('\n','')
                         for line in file(self.log_path, 'r').readlines()]
        else:
            dvhistory = [ ]
        return dvhistory
    
    def save_dvhistory(self):
        """Save history to a text file in user home directory"""
        file(self.log_path, 'w').write("\n".join( \
            [ unicode( self.combo.itemText(index) )
                for index in range(self.combo.count()) ] ))
        
    def toggle_help(self, state):
        """Toggle between docstring and help()"""
        self.docstring = (state == Qt.Unchecked)
        self.refresh()
        
    def refresh(self, text=None):
        """Refresh widget"""
        if text is None:
            text = self.combo.currentText()
        else:
            index = self.combo.findText(text)
            while index!=-1:
                self.combo.removeItem(index)
                index = self.combo.findText(text)
            self.combo.insertItem(0, text)
            self.combo.setCurrentIndex(0)
        self.set_help(text)
        self.save_dvhistory()
        
    def set_help(self, obj_text):
        """Show help"""
        obj_text = unicode(obj_text)
        hlp_text = None
        try:
            obj = eval(obj_text, self.mainwindow.shell.interpreter.locals)
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
        self.editor.set_cursor_to("Start")
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

