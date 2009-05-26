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

from PyQt4.QtGui import (QHBoxLayout, QVBoxLayout, QLabel, QFileDialog,
                         QSizePolicy, QMessageBox, QFontDialog,
                         QCheckBox, QToolBar, QAction, QComboBox)
from PyQt4.QtCore import Qt, SIGNAL, QStringList

import os, sys, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell import encoding
from PyQtShell.config import CONF, get_conf_path, get_icon, get_font, set_font
from PyQtShell.qthelpers import (create_action, add_actions, mimedata2url,
                                 get_filetype_icon, create_toolbutton)
from PyQtShell.dochelpers import getdoc, getsource
try:
    from PyQtShell.widgets.qscieditor import QsciEditor
except ImportError, e:
    raise ImportError, str(e) + \
        "\nPyQtShell v0.3.23+ is exclusively based on QScintilla2\n" + \
        "(http://www.riverbankcomputing.co.uk/software/qscintilla)"
from PyQtShell.widgets import Tabs
from PyQtShell.widgets.comboboxes import EditableComboBox
from PyQtShell.widgets.findreplace import FindReplace
from PyQtShell.plugins import PluginWidget


class CodeEditor(QsciEditor):
    """
    Simple Script Editor Widget:
    QsciEditor -> *CodeEditor* -> Editor
    """
    def __init__(self, parent, text, language=None):
        super(CodeEditor, self).__init__(parent, language=language)
        self.setup_editor(text)
        
    def setup_editor(self, text):
        """Setup Editor"""
        self.set_font( get_font('editor') )
        self.set_wrap_mode( CONF.get('editor', 'wrap') )
        self.setup_api()
        self.set_text(text)
        self.setModified(False)
        
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


#TODO: Google-Code feature request: add a class/function browser
class Editor(PluginWidget):
    """
    Multi-file Editor widget
    """
    ID = 'editor'
    file_path = get_conf_path('.temp.py')
    def __init__(self, parent):
        self.file_dependent_actions = []
        self.dock_toolbar_actions = None
        PluginWidget.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.dock_toolbar = QToolBar(self)
        add_actions(self.dock_toolbar, self.dock_toolbar_actions)
        layout.addWidget(self.dock_toolbar)
        
        # Tab widget with close button
        self.tabwidget = Tabs(self, self.tab_actions)
        self.connect(self.tabwidget, SIGNAL("close_tab(int)"), self.close)
        self.close_button = create_toolbutton(self.tabwidget,
                                          icon=get_icon("fileclose.png"),
                                          callback=self.close,
                                          tip=self.tr("Close current script"))
        self.tabwidget.setCornerWidget(self.close_button)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh)
        layout.addWidget(self.tabwidget)
        
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        self.recent_files = CONF.get('editor', 'recent_files', [])
        self.filenames = []
        self.encodings = []
        self.editors = []
        self.processlist = []
        
        filenames = CONF.get(self.ID, 'filenames', [])
        if filenames:
            self.load(filenames)
        else:
            self.load_temp_file()
            
        # Accepting drops
        self.setAcceptDrops(True)
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Editor')

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
        title = self.get_widget_title()
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
        PluginWidget.visibility_changed(self, enable)
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

    def set_actions(self):
        """Setup actions"""
        self.new_action = create_action(self, self.tr("New..."), "Ctrl+N",
            'filenew.png', self.tr("Create a new Python script"),
            triggered = self.new)
        self.open_action = create_action(self, self.tr("Open..."), "Ctrl+O",
            'fileopen.png', self.tr("Open a Python script"),
            triggered = self.load)
        self.save_action = create_action(self, self.tr("Save"), "Ctrl+S",
            'filesave.png', self.tr("Save current script"),
            triggered = self.save)
        self.save_as_action = create_action(self, self.tr("Save as..."), None,
            'filesaveas.png', self.tr("Save current script as..."),
            triggered = self.save_as)
        self.close_action = create_action(self, self.tr("Close"), "Ctrl+W",
            'fileclose.png', self.tr("Close current script"),
            triggered = self.close)
        self.close_all_action = create_action(self, self.tr("Close all"),
            "Ctrl+Maj+W", 'filecloseall.png',
            self.tr("Close all opened scripts"),
            triggered = self.close_all)
        self.check_action = create_action(self, self.tr("&Check syntax"), "F8",
            'check.png', self.tr("Check current script for syntax errors"),
            triggered=self.check_script)
        self.exec_action = create_action(self,
            self.tr("&Run in interactive console"), "F9", 'execute.png',
            self.tr("Run current script in interactive console"),
            triggered=self.exec_script)
        self.exec_interact_action = create_action(self,
            self.tr("Run and &interact"), "Shift+F9", 'execute_interact.png',
            self.tr("Run current script in interactive console "
                    "and set focus to shell"),
            triggered=self.exec_script_and_interact)
        #TODO: implement Paste special to paste & removing leading >>>
        self.exec_selected_action = create_action(self,
            self.tr("Run &selection"), "Ctrl+F9", 'execute_selection.png',
            self.tr("Run selected text in interactive console"
                    " and set focus to shell"),
            triggered=self.exec_selected_text)
        self.exec_process_action = create_action(self,
            self.tr("Run in e&xternal console"), "F5", 'execute_safe.png',
            self.tr("Run current script in external console"
                    "\n(external console is executed in a separate process)"),
            triggered=lambda: self.exec_script_safeconsole())
        self.exec_process_interact_action = create_action(self,
            self.tr("Run and interact"), "Shift+F5",
            tip=self.tr("Run current script in external console and interact "
                        "\nwith Python interpreter when program has finished"
                        "\n(external console is executed in a separate process)"),
            triggered=lambda: self.exec_script_safeconsole(interact=True))
        self.exec_process_args_action = create_action(self,
            self.tr("Run with arguments"), "Ctrl+F5",
            tip=self.tr("Run current script in external console specifying "
                        "command line arguments"
                        "\n(external console is executed in a separate process)"),
            triggered=lambda: self.exec_script_safeconsole(ask_for_arguments=True))
        self.exec_process_debug_action = create_action(self,
            self.tr("Debug"), "Ctrl+Shift+F5",
            tip=self.tr("Debug current script in external console"
                        "\n(external console is executed in a separate process)"),
            triggered=lambda: self.exec_script_safeconsole(ask_for_arguments=True, debug=True))
        self.comment_action = create_action(self, self.tr("Comment"), "Ctrl+K",
            'comment.png', self.tr("Comment current line or selection"),
            triggered = self.comment)
        self.uncomment_action = create_action(self, self.tr("Uncomment"),
            "Shift+Ctrl+K",
            'uncomment.png', self.tr("Uncomment current line or selection"),
            triggered = self.uncomment)
        self.indent_action = create_action(self, self.tr("Indent"), "Ctrl+Tab",
            'indent.png', self.tr("Indent current line or selection"),
            triggered = self.indent)
        self.unindent_action = create_action(self, self.tr("Unindent"),
            "Shift+Ctrl+Tab",
            'unindent.png', self.tr("Unindent current line or selection"),
            triggered = self.unindent)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set editor font style"),
            triggered=self.change_font)
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        workdir_action = create_action(self, self.tr("Set working directory"),
            tip=self.tr("Change working directory to current script directory"),
            triggered=self.set_workdir)
        menu_actions = (self.comment_action, self.uncomment_action,
                self.indent_action, self.unindent_action, self.check_action,
                None, self.exec_action, self.exec_interact_action,
                self.exec_selected_action, None, self.exec_process_action,
                self.exec_process_interact_action,self.exec_process_args_action,
                self.exec_process_debug_action, None, font_action, wrap_action)
        toolbar_actions = [self.new_action, self.open_action, self.save_action,
                None, self.main.find_action, self.main.replace_action, None,
                self.check_action, self.exec_action, self.exec_selected_action,
                self.exec_process_action]
        self.dock_toolbar_actions = toolbar_actions + \
                [self.exec_interact_action, self.comment_action,
                 self.uncomment_action, self.indent_action,
                 self.unindent_action]
        self.file_dependent_actions = (self.save_action, self.save_as_action,
                self.check_action, self.exec_action, self.exec_interact_action,
                self.exec_selected_action, self.exec_process_action,
                self.exec_process_interact_action,self.exec_process_args_action,
                self.exec_process_debug_action,
                workdir_action, self.close_action, self.close_all_action,
                self.comment_action, self.uncomment_action,
                self.indent_action, self.unindent_action)
        self.tab_actions = (self.save_action, self.save_as_action,
                self.check_action, self.exec_action, self.exec_process_action,
                workdir_action, None, self.close_action)
        return (menu_actions, toolbar_actions)        
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        CONF.set(self.ID, 'filenames', self.filenames)
        CONF.set(self.ID, 'recent_files', self.recent_files)
        return self.save_if_changed(cancelable)
    
    def indent(self):
        """Indent current line or selection"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            self.editors[index].indent()

    def unindent(self):
        """Unindent current line or selection"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            self.editors[index].unindent()
    
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
            directory = os.path.dirname(os.path.abspath(filename))
            self.emit(SIGNAL("open_dir(QString)"), directory)
        
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
        self.main.console.shell.restore_stds()
        fname = QFileDialog.getSaveFileName(self, self.tr("New Python script"),
                    fname, self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.main.console.shell.redirect_stds()
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
    
    def exec_script_safeconsole(self, ask_for_arguments=False,
                                       interact=False, debug=False):
        """Run current script in another process"""
        if self.save():
            index = self.tabwidget.currentIndex()
            fname = os.path.abspath(self.filenames[index])
            self.emit(SIGNAL('open_safe_console(QString,bool,bool,bool)'),
                      fname, ask_for_arguments, interact, debug)
    
    def exec_script(self, set_focus=False):
        """Run current script"""
        if self.save():
            index = self.tabwidget.currentIndex()
            self.main.console.run_script(self.filenames[index],
                                         silent=True, set_focus=set_focus)
    
    def exec_script_and_interact(self):
        """Run current script and set focus to shell"""
        self.exec_script(set_focus=True)
        
    def exec_selected_text(self):
        """Run selected text in current script and set focus to shell"""
        index = self.tabwidget.currentIndex()
        lines = unicode( self.editors[index].selectedText() )
        # If there is a common indent to all lines, remove it
        min_indent = 999
        for line in lines.split(os.linesep):
            min_indent = min(len(line)-len(line.lstrip()), min_indent)
        if min_indent:
            lines = [line[min_indent:] for line in lines.split(os.linesep)]
            lines = os.linesep.join(lines)
        # If there is only one line of code, add an EOL char
        if (r"\n" not in lines) or (r"\r" not in lines):
            lines += os.linesep
        self.main.console.shell.execute_lines(lines)
        self.main.console.shell.setFocus()

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
                answer = QMessageBox.question(self, self.get_widget_title(),
                    osp.basename(filename)+' '+ \
                    self.tr(" has been modified.\nDo you want to save changes?"),
                    buttons)
                if answer == QMessageBox.Yes:
                    self.save()
                elif answer == QMessageBox.Cancel:
                    return False
        return True
    
    def close(self, index=None):
        """Close current Python script file"""
        if index is None:
            if self.tabwidget.count():
                index = self.tabwidget.currentIndex()
            else:
                self.find_widget.set_editor(None)
                return        
        is_ok = self.save_if_changed(cancelable=True)
        if is_ok:
            self.tabwidget.removeTab(index)
            self.filenames.pop(index)
            self.encodings.pop(index)
            self.editors.pop(index)
            self.refresh()
        return is_ok
            
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
            self.main.console.shell.restore_stds()
            basedir = os.getcwdu()
            if self.filenames:
                index = self.tabwidget.currentIndex()
                if self.filenames[index] != self.file_path:
                    basedir = osp.dirname(self.filenames[index])
            filenames = QFileDialog.getOpenFileNames(self,
                          self.tr("Open Python script"), basedir,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.main.console.shell.redirect_stds()
            filenames = list(filenames)
            if len(filenames):
#                directory = os.path.dirname(unicode(filenames[-1]))
#                self.emit(SIGNAL("open_dir(QString)"), directory)
                filenames = [osp.normpath(unicode(fname)) for fname in filenames]
            else:
                return
            
        if self.dockwidget:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
        
        if not isinstance(filenames, (list, QStringList)):
            filenames = [unicode(filenames)]
        else:
            filenames = [unicode(fname) for fname in list(filenames)]
            
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
                ext = osp.splitext(filename)[1]
                if ext.startswith('.'):
                    ext = ext[1:] # file extension with leading dot
                
                editor = CodeEditor(self, txt, language=ext)
                self.connect(editor, SIGNAL('modificationChanged(bool)'),
                             self.change)
                self.editors.append(editor)
                
                title = self.get_title(filename)
                index = self.tabwidget.addTab(editor, title)
                self.tabwidget.setTabToolTip(index, filename)
                self.tabwidget.setTabIcon(index, get_filetype_icon(filename))
                
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
            self.main.console.shell.restore_stds()
            filename = QFileDialog.getSaveFileName(self,
                          self.tr("Save Python script"), self.filenames[index],
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.main.console.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
                self.filenames[index] = filename
#                directory = os.path.dirname(filename)
#                self.emit(SIGNAL("open_dir(QString)"), directory)
            else:
                return False
            self.save()
    
    def save(self):
        """Save the currently edited Python script file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            if not self.editors[index].isModified():
                return True
            txt = unicode(self.editors[index].get_text())
            try:
                self.encodings[index] = encoding.write(txt,
                                                       self.filenames[index],
                                                       self.encodings[index])
                self.editors[index].setModified(False)
                self.change()
                return True
            except IOError, error:
                QMessageBox.critical(self, self.tr("Save"),
                self.tr("<b>Unable to save script '%1'</b>"
                        "<br><br>Error message:<br>%2") \
                .arg(osp.basename(self.filenames[index])).arg(str(error)))
                return False
        
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
            CONF.set(self.ID, 'wrap', checked)
    
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


#TODO: add a combo box to select a date from the shown history
class HistoryLog(PluginWidget):
    """
    History log widget
    """
    ID = 'historylog'
    def __init__(self, parent):
        PluginWidget.__init__(self, parent)

        # Read-only editor
        self.editor = QsciEditor(self, margin=False, language='py')
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
        
        self.history = None
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('History log')
        
    def set_rawhistory(self, rawhistory):
        """Set history log's raw history"""
        self.history = rawhistory
        self.refresh()
        
    def refresh(self):
        """Refresh widget"""
        if self.history:
            self.editor.set_text("\n".join(self.history))
            self.editor.move_cursor_to_end()
        
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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr("Press enter to validate this object name"),
                     False: self.tr('This object name is incorrect')}
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        _, valid = self.parent().interpreter.eval(unicode(qstr))
        return valid
        
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            text = self.currentText()
            if self.is_valid(text):
                self.parent().refresh(text, force=True)
                self.set_default_style()
        else:
            QComboBox.keyPressEvent(self, event)
    
class DocViewer(PluginWidget):
    """
    Docstrings viewer widget
    """
    ID = 'docviewer'
    log_path = get_conf_path('.docviewer')
    def __init__(self, parent):
        PluginWidget.__init__(self, parent)
        
        self.interpreter = None
        
        # locked = disable link with Console
        self.locked = False

        # Read-only editor
        self.editor = QsciEditor(self, margin=False, language='py')
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
        layout_edit.addWidget(self.combo)
        self.combo.setMaxCount(CONF.get(self.ID, 'max_history_entries'))
        dvhistory = self.load_dvhistory()
        self.combo.addItems( dvhistory )
        
        # Doc/source checkbox
        self.help_or_doc = QCheckBox(self.tr("Show source"))
        self.connect(self.help_or_doc, SIGNAL("stateChanged(int)"),
                     self.toggle_help)
        layout_edit.addWidget(self.help_or_doc)
        self.docstring = None
        self.autosource = False
        self.toggle_help(Qt.Unchecked)
        
        # Lock checkbox
        self.locked_button = create_toolbutton(self,
                                               callback=self.toggle_locked)
        layout_edit.addWidget(self.locked_button)
        self._update_lock_icon()

        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(layout_edit)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Doc')
        
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
        self.refresh(force=True)
        
    def toggle_locked(self):
        """
        Toggle locked state
        locked = disable link with Console
        """
        self.locked = not self.locked
        self._update_lock_icon()
        
    def _update_lock_icon(self):
        """Update locked state icon"""
        icon = get_icon("lock.png" if self.locked else "lock_open.png")
        self.locked_button.setIcon(icon)
        tip = self.tr("Unlock") if self.locked else self.tr("Lock")
        self.locked_button.setToolTip(tip)
        
    def set_interpreter(self, interpreter):
        """Bind to interpreter"""
        self.interpreter = interpreter
        self.refresh()
        
    def refresh(self, text=None, force=False):
        """Refresh widget"""
        if self.locked and not force:
            return
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
        if self.interpreter is None:
            return
        obj_text = unicode(obj_text)
        hlp_text = None
        obj, valid = self.interpreter.eval(obj_text)
        if valid:
            if self.docstring:
                hlp_text = getdoc(obj)
                if hlp_text is None:
                    self.help_or_doc.setChecked(True)
                    return
            else:
                try:
                    hlp_text = getsource(obj)
                except (TypeError, IOError):
                    hlp_text = self.tr("No source code available.")
        if hlp_text is None:
            hlp_text = self.tr("No documentation available.")
        self.editor.set_text(hlp_text)
        self.editor.move_cursor_to_start()
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

