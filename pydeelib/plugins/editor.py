# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Editor widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QHBoxLayout, QVBoxLayout, QLabel, QFileDialog,
                         QSizePolicy, QMessageBox, QFontDialog, QSplitter,
                         QCheckBox, QToolBar, QAction, QComboBox)
from PyQt4.QtCore import Qt, SIGNAL, QStringList

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib import encoding
from pydeelib.config import CONF, get_conf_path, get_icon, get_font, set_font
from pydeelib.qthelpers import (create_action, add_actions, mimedata2url,
                                 get_filetype_icon, create_toolbutton)
from pydeelib.dochelpers import getdoc, getsource
try:
    from pydeelib.widgets.qscieditor import QsciEditor
except ImportError, e:
    raise ImportError, str(e) + \
        "\nPydee v0.3.23+ is exclusively based on QScintilla2\n" + \
        "(http://www.riverbankcomputing.co.uk/software/qscintilla)"
from pydeelib.widgets.tabs import Tabs
from pydeelib.widgets.comboboxes import EditableComboBox
from pydeelib.widgets.findreplace import FindReplace
from pydeelib.widgets.classbrowser import ClassBrowser
from pydeelib.plugins import PluginWidget


def is_python_script(fname):
    return osp.splitext(fname)[1][1:] in ('py', 'pyw')


#TODO: Implement multiple editor windows
#      (editor tab -> context menu -> "Open in a new window")

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
        self.connect(self.tabwidget, SIGNAL('switch_data(int,int)'),
                     self.switch_data)
        self.connect(self.tabwidget, SIGNAL("close_tab(int)"), self.close)
        self.close_button = create_toolbutton(self.tabwidget,
                                          icon=get_icon("fileclose.png"),
                                          callback=self.close,
                                          tip=self.tr("Close current script"))
        self.tabwidget.setCornerWidget(self.close_button)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh)
        
        # Class browser
        self.classbrowser = ClassBrowser(self)
        self.classbrowser.setVisible( CONF.get(self.ID, 'class_browser') )
        self.connect(self.classbrowser, SIGNAL('go_to_line(int)'),
                     self.go_to_line)
        
        splitter = QSplitter(self)
        splitter.addWidget(self.tabwidget)
        splitter.addWidget(self.classbrowser)
        splitter.setSizes([3, 1])
        layout.addWidget(splitter)
        
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        self.recent_files = CONF.get(self.ID, 'recent_files', [])
        self.filenames = []
        self.encodings = []
        self.editors = []
        self.classes = []
        
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
            self.classbrowser.refresh(self.classes[index], update=False)
        else:
            editor = None
        if self.dockwidget:
            self.dockwidget.setWindowTitle(title)
            
        self.find_widget.set_editor(editor, refresh=False)
        
        self.__refresh_code_analysis_buttons(index)

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
        # Toggle save/save all actions state
        self.save_action.setEnabled(state)
        if self.tabwidget.count() > 1:
            state = False
            for ind in range(self.tabwidget.count()):
                if self.editors[ind].isModified():
                    state = True
                    break
        self.save_all_action.setEnabled(state)

    def set_actions(self):
        """Setup actions"""
        self.new_action = create_action(self, self.tr("New..."), "Ctrl+N",
            'filenew.png', self.tr("Create a new Python script"),
            triggered = self.new)
        self.open_action = create_action(self, self.tr("Open..."), "Ctrl+O",
            'fileopen.png', self.tr("Open text file"),
            triggered = self.load)
        self.save_action = create_action(self, self.tr("Save"), "Ctrl+S",
            'filesave.png', self.tr("Save current file"),
            triggered = self.save)
        self.save_all_action = create_action(self, self.tr("Save all"),
            "Ctrl+Shift+S", 'save_all.png', self.tr("Save all opened files"),
            triggered = self.save_all)
        self.save_as_action = create_action(self, self.tr("Save as..."), None,
            'filesaveas.png', self.tr("Save current file as..."),
            triggered = self.save_as)
        self.close_action = create_action(self, self.tr("Close"), "Ctrl+W",
            'fileclose.png', self.tr("Close current file"),
            triggered = self.close)
        self.close_all_action = create_action(self, self.tr("Close all"),
            "Ctrl+Maj+W", 'filecloseall.png',
            self.tr("Close all opened files"),
            triggered = self.close_all)
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
            self.tr("Run in e&xternal console"), "F5", 'execute_external.png',
            self.tr("Run current script in external console"
                    "\n(external console is executed in a separate process)"),
            triggered=lambda: self.exec_script_extconsole())
        self.exec_process_interact_action = create_action(self,
            self.tr("Run and interact"), "Shift+F5",
            tip=self.tr("Run current script in external console and interact "
                        "\nwith Python interpreter when program has finished"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.exec_script_extconsole(interact=True))
        self.exec_process_args_action = create_action(self,
            self.tr("Run with arguments"), "Ctrl+F5",
            tip=self.tr("Run current script in external console specifying "
                        "command line arguments"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.exec_script_extconsole( \
                                           ask_for_arguments=True))
        self.exec_process_debug_action = create_action(self,
            self.tr("Debug"), "Ctrl+Shift+F5",
            tip=self.tr("Debug current script in external console"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.exec_script_extconsole( \
                                           ask_for_arguments=True, debug=True))
        
        self.previous_warning_action = create_action(self,
            self.tr("Previous warning/error"), icon='prev_wng.png',
            tip=self.tr("Go to previous code analysis warning/error"),
            triggered=self.go_to_previous_warning)
        self.next_warning_action = create_action(self,
            self.tr("Next warning/error"), icon='next_wng.png',
            tip=self.tr("Go to next code analysis warning/error"),
            triggered=self.go_to_next_warning)
        
        self.comment_action = create_action(self, self.tr("Comment"), "Ctrl+3",
            'comment.png', self.tr("Comment current line or selection"),
            triggered=self.comment)
        self.uncomment_action = create_action(self, self.tr("Uncomment"),
            "Ctrl+2",
            'uncomment.png', self.tr("Uncomment current line or selection"),
            triggered=self.uncomment)
        self.blockcomment_action = create_action(self,
            self.tr("Add block comment"), "Ctrl+4",
            tip = self.tr("Add block comment around current line or selection"),
            triggered=self.blockcomment)
        self.unblockcomment_action = create_action(self,
            self.tr("Remove block comment"), "Ctrl+5",
            tip = self.tr("Remove comment block around "
                          "current line or selection"),
            triggered=self.unblockcomment)
                
        # ----------------------------------------------------------------------
        # The following action shortcuts are hard-coded in QsciEditor
        # keyPressEvent handler (the shortcut is here only to inform user):
        # (window_context=False -> disable shortcut for other widgets)
        self.indent_action = create_action(self, self.tr("Indent"), "Tab",
            'indent.png', self.tr("Indent current line or selection"),
            window_context=False)
        self.unindent_action = create_action(self, self.tr("Unindent"),
            "Shift+Tab",
            'unindent.png', self.tr("Unindent current line or selection"),
            window_context=False)
        # ----------------------------------------------------------------------
        
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set editor font style"),
            triggered=self.change_font)
        analyze_action = create_action(self, self.tr("Code analysis"),
            toggled=self.toggle_code_analysis)
        analyze_action.setChecked( CONF.get(self.ID, 'code_analysis') )
        classbrowser_action = create_action(self,
            self.tr("Classes and functions"),
            toggled=self.toggle_classbrowser)
        classbrowser_action.setChecked( CONF.get(self.ID, 'class_browser') )
        fold_action = create_action(self, self.tr("Code folding"),
            toggled=self.toggle_code_folding)
        fold_action.setChecked( CONF.get(self.ID, 'code_folding') )
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        workdir_action = create_action(self, self.tr("Set working directory"),
            tip=self.tr("Change working directory to current script directory"),
            triggered=self.set_workdir)
        self.file_menu_actions = [self.new_action,
                                  self.open_action,
                                  self.save_action,
                                  self.save_all_action,
                                  self.save_as_action, None,
                                  self.close_action,
                                  self.close_all_action, None,
                                  ]
        source_menu_actions = (self.comment_action, self.uncomment_action,
                self.blockcomment_action, self.unblockcomment_action,
                self.indent_action, self.unindent_action,
                None, self.exec_action, self.exec_interact_action,
                self.exec_selected_action, None, self.exec_process_action,
                self.exec_process_interact_action,self.exec_process_args_action,
                self.exec_process_debug_action,
                None, font_action, wrap_action, fold_action, analyze_action,
                classbrowser_action)
        toolbar_actions = [self.new_action, self.open_action, self.save_action,
                self.save_all_action,
                None, self.previous_warning_action, self.next_warning_action,
                None, self.exec_action, self.exec_selected_action,
                self.exec_process_action]
        self.dock_toolbar_actions = toolbar_actions + \
                [self.exec_interact_action, self.comment_action,
                 self.uncomment_action, self.indent_action,
                 self.unindent_action]
        self.file_dependent_actions = (self.save_action, self.save_as_action,
                self.save_all_action, self.exec_action,
                self.exec_interact_action, self.exec_selected_action,
                self.exec_process_action, self.exec_process_interact_action,
                self.exec_process_args_action, self.exec_process_debug_action,
                workdir_action, self.close_action, self.close_all_action,
                self.previous_warning_action, self.next_warning_action,
                self.blockcomment_action, self.unblockcomment_action,
                self.comment_action, self.uncomment_action,
                self.indent_action, self.unindent_action)
        self.tab_actions = (self.save_action, self.save_as_action,
                self.exec_action, self.exec_process_action,
                workdir_action, None, self.close_action)
        return (source_menu_actions, toolbar_actions)        
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        CONF.set(self.ID, 'filenames', self.filenames)
        CONF.set(self.ID, 'recent_files', self.recent_files)
        return self.save_if_changed(cancelable)
    
    def update_classbrowser(self, index=None):
        """Update class browser data"""
        if index is None:
            index = self.tabwidget.currentIndex()
        fname = self.filenames[index]
        if CONF.get(self.ID, 'class_browser') and is_python_script(fname):
            self.classes[index] = self.classbrowser.refresh(self.classes[index])
    
    def go_to_line(self, lineno):
        """Go to line lineno and highlight it"""
        self.editors[ self.tabwidget.currentIndex() ].highlight_line(lineno)
    
    def indent(self):
        """Indent current line or selection"""
        if self.tabwidget.count():
            self.editors[ self.tabwidget.currentIndex() ].indent()

    def unindent(self):
        """Unindent current line or selection"""
        if self.tabwidget.count():
            self.editors[ self.tabwidget.currentIndex() ].unindent()
    
    def comment(self):
        """Comment current line or selection"""
        if self.tabwidget.count():
            self.editors[ self.tabwidget.currentIndex() ].comment()

    def uncomment(self):
        """Uncomment current line or selection"""
        if self.tabwidget.count():
            self.editors[ self.tabwidget.currentIndex() ].uncomment()
    
    def blockcomment(self):
        """Block comment current line or selection"""
        if self.tabwidget.count():
            self.editors[ self.tabwidget.currentIndex() ].blockcomment()

    def unblockcomment(self):
        """Un-block comment current line or selection"""
        if self.tabwidget.count():
            self.editors[ self.tabwidget.currentIndex() ].unblockcomment()
        
    def set_workdir(self):
        """Set working directory as current script directory"""
        if self.tabwidget.count():
            filename = self.filenames[ self.tabwidget.currentIndex() ]
            directory = osp.dirname(osp.abspath(filename))
            self.emit(SIGNAL("open_dir(QString)"), directory)
        
    def load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if not osp.isfile(self.file_path):
            # Creating temporary file
            default = ['# -*- coding: utf-8 -*-',
                       '"""',
                       self.tr("Pydee Editor"),
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
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        fname = QFileDialog.getSaveFileName(self, self.tr("New Python script"),
                    fname, self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
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
    
    def analyze_script(self, index=None):
        """Analyze current script with pyflakes"""
        if index is None:
            index = self.tabwidget.currentIndex()
        fname = self.filenames[index]
        if CONF.get(self.ID, 'code_analysis') and is_python_script(fname):
            self.editors[index].do_code_analysis(fname)
        self.__refresh_code_analysis_buttons(index)
            
    def __refresh_code_analysis_buttons(self, index):
        """Refresh previous/next warning toolbar buttons state"""
        if index >= 0:
            state = len(self.editors[index].marker_lines)
            self.previous_warning_action.setEnabled(state)
            self.next_warning_action.setEnabled(state)
    
    def go_to_next_warning(self):
        index = self.tabwidget.currentIndex()
        self.editors[index].go_to_next_warning()
    
    def go_to_previous_warning(self):
        index = self.tabwidget.currentIndex()
        self.editors[index].go_to_previous_warning()
    
    def exec_script_extconsole(self, ask_for_arguments=False,
                               interact=False, debug=False):
        """Run current script in another process"""
        if self.save():
            index = self.tabwidget.currentIndex()
            fname = osp.abspath(self.filenames[index])
            wdir = osp.dirname(fname)
            self.emit(SIGNAL('open_external_console(QString,QString,bool,bool,bool)'),
                      fname, wdir, ask_for_arguments, interact, debug)
    
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

    def save_if_changed(self, cancelable=False, index=None):
        """Ask user to save file if modified"""
        if index is None:
            indexes = range(self.tabwidget.count())
        else:
            indexes = [index]
        buttons = QMessageBox.Yes | QMessageBox.No
        if cancelable:
            buttons |= QMessageBox.Cancel
        unsaved_nb = 0
        for index in indexes:
            if self.editors[index].isModified():
                unsaved_nb += 1
        if not unsaved_nb:
            # No file to save
            return True
        if unsaved_nb > 1:
            buttons |= QMessageBox.YesAll | QMessageBox.NoAll
        yes_all = False
        for index in indexes:
            self.tabwidget.setCurrentIndex(index)
            filename = self.filenames[index]
            if filename == self.file_path or yes_all:
                if not self.save():
                    return False
            elif self.editors[index].isModified():
                answer = QMessageBox.question(self, self.get_widget_title(),
                    self.tr("<b>%1</b> has been modified."
                            "<br>Do you want to save "
                            "changes?").arg(osp.basename(filename)), buttons)
                if answer == QMessageBox.Yes:
                    if not self.save():
                        return False
                elif answer == QMessageBox.YesAll:
                    if not self.save():
                        return False
                    yes_all = True
                elif answer == QMessageBox.NoAll:
                    return True
                elif answer == QMessageBox.Cancel:
                    return False
        return True
    
    def close(self, index=None):
        """Close current file"""
        if index is None:
            if self.tabwidget.count():
                index = self.tabwidget.currentIndex()
            else:
                self.find_widget.set_editor(None)
                return
        is_ok = self.save_if_changed(cancelable=True, index=index)
        if is_ok:
            self.filenames.pop(index)
            self.encodings.pop(index)
            self.editors.pop(index)
            self.classes.pop(index)
            self.classbrowser.clear() # Clearing class browser contents
            self.tabwidget.removeTab(index)
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
        
    def switch_data(self, index1, index2):
        """
        Switching tabs
        In fact tabs have already been switched by the tabwidget
        but we have to switch the self.editors/fnames elements too
        """
        self.editors[index2], self.editors[index1] = \
            self.editors[index1], self.editors[index2]
        self.filenames[index2], self.filenames[index1] = \
            self.filenames[index1], self.filenames[index2]
        self.encodings[index2], self.encodings[index1] = \
            self.encodings[index1], self.encodings[index2]
        self.classes[index2], self.classes[index1] = \
            self.classes[index1], self.classes[index2]
        
    def load(self, filenames=None, goto=0):
        """Load a text file"""
        if not filenames:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filenames = unicode(action.data().toString())
        if not filenames:
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            basedir = os.getcwdu()
            if self.filenames:
                index = self.tabwidget.currentIndex()
                if self.filenames[index] != self.file_path:
                    basedir = osp.dirname(self.filenames[index])
            filenames = QFileDialog.getOpenFileNames(self,
                          self.tr("Open Python script"), basedir,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            filenames = list(filenames)
            if len(filenames):
#                directory = osp.dirname(unicode(filenames[-1]))
#                self.emit(SIGNAL("open_dir(QString)"), directory)
                filenames = [osp.normpath(unicode(fname)) for fname in filenames]
            else:
                return
            
        if self.dockwidget:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        
        if not isinstance(filenames, (list, QStringList)):
            filenames = [osp.abspath(unicode(filenames))]
        else:
            filenames = [osp.abspath(unicode(fname)) for fname in list(filenames)]
            
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
                
                editor = QsciEditor(self, language=ext,
                            linenumbers=True,
                            code_analysis=CONF.get(self.ID, 'code_analysis'),
                            code_folding=CONF.get(self.ID, 'code_folding'))
                editor.setup_editor(txt, font=get_font('editor'),
                                    wrap=CONF.get(self.ID, 'wrap'))
                self.connect(editor, SIGNAL('modificationChanged(bool)'),
                             self.change)
                self.connect(editor, SIGNAL("focus_changed()"),
                             lambda: self.emit(SIGNAL("focus_changed()")))
                self.editors.append(editor)

                self.classes.append(None)
                self.classbrowser.set_filename(filename)
                
                title = self.get_title(filename)
                index = self.tabwidget.addTab(editor, title)
                self.tabwidget.setTabToolTip(index, filename)
                self.tabwidget.setTabIcon(index, get_filetype_icon(filename))
                
                self.find_widget.set_editor(editor)
               
                self.change()
                self.analyze_script(index)
                self.update_classbrowser(index)
                
                self.tabwidget.setCurrentIndex(index)
                
                editor.setFocus()
                self.add_recent_file(filename)
            
            if goto > 0:
                editor.highlight_line(goto)

    def save_as(self):
        """Save *as* the currently edited file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            filename = QFileDialog.getSaveFileName(self,
                          self.tr("Save Python script"), self.filenames[index],
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            if filename:
                filename = unicode(filename)
                self.filenames[index] = filename
            else:
                return False
            self.save(force=True)
            # Refresh the explorer widget if it exists:
            self.emit(SIGNAL("refresh_explorer()"))
    
    def save(self, index=None, force=False):
        """Save file"""
        if index is None:
            # Save the currently edited file
            if not self.tabwidget.count():
                return
            index = self.tabwidget.currentIndex()
            
        if not self.editors[index].isModified() and not force:
            return True
        txt = unicode(self.editors[index].get_text())
        try:
            self.encodings[index] = encoding.write(txt,
                                                   self.filenames[index],
                                                   self.encodings[index])
            self.editors[index].setModified(False)
            self.change()
            self.analyze_script(index)
            self.update_classbrowser(index)
            return True
        except IOError, error:
            QMessageBox.critical(self, self.tr("Save"),
            self.tr("<b>Unable to save script '%1'</b>"
                    "<br><br>Error message:<br>%2") \
            .arg(osp.basename(self.filenames[index])).arg(str(error)))
            return False
        
    def save_all(self):
        """Save all opened files"""
        for index in range(self.tabwidget.count()):
            self.save(index)
        
    def change_font(self):
        """Change editor font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                          self, self.tr("Select a new font"))
        if valid:
            for index in range(self.tabwidget.count()):
                self.editors[index].set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if hasattr(self, 'tabwidget'):
            for index in range(self.tabwidget.count()):
                self.editors[index].set_wrap_mode(checked)
            CONF.set(self.ID, 'wrap', checked)
            
    def toggle_code_folding(self, checked):
        """Toggle code folding"""
        if hasattr(self, 'tabwidget'):
            for editor in self.editors:
                editor.setup_margins(linenumbers=True,
                          code_folding=checked,
                          code_analysis=CONF.get(self.ID, 'code_analysis'))
                if not checked:
                    editor.unfold_all()
            CONF.set(self.ID, 'code_folding', checked)
            
    def toggle_code_analysis(self, checked):
        """Toggle code analysis"""
        if hasattr(self, 'tabwidget'):
            CONF.set(self.ID, 'code_analysis', checked)
            for index in range(self.tabwidget.count()):
                self.editors[index].setup_margins(linenumbers=True,
                          code_analysis=checked,
                          code_folding=CONF.get(self.ID, 'code_folding'))
                self.analyze_script(index)
                
    def toggle_classbrowser(self, checked):
        """Toggle class browser"""
        if hasattr(self, 'tabwidget'):
            CONF.set(self.ID, 'class_browser', checked)
            if checked:
                self.classbrowser.show()
                for index in range(self.tabwidget.count()):
                    self.update_classbrowser(index)
            else:
                self.classbrowser.hide()
    
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


#TODO: [low-priority] add a combo box to select a date from the shown history
class HistoryLog(PluginWidget):
    """
    History log widget
    """
    ID = 'historylog'
    def __init__(self, parent):
        PluginWidget.__init__(self, parent)

        # Read-only editor
        self.editor = QsciEditor(self, linenumbers=False, language='py',
                                 code_folding=True)
        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
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
        self._last_text = None

        # Read-only editor
        self.editor = QsciEditor(self, linenumbers=False, language='py',
                                 code_folding=True)
        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
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
        if (self.locked and not force):
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
        if self.dockwidget and self.dockwidget.isVisible():
            if text != self._last_text:
                self.dockwidget.raise_()
        self._last_text = text
        
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

