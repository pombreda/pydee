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

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QMessageBox, QFontDialog,
                         QSplitter, QToolBar, QAction, QApplication)
from PyQt4.QtCore import SIGNAL, QStringList, Qt

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib import encoding
from pydeelib.config import CONF, get_conf_path, get_icon, get_font, set_font
from pydeelib.qthelpers import (create_action, add_actions, mimedata2url,
                                get_filetype_icon, create_toolbutton)
from pydeelib.widgets.qscieditor import QsciEditor
from pydeelib.widgets.tabs import Tabs
from pydeelib.widgets.findreplace import FindReplace
from pydeelib.widgets.classbrowser import ClassBrowser
from pydeelib.plugins import PluginWidget


def is_python_script(fname):
    return osp.splitext(fname)[1][1:] in ('py', 'pyw')


class TabbedEditor(Tabs):
    def __init__(self, parent, actions):
        Tabs.__init__(self, parent, actions)
        add_actions(self.menu, self.get_actions())
        
        self.plugin = parent
        self.ID = self.plugin.ID
        self.interactive_console = self.plugin.main.console
        
        self.connect(self, SIGNAL('switch_data(int,int)'), self.switch_data)
        self.connect(self, SIGNAL("close_tab(int)"), self.close_file)
        self.close_button = create_toolbutton(self,
                                          icon=get_icon("fileclose.png"),
                                          triggered=self.close_file,
                                          tip=self.tr("Close current script"))
        self.setCornerWidget(self.close_button)
        self.connect(self, SIGNAL('currentChanged(int)'), self.current_changed)
        
        self.filenames = []
        self.encodings = []
        self.editors = []
        self.classes = []
        
        self.plugin.register_tabbededitor(self)
            
        # Accepting drops
        self.setAcceptDrops(True)

    def get_actions(self):
        # Splitting
        versplit_action = create_action(self, self.tr("Split vertically"),
            icon="versplit.png",
            tip=self.tr("Split vertically this editor window"),
            triggered=lambda: self.split(vertically=True))
        horsplit_action = create_action(self, self.tr("Split horizontally"),
            icon="horsplit.png",
            tip=self.tr("Split horizontally this editor window"),
            triggered=lambda: self.split(vertically=False))
        return (None, versplit_action, horsplit_action)
        
    def split(self, vertically=True):
        if len(self.filenames) <= 1:
            return
        if vertically:
            self.emit(SIGNAL("split_vertically()"))
        else:
            self.emit(SIGNAL("split_horizontally()"))
        
    def get_current_filename(self):
        if self.filenames:
            return self.filenames[ self.currentIndex() ]
        
    def set_current_filename(self, filename):
        if filename in self.filenames:
            index = self.filenames.index(filename)
            self.setCurrentIndex(index)
            self.editors[index].setFocus()
            return True

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
    
    def close_file(self, index=None):
        """Close current file"""
        if index is None:
            if self.count():
                index = self.currentIndex()
            else:
                self.plugin.find_widget.set_editor(None)
                return
        is_ok = self.save_if_changed(cancelable=True, index=index)
        if is_ok:
            self.filenames.pop(index)
            self.encodings.pop(index)
            self.editors.pop(index)
            self.classes.pop(index)
            self.plugin.classbrowser.clear() # Clearing class browser contents
            self.removeTab(index)
            self.plugin.refresh()
            if not self.filenames:
                # Tabbed editor is empty: removing it
                # (if it's not the first tabbed editor)
                self.plugin.unregister_tabbededitor(self)
        return is_ok

    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass
        
    def save_if_changed(self, cancelable=False, index=None):
        """Ask user to save file if modified"""
        if index is None:
            indexes = range(self.count())
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
            self.setCurrentIndex(index)
            filename = self.filenames[index]
            if filename == self.plugin.file_path or yes_all:
                if not self.save():
                    return False
            elif self.editors[index].isModified():
                answer = QMessageBox.question(self,
                    self.plugin.get_widget_title(),
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
    
    def save(self, index=None, force=False):
        """Save file"""
        if index is None:
            # Save the currently edited file
            if not self.count():
                return
            index = self.currentIndex()
            
        if not self.editors[index].isModified() and not force:
            return True
        txt = unicode(self.editors[index].get_text())
        try:
            self.encodings[index] = encoding.write(txt,
                                                   self.filenames[index],
                                                   self.encodings[index])
            self.editors[index].setModified(False)
            self.modification_changed(index=index)
            self.analyze_script(index)
            self.update_classbrowser(index)
            return True
        except EnvironmentError, error:
            QMessageBox.critical(self, self.tr("Save"),
            self.tr("<b>Unable to save script '%1'</b>"
                    "<br><br>Error message:<br>%2") \
            .arg(osp.basename(self.filenames[index])).arg(str(error)))
            return False
        
    def save_all(self):
        """Save all opened files"""
        for index in range(self.count()):
            self.save(index)
    
    def update_classbrowser(self, index=None):
        """Update class browser data"""
        if index is None:
            index = self.currentIndex()
        fname = self.filenames[index]
        if CONF.get(self.ID, 'class_browser') and is_python_script(fname):
            refresh = self.plugin.classbrowser.refresh
            self.classes[index] = refresh(self.classes[index])
    
    def analyze_script(self, index=None):
        """Analyze current script with pyflakes"""
        if index is None:
            index = self.currentIndex()
        fname = self.filenames[index]
        if CONF.get(self.ID, 'code_analysis') and is_python_script(fname):
            self.editors[index].do_code_analysis(fname)
        self.__refresh_code_analysis_buttons(index)
            
    def __refresh_code_analysis_buttons(self, index):
        """Refresh previous/next warning toolbar buttons state"""
        if index >= 0:
            state = len(self.editors[index].marker_lines) and \
                    CONF.get(self.ID, 'code_analysis')
            self.plugin.set_warning_actions_state(state)
        
    def current_changed(self, index):
        """Tab index has changed"""
        if self.currentIndex() != -1:
            self.currentWidget().setFocus()
        # no need to refresh anymore: when focus changes, editor is refreshed
#        self.refresh(index)
        
    def focus_changed(self):
        """Editor focus has changed"""
        fwidget = QApplication.focusWidget()
        if fwidget in self.editors:
            self.refresh(self.editors.index(fwidget))
        
    def refresh(self, index=None):
        """Refresh tabwidget"""
        if index is None:
            index = self.currentIndex()
        # Set current editor
        title = self.plugin.get_widget_title()
        if self.count():
            index = self.currentIndex()
            editor = self.editors[index]
            editor.setFocus()
            fname = self.filenames[index]
            title += " - "+osp.basename(fname)
            if CONF.get(self.ID, 'class_browser'):
                refresh = self.plugin.classbrowser.refresh
                refresh(self.classes[index], update=False)
        else:
            editor = None
        if self.plugin.dockwidget:
            self.plugin.dockwidget.setWindowTitle(title)
        # Update the modification-state-dependent parameters
        self.modification_changed()
        # Update FindReplace binding
        self.plugin.find_widget.set_editor(editor, refresh=False)
        # Update code analysis buttons
        self.__refresh_code_analysis_buttons(index)
        
    def get_title(self, filename):
        """Return tab title"""
        if filename != self.plugin.file_path:
            return osp.basename(filename)
        else:
            return unicode(self.tr("Temporary file"))

    def modification_changed(self, state=None, index=None):
        """
        Current editor's modification state has changed
        --> change tab title depending on new modification state
        --> enable/disable save/save all actions
        """
        if index is None:
            index = self.currentIndex()
        if index == -1:
            return
        if state is None:
            state = self.editors[index].isModified()
        title = self.get_title(self.filenames[index])
        if state:
            title += "*"
        elif title.endswith('*'):
            title = title[:-1]
        self.setTabText(index, title)
        # Toggle save/save all actions state
        self.plugin.save_action.setEnabled(state)
        if self.count() > 1:
            state = False
            for ind in range(self.count()):
                if self.editors[ind].isModified():
                    state = True
                    break
        self.plugin.save_all_action.setEnabled(state)
        
    def load(self, filename, goto=0):
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
                     self.modification_changed)
        self.connect(editor, SIGNAL("focus_changed()"),
                     lambda: self.plugin.emit(SIGNAL("focus_changed()")))
        self.connect(editor, SIGNAL("focus_changed()"), self.focus_changed)
        self.editors.append(editor)

        self.classes.append( (filename, None, None) )
        
        title = self.get_title(filename)
        index = self.addTab(editor, title)
        self.setTabToolTip(index, filename)
        self.setTabIcon(index, get_filetype_icon(filename))
        
        self.plugin.find_widget.set_editor(editor)
       
        self.modification_changed()

        self.analyze_script(index)
        self.update_classbrowser(index)
        
        self.setCurrentIndex(index)
        
        editor.setFocus()
        
        if goto > 0:
            editor.highlight_line(goto)
    
    def exec_script_extconsole(self, ask_for_arguments=False,
                               interact=False, debug=False):
        """Run current script in another process"""
        if self.save():
            index = self.currentIndex()
            fname = osp.abspath(self.filenames[index])
            wdir = osp.dirname(fname)
            self.plugin.emit(SIGNAL('open_external_console(QString,QString,bool,bool,bool)'),
                             fname, wdir, ask_for_arguments, interact, debug)
            if not interact and not debug:
                # If external console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # current external shell automatically
                # (see PluginWidget.visibility_changed method)
                self.editors[index].setFocus()
    
    def exec_script(self, set_focus=False):
        """Run current script"""
        if self.save():
            index = self.currentIndex()
            self.interactive_console.run_script(self.filenames[index],
                                                silent=True,
                                                set_focus=set_focus)
            if not set_focus:
                # If interactive console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # interactive shell automatically
                # (see PluginWidget.visibility_changed method)
                self.editors[index].setFocus()
        
    def exec_selected_text(self):
        """Run selected text in current script and set focus to shell"""
        editor = self.currentWidget()
        ls = editor.get_line_separator()
        
        line_from, _index_from, line_to, index_to = editor.getSelection()
        if line_from != line_to:
            # Multiline selection -> first line must be entirely selected
            editor.setSelection(line_from, 0, line_to, index_to)
        lines = unicode( editor.selectedText() )
        
        # If there is a common indent to all lines, remove it
        min_indent = 999
        for line in lines.split(ls):
            if line.strip():
                min_indent = min(len(line)-len(line.lstrip()), min_indent)
        if min_indent:
            lines = [line[min_indent:] for line in lines.split(ls)]
            lines = ls.join(lines)

        last_line = lines.split(ls)[-1]
        if last_line.strip() == unicode(editor.text(line_to)).strip():
            # If last line is complete, add an EOL character
            lines += ls
            
        self.interactive_console.shell.execute_lines(lines)
        self.interactive_console.shell.setFocus()
        
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
                self.plugin.load(files)
        elif source.hasText():
            editor = self.currentWidget()
            if editor is not None:
                editor.insert_text( source.text() )
        event.acceptProposedAction()


class SplitEditor(QSplitter):
    def __init__(self, parent, actions, orientation=Qt.Vertical):
        QSplitter.__init__(self, orientation, parent)
        self.setChildrenCollapsible(False)
        self.plugin = parent
        self.tab_actions = actions
        tabbededitor = TabbedEditor(self.plugin, actions)
        self.connect(tabbededitor, SIGNAL("split_vertically()"),
                     lambda: self.split(orientation=Qt.Vertical))
        self.connect(tabbededitor, SIGNAL("split_horizontally()"),
                     lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(tabbededitor)
        
    def split(self, orientation=Qt.Vertical):
        new_spliteditor = SplitEditor(self.plugin, self.tab_actions,
                                      orientation)
        self.addWidget(new_spliteditor)


#TODO: Implement editor window horizontal/vertical splitting
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
                
        # Class browser
        self.classbrowser = ClassBrowser(self)
        self.classbrowser.setVisible( CONF.get(self.ID, 'class_browser') )
        self.connect(self.classbrowser, SIGNAL('go_to_line(int)'),
                     self.go_to_line)
        
        self.tabbededitors = []
        
        # Double splitter
        self.spliteditor = SplitEditor(self, self.tab_actions)
        
        cb_splitter = QSplitter(self)
        cb_splitter.addWidget(self.spliteditor)
        cb_splitter.addWidget(self.classbrowser)
        cb_splitter.setStretchFactor(0, 3)
        cb_splitter.setStretchFactor(1, 1)
        layout.addWidget(cb_splitter)
        
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        self.recent_files = CONF.get(self.ID, 'recent_files', [])
        
        filenames = CONF.get(self.ID, 'filenames', [])
        if filenames:
            self.load(filenames)
            self.set_current_filename(CONF.get(self.ID, 'current_filename', ''))
        else:
            self.load_temp_file()
        
        self.last_focus_tabbededitor = None
        self.connect(self, SIGNAL("focus_changed()"),
                     self.save_focus_tabbededitor)
        
    def __get_focus_tabbededitor(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, QsciEditor):
            for tabbededitor in self.tabbededitors:
                if fwidget is tabbededitor.currentWidget():
                    return tabbededitor
        
    def save_focus_tabbededitor(self):
        tabbededitor = self.__get_focus_tabbededitor()
        if tabbededitor is not None:
            self.last_focus_tabbededitor = tabbededitor
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Editor')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.get_current_editor()
        
    def register_tabbededitor(self, tabbededitor):
        self.tabbededitors.append(tabbededitor)
        self.last_focus_tabbededitor = tabbededitor
        
    def unregister_tabbededitor(self, tabbededitor):
        """Removing tabbed editor only if it's not the last remaining"""
        if len(self.tabbededitors) > 1:
            self.tabbededitors.pop(self.tabbededitors.index(tabbededitor))
            tabbededitor.close() #XXX: remove widget from splitter

    def get_current_tabbededitor(self):
        if len(self.tabbededitors) == 1:
            return self.tabbededitors[0]
        else:
            tabbededitor = self.__get_focus_tabbededitor()
            if tabbededitor is None:
                return self.last_focus_tabbededitor
            else:
                return tabbededitor
        
    def get_current_editor(self):
        tabbededitor = self.get_current_tabbededitor()
        if tabbededitor is not None:
            return tabbededitor.currentWidget()
        
    def get_current_filename(self):
        tabbededitor = self.get_current_tabbededitor()
        if tabbededitor is not None:
            return tabbededitor.get_current_filename()
        
    def is_file_opened(self, filename=None):
        if filename is None:
            # Is there any file opened?
            return self.get_current_editor() is not None
        else:
            for tabbededitor in self.tabbededitors:
                if filename in tabbededitor.filenames:
                    return True
        
    def set_current_filename(self, filename):
        """Set focus to *filename* if this file has been opened"""
        tabbededitor = self.get_current_tabbededitor()
        if tabbededitor is not None:
            return tabbededitor.set_current_filename(filename)
    
    def refresh_file_dependent_actions(self):
        """Enable/disable file dependent actions
        (only if dockwidget is visible)"""
        if self.dockwidget and self.dockwidget.isVisible():
            enable = self.get_current_editor() is not None
            for action in self.file_dependent_actions:
                action.setEnabled(enable)
    
    def refresh(self):
        """Refresh editor plugin"""
        #XXX: refresh TabbedEditor instances!!! ???
        self.refresh_file_dependent_actions()
        
    def add_recent_file(self, fname):
        """Add to recent file list"""
        if fname is None:
            return
        if not fname in self.recent_files:
            self.recent_files.insert(0, fname)
            if len(self.recent_files) > 9:
                self.recent_files.pop(-1)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        PluginWidget.visibility_changed(self, enable)
        if self.dockwidget.isWindow():
            self.dock_toolbar.show()
        else:
            self.dock_toolbar.hide()
        self.refresh()

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
            triggered = self.close_file)
        self.close_all_action = create_action(self, self.tr("Close all"),
            "Ctrl+Alt+W", 'filecloseall.png',
            self.tr("Close all opened files"),
            triggered = self.close_all_files)
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
            self.tr("Classes and functions"), None, 'class_browser.png',
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
                self.save_all_action, None, self.previous_warning_action,
                self.next_warning_action, classbrowser_action,
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
        
    def split(self, orientation):
        """Split editor window in two parts"""
        self.spliteditor.split(orientation)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        filenames = []
        for tabbededitor in self.tabbededitors:
            filenames += tabbededitor.filenames
        CONF.set(self.ID, 'filenames', filenames)
        CONF.set(self.ID, 'current_filename', self.get_current_filename())
        CONF.set(self.ID, 'recent_files', self.recent_files)
        is_ok = True
        for tabbededitor in self.tabbededitors:
            is_ok = is_ok and tabbededitor.save_if_changed(cancelable)
            if not is_ok and cancelable:
                break
        return is_ok
    
    def go_to_line(self, lineno):
        """Go to line lineno and highlight it"""
        self.get_current_editor().highlight_line(lineno)
    
    def indent(self):
        """Indent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.indent()

    def unindent(self):
        """Unindent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unindent()
    
    def comment(self):
        """Comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.comment()

    def uncomment(self):
        """Uncomment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.uncomment()
    
    def blockcomment(self):
        """Block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.blockcomment()

    def unblockcomment(self):
        """Un-block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unblockcomment()
        
    def set_workdir(self):
        """Set working directory as current script directory"""
        fname = self.get_current_filename()
        if fname is not None:
            directory = osp.dirname(osp.abspath(fname))
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
                       '"""', osp.basename(fname), '"""', '', '']
            text = os.linesep.join(default)
            encoding.write(unicode(text), fname, 'utf-8')
            self.load(fname)
            
    def set_warning_actions_state(self, state):
        """Refresh previous/next warning toolbar buttons state"""
        self.previous_warning_action.setEnabled(state)
        self.next_warning_action.setEnabled(state)
    
    def go_to_next_warning(self):
        editor = self.get_current_editor()
        editor.go_to_next_warning()
    
    def go_to_previous_warning(self):
        editor = self.get_current_editor()
        editor.go_to_previous_warning()
            
    def close_all_files(self):
        """Close all opened scripts"""
        for tabbededitor in self.tabbededitors:
            tabbededitor.close_all_files()
        
    def load(self, filenames=None, goto=0):
        """Load a text file"""
        if not filenames:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filenames = unicode(action.data().toString())
        if not filenames:
            basedir = os.getcwdu()
            fname = self.get_current_filename()
            if fname is not None and fname != self.file_path:
                basedir = osp.dirname(fname)
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            filenames = QFileDialog.getOpenFileNames(self,
                          self.tr("Open Python script"), basedir,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            filenames = list(filenames)
            if len(filenames):
#                directory = osp.dirname(unicode(filenames[-1]))
#                self.emit(SIGNAL("open_dir(QString)"), directory)
                filenames = [osp.normpath(unicode(fname)) \
                             for fname in filenames]
            else:
                return
            
        if self.dockwidget:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        
        if not isinstance(filenames, (list, QStringList)):
            filenames = [osp.abspath(unicode(filenames))]
        else:
            filenames = [osp.abspath(unicode(fname)) \
                         for fname in list(filenames)]
            
        for filename in filenames:
            for tabbededitor in self.tabbededitors:
                # -- Do not open an already opened file
                if tabbededitor.set_current_filename(filename):
                    break
            else:
                # -- Not a valid filename:
                if not osp.isfile(filename):
                    continue
                # --
                tabbededitor = self.get_current_tabbededitor()
                tabbededitor.load(filename, goto)
                self.add_recent_file(filename)
                
    def close_file(self):
        """Close current file"""
        tabbededitor = self.get_current_tabbededitor()
        tabbededitor.close_file()
                
    def save(self, index=None, force=False):
        """Save file"""
        tabbededitor = self.get_current_tabbededitor()
        tabbededitor.save(index=index, force=force)
                
    def save_as(self):
        """Save *as* the currently edited file"""
        fname = self.get_current_filename()
        if fname is not None:
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            filename = QFileDialog.getSaveFileName(self,
                          self.tr("Save Python script"), fname,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            if filename:
                filename = unicode(filename)
                tabbededitor = self.get_current_tabbededitor()
                index = tabbededitor.currentIndex()
                tabbededitor.filenames[index] = filename
            else:
                return False
            self.save(force=True)
            # Refresh the explorer widget if it exists:
            self.emit(SIGNAL("refresh_explorer()"))
        
    def save_all(self):
        """Save all opened files"""
        for tabbededitor in self.tabbededitors:
            tabbededitor.save_all()
    
    def exec_script_extconsole(self, ask_for_arguments=False,
                               interact=False, debug=False):
        """Run current script in another process"""
        tabbededitor = self.get_current_tabbededitor()
        tabbededitor.exec_script_extconsole(ask_for_arguments=ask_for_arguments,
                                            interact=interact, debug=debug)
    
    def exec_script(self, set_focus=False):
        """Run current script"""
        tabbededitor = self.get_current_tabbededitor()
        tabbededitor.exec_script(set_focus=set_focus)
    
    def exec_script_and_interact(self):
        """Run current script and set focus to shell"""
        self.exec_script(set_focus=True)
        
    def exec_selected_text(self):
        """Run selected text in current script and set focus to shell"""
        tabbededitor = self.get_current_tabbededitor()
        tabbededitor.exec_selected_text()
        
    def change_font(self):
        """Change editor font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                          self.tr("Select a new font"))
        if valid:
            for tabbededitor in self.tabbededitors:
                for editor in tabbededitor.editors:
                    editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if hasattr(self, 'tabbededitors'): #XXX Is it still necessary?
            for tabbededitor in self.tabbededitors:
                for editor in tabbededitor.editors:
                    editor.set_wrap_mode(checked)
            CONF.set(self.ID, 'wrap', checked)
            
    def toggle_code_folding(self, checked):
        """Toggle code folding"""
        if hasattr(self, 'tabbededitors'): #XXX Is it still necessary?
            for tabbededitor in self.tabbededitors:
                for editor in tabbededitor.editors:
                    editor.setup_margins(linenumbers=True,
                              code_folding=checked,
                              code_analysis=CONF.get(self.ID, 'code_analysis'))
                    if not checked:
                        editor.unfold_all()
            CONF.set(self.ID, 'code_folding', checked)
            
    def toggle_code_analysis(self, checked):
        """Toggle code analysis"""
        if hasattr(self, 'tabbededitors'): #XXX Is it still necessary?
            CONF.set(self.ID, 'code_analysis', checked)
            current_tabbededitor = self.get_current_tabbededitor()
            current_index = current_tabbededitor.currentIndex()
            for tabbededitor in self.tabbededitors:
                for index, editor in enumerate(tabbededitor.editors):
                    editor.setup_margins(linenumbers=True,
                              code_analysis=checked,
                              code_folding=CONF.get(self.ID, 'code_folding'))
                    if index != current_index:
                        tabbededitor.analyze_script(index)
            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            current_tabbededitor.analyze_script()

    def toggle_classbrowser(self, checked):
        """Toggle class browser"""
        if hasattr(self, 'tabwidget'):
            CONF.set(self.ID, 'class_browser', checked)
            if checked:
                self.classbrowser.show()
                current_tabbededitor = self.get_current_tabbededitor()
                current_index = current_tabbededitor.currentIndex()
                for tabbededitor in self.tabbededitors:
                    for index in range(tabbededitor.count()):
                        if index != current_index:
                            tabbededitor.update_classbrowser(index)
                # We must update the current editor after the others:
                # (otherwise, we would show class tree of the last editor
                #  instead of showing the one of the current editor)
                current_tabbededitor.update_classbrowser()
            else:
                self.classbrowser.hide()
    
