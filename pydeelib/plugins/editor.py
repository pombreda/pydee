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
                         QSplitter, QToolBar, QAction, QApplication, QToolBox,
                         QListWidget, QListWidgetItem, QLabel, QWidget,
                         QHBoxLayout)
from PyQt4.QtCore import SIGNAL, QStringList, Qt, QVariant, QFileInfo

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib import encoding
from pydeelib.config import CONF, get_conf_path, get_icon, get_font, set_font
from pydeelib.qthelpers import (create_action, add_actions, mimedata2url,
                                get_filetype_icon, create_toolbutton,
                                translate)
from pydeelib.widgets.qscieditor import QsciEditor, check
from pydeelib.widgets.tabs import Tabs
from pydeelib.widgets.findreplace import FindReplace
from pydeelib.widgets.classbrowser import ClassBrowser
from pydeelib.widgets.pylintgui import is_pylint_installed
from pydeelib.plugins import PluginWidget


def is_python_script(fname):
    return osp.splitext(fname)[1][1:] in ('py', 'pyw')


class TabInfo(object):
    def __init__(self, filename, encoding, editor):
        self.filename = filename
        self.encoding = encoding
        self.editor = editor
        self.classes = (filename, None, None)
        self.analysis_results = []
        self.lastmodified = QFileInfo(filename).lastModified()

class EditorTabWidget(Tabs):
    def __init__(self, parent, actions):
        Tabs.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.original_actions = actions
        self.additional_actions = self.__get_split_actions()
        self.connect(self.menu, SIGNAL("aboutToShow()"), self.__setup_menu)
        
        self.plugin = parent
        self.ID = self.plugin.ID
        self.interactive_console = self.plugin.main.console
        
        self.connect(self, SIGNAL('move_data(int,int)'), self.move_data)
        self.connect(self, SIGNAL("close_tab(int)"), self.close_file)
        self.close_button = create_toolbutton(self,
                                          icon=get_icon("fileclose.png"),
                                          triggered=self.close_file,
                                          tip=self.tr("Close current script"))
        self.setCornerWidget(self.close_button)
        self.connect(self, SIGNAL('currentChanged(int)'), self.current_changed)
        
        self.data = []
        
        self.__last_modified_flag = False
        
        self.already_closed = False
        
        self.plugin.register_editortabwidget(self)
            
        # Accepting drops
        self.setAcceptDrops(True)

    def __setup_menu(self):
        """Setup tab context menu before showing it"""
        self.menu.clear()
        if self.data:
            actions = self.original_actions
        else:
            actions = (self.plugin.new_action, self.plugin.open_action)
            self.setFocus() # --> Editor.__get_focus_editortabwidget
        add_actions(self.menu, actions + self.additional_actions)
        self.close_action.setEnabled( len(self.plugin.editortabwidgets) > 1 )

#===============================================================================
#    Horizontal/Vertical splitting
#===============================================================================
    def __get_split_actions(self):
        # Splitting
        self.versplit_action = create_action(self,
                    self.tr("Split vertically"), icon="versplit.png",
                    tip=self.tr("Split vertically this editor window"),
                    triggered=lambda: self.emit(SIGNAL("split_vertically()")))
        self.horsplit_action = create_action(self,
                    self.tr("Split horizontally"), icon="horsplit.png",
                    tip=self.tr("Split horizontally this editor window"),
                    triggered=lambda: self.emit(SIGNAL("split_horizontally()")))
        self.close_action = create_action(self,
                    self.tr("Close this panel"), icon="close_panel.png",
                    triggered=self.close_editortabwidget)
        return (None, self.versplit_action, self.horsplit_action,
                self.close_action)
        
    def reset_orientation(self):
        self.horsplit_action.setEnabled(True)
        self.versplit_action.setEnabled(True)
        
    def set_orientation(self, orientation):
        self.horsplit_action.setEnabled(orientation == Qt.Horizontal)
        self.versplit_action.setEnabled(orientation == Qt.Vertical)
        
        
#===============================================================================
    def get_current_filename(self):
        if self.data:
            return self.data[self.currentIndex()].filename
        
    def has_filename(self, filename):
        for index, finfo in enumerate(self.data):
            if filename == finfo.filename:
                return index
        
    def set_current_filename(self, filename):
        index = self.has_filename(filename)
        if index is not None:
            self.setCurrentIndex(index)
            self.data[index].editor.setFocus()
            return True
        

#===============================================================================
    def move_data(self, index_from, index_to, editortabwidget_to=None):
        """
        Move tab
        In fact tabs have already been moved by the tabwidget
        but we have to move the self.data elements too
        """
        finfo = self.data.pop(index_from)
        if editortabwidget_to is None:
            editortabwidget_to = self        
        editortabwidget_to.data.insert(index_to, finfo)
        
        if editortabwidget_to is not self:
            self.disconnect(finfo.editor, SIGNAL('modificationChanged(bool)'),
                            self.modification_changed)
            self.disconnect(finfo.editor, SIGNAL("focus_in()"),
                            self.focus_changed)
            self.connect(finfo.editor, SIGNAL('modificationChanged(bool)'),
                         editortabwidget_to.modification_changed)
            self.connect(finfo.editor, SIGNAL("focus_in()"),
                         editortabwidget_to.focus_changed)            
    
#===============================================================================
#    Close file, all files, editortabwidget
#===============================================================================
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
            self.data.pop(index)
            self.removeTab(index)
            if not self.data:
                # editortabwidget is empty: removing it
                # (if it's not the first editortabwidget)
                self.close_editortabwidget()
            self.emit(SIGNAL('opened_files_list_changed()'))
            self.emit(SIGNAL('refresh_analysis_results()'))
            self.__refresh_classbrowser()
            self.emit(SIGNAL('refresh_file_dependent_actions()'))
        return is_ok
    
    def close_editortabwidget(self):
        if self.data:
            self.close_all_files()
            if self.already_closed:
                # All opened files were closed and *self* is not the last
                # editortabwidget remaining --> *self* was automatically closed
                return
        removed = self.plugin.unregister_editortabwidget(self)
        if removed:
            self.close()
            
    def close(self):
        Tabs.close(self)
        self.already_closed = True # used in self.close_tabbeeditor

    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass
        
#===============================================================================
#    Save
#===============================================================================
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
            if self.data[index].editor.isModified():
                unsaved_nb += 1
        if not unsaved_nb:
            # No file to save
            return True
        if unsaved_nb > 1:
            buttons |= QMessageBox.YesAll | QMessageBox.NoAll
        yes_all = False
        for index in indexes:
            self.setCurrentIndex(index)
            finfo = self.data[index]
            if finfo.filename == self.plugin.file_path or yes_all:
                if not self.save():
                    return False
            elif finfo.editor.isModified():
                answer = QMessageBox.question(self,
                            self.plugin.get_widget_title(),
                            self.tr("<b>%1</b> has been modified."
                                    "<br>Do you want to save changes?") \
                                    .arg(osp.basename(finfo.filename)),
                            buttons)
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
            
        finfo = self.data[index]
        if not finfo.editor.isModified() and not force:
            return True
        txt = unicode(finfo.editor.get_text())
        try:
            finfo.encoding = encoding.write(txt, finfo.filename, finfo.encoding)
            finfo.editor.setModified(False)
            finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
            self.modification_changed(index=index)
            self.analyze_script(index)
            self.__refresh_classbrowser(index)
            return True
        except EnvironmentError, error:
            QMessageBox.critical(self, self.tr("Save"),
                            self.tr("<b>Unable to save script '%1'</b>"
                                    "<br><br>Error message:<br>%2") \
                            .arg(osp.basename(finfo.filename)).arg(str(error)))
            return False
        
    def save_all(self):
        """Save all opened files"""
        for index in range(self.count()):
            self.save(index)
    
#===============================================================================
#    Update UI
#===============================================================================
    def analyze_script(self, index=None):
        """Analyze current script with pyflakes"""
        if index is None:
            index = self.currentIndex()
        if self.data:
            finfo = self.data[index]
            fname = finfo.filename
            if CONF.get(self.ID, 'code_analysis') and is_python_script(fname):
                finfo.analysis_results = check(fname)
                finfo.editor.process_code_analysis(finfo.analysis_results)
            self.emit(SIGNAL('refresh_analysis_results()'))
        
    def get_analysis_results(self):
        if self.data:
            return self.data[self.currentIndex()].analysis_results
        
    def current_changed(self, index):
        """Tab index has changed"""
        if index != -1:
            self.currentWidget().setFocus()
        else:
            self.emit(SIGNAL('reset_statusbar()'))
        self.emit(SIGNAL('opened_files_list_changed()'))
        
    def focus_changed(self):
        """Editor focus has changed"""
        fwidget = QApplication.focusWidget()
        for finfo in self.data:
            if fwidget is finfo.editor:
                self.refresh()
        
    def __refresh_classbrowser(self, index=None, update=True):
        """Refresh class browser panel"""
        if index is None:
            index = self.currentIndex()
        enable = False
        classbrowser = self.plugin.classbrowser
        if self.data:
            finfo = self.data[index]
            if CONF.get(self.ID, 'class_browser') \
               and is_python_script(finfo.filename) and classbrowser.isVisible():
                enable = True
                classbrowser.setEnabled(True)
                classes = classbrowser.refresh(finfo.classes, update=update)
                if update:
                    finfo.classes = classes
        if not enable:
            classbrowser.setEnabled(False)
            classbrowser.clear()
            
    def __refresh_statusbar(self, index):
        """Refreshing statusbar widgets"""
        finfo = self.data[index]
        self.emit(SIGNAL('encoding_changed(QString)'), finfo.encoding)
        # Refresh cursor position status:
        line, index = finfo.editor.getCursorPosition()
        self.emit(SIGNAL('cursorPositionChanged(int,int)'), line, index)
        
    def __refresh_readonly(self, index):
        finfo = self.data[index]
        read_only = not QFileInfo(finfo.filename).isWritable()
        finfo.editor.setReadOnly(read_only)
        self.emit(SIGNAL('readonly_changed(bool)'), read_only)
        
    def __check_last_modified(self, index):
        if self.__last_modified_flag:
            # Avoid infinite loop: when the QMessageBox.question pops, it
            # gets focus and then give it back to the QsciEditor instance,
            # triggering a refresh cycle which calls this method
            return
        finfo = self.data[index]
        self.__last_modified_flag = True
        lastm = QFileInfo(finfo.filename).lastModified()
        if lastm.toString().compare(finfo.lastmodified.toString()):
            if finfo.editor.isModified():
                answer = QMessageBox.question(self,
                    self.plugin.get_widget_title(),
                    self.tr("<b>%1</b> has been modified outside Pydee."
                            "<br>Do you want to reload it and loose all your "
                            "changes?").arg(osp.basename(finfo.filename)),
                    QMessageBox.Yes | QMessageBox.No)
                if answer == QMessageBox.Yes:
                    self.reload(index)
                else:
                    finfo.lastmodified = lastm
            else:
                self.reload(index)
        self.__last_modified_flag = False
        
    def refresh(self, index=None):
        """Refresh tabwidget"""
        if index is None:
            index = self.currentIndex()
        # Set current editor
        plugin_title = self.plugin.get_widget_title()
        if self.count():
            index = self.currentIndex()
            finfo = self.data[index]
            editor = finfo.editor
            editor.setFocus()
            plugin_title += " - " + osp.basename(finfo.filename)
            self.__refresh_classbrowser(index, update=False)
            self.emit(SIGNAL('refresh_analysis_results()'))
            self.__refresh_statusbar(index)
            self.__refresh_readonly(index)
            self.__check_last_modified(index)
        else:
            editor = None
        if self.plugin.dockwidget:
            self.plugin.dockwidget.setWindowTitle(plugin_title)
        # Update the modification-state-dependent parameters
        self.modification_changed()
        # Update FindReplace binding
        self.plugin.find_widget.set_editor(editor, refresh=False)
                
    def get_title(self, filename):
        """Return tab title"""
        if filename != self.plugin.file_path:
            return osp.basename(filename)
        else:
            return unicode(self.tr("Temporary file"))
        
    def __get_state_index(self, state, index):
        if index is None:
            index = self.currentIndex()
        if index == -1:
            return None, None
        if state is None:
            state = self.data[index].editor.isModified()
        return state, index
        
    def get_full_title(self, state=None, index=None):
        state, index = self.__get_state_index(state, index)
        if index is None:
            return
        finfo = self.data[index]
        title = self.get_title(finfo.filename)
        if state:
            title += "*"
        elif title.endswith('*'):
            title = title[:-1]
        if finfo.editor.isReadOnly():
            title = '(' + title + ')'
        return title

    def modification_changed(self, state=None, index=None):
        """
        Current editor's modification state has changed
        --> change tab title depending on new modification state
        --> enable/disable save/save all actions
        """
        # This must be done before refreshing save/save all actions:
        # (otherwise Save/Save all actions will always be enabled)
        self.emit(SIGNAL('opened_files_list_changed()'))
        # --
        state, index = self.__get_state_index(state, index)
        title = self.get_full_title(state, index)
        if index is None or title is None:
            return
        self.setTabText(index, title)
        # Toggle save/save all actions state
        self.plugin.save_action.setEnabled(state)
        self.plugin.refresh_save_all_action()
        
#===============================================================================
#    Load, reload
#===============================================================================
    def reload(self, index):
        finfo = self.data[index]
        txt, finfo.encoding = encoding.read(finfo.filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
        line, index = finfo.editor.getCursorPosition()
        finfo.editor.set_text(txt)
        finfo.editor.setModified(False)
        finfo.editor.setCursorPosition(line, index)
        
    def load(self, filename, goto=0):
        txt, enc = encoding.read(filename)
        ext = osp.splitext(filename)[1]
        if ext.startswith('.'):
            ext = ext[1:] # file extension with leading dot
        
        editor = QsciEditor(self)
        self.data.append( TabInfo(filename, enc, editor) )
        editor.set_text(txt)
        editor.setup_editor(linenumbers=True, language=ext,
                            code_analysis=CONF.get(self.ID, 'code_analysis'),
                            code_folding=CONF.get(self.ID, 'code_folding'),
                            font=get_font('editor'),
                            wrap=CONF.get(self.ID, 'wrap'))
        self.connect(editor, SIGNAL('cursorPositionChanged(int,int)'),
                     lambda line, index:
                     self.emit(SIGNAL('cursorPositionChanged(int,int)'),
                               line, index))
        self.connect(editor, SIGNAL('modificationChanged(bool)'),
                     self.modification_changed)
        self.connect(editor, SIGNAL("focus_in()"), self.focus_changed)
        self.connect(editor, SIGNAL("focus_changed()"),
                     lambda: self.plugin.emit(SIGNAL("focus_changed()")))

        title = self.get_title(filename)
        index = self.addTab(editor, title)
        self.setTabToolTip(index, filename)
        self.setTabIcon(index, get_filetype_icon(filename))
        
        self.plugin.find_widget.set_editor(editor)
       
        self.emit(SIGNAL('refresh_file_dependent_actions()'))
        self.modification_changed()

        self.analyze_script(index)
        self.__refresh_classbrowser(index)
        
        self.setCurrentIndex(index)
        
        editor.setFocus()
        
        if goto > 0:
            editor.highlight_line(goto)
                
#===============================================================================
#    Run
#===============================================================================
    def exec_script_extconsole(self, ask_for_arguments=False,
                               interact=False, debug=False):
        """Run current script in another process"""
        if self.save():
            finfo = self.data[self.currentIndex()]
            fname = osp.abspath(finfo.filename)
            wdir = osp.dirname(fname)
            self.plugin.emit(SIGNAL('open_external_console(QString,QString,bool,bool,bool)'),
                             fname, wdir, ask_for_arguments, interact, debug)
            if not interact and not debug:
                # If external console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # current external shell automatically
                # (see PluginWidget.visibility_changed method)
                finfo.editor.setFocus()
    
    def exec_script(self, set_focus=False):
        """Run current script"""
        if self.save():
            finfo = self.data[self.currentIndex()]
            self.interactive_console.run_script(finfo.filename, silent=True,
                                                set_focus=set_focus)
            if not set_focus:
                # If interactive console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # interactive shell automatically
                # (see PluginWidget.visibility_changed method)
                finfo.editor.setFocus()
        
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
        
#===============================================================================
#    Drag and drop
#===============================================================================
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


#TODO: Transform EditorSplitter into a real generic splittable editor
# -> i.e. all QSplitter widgets must be of the same kind
#    (currently there are editortabwidgets and editorsplitters at the same level)
# -> the main issue is that it's not possible to remove a widget from a
#    QSplitter except by destroying it -> it's not possible to change parenting
class EditorSplitter(QSplitter):
    def __init__(self, parent, actions):
        QSplitter.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setChildrenCollapsible(False)
        self.plugin = parent
        self.tab_actions = actions
        self.editortabwidget = EditorTabWidget(self.plugin, actions)
        self.connect(self.editortabwidget, SIGNAL("destroyed(QObject*)"),
                     self.editortabwidget_closed)
        self.connect(self.editortabwidget, SIGNAL("split_vertically()"),
                     lambda: self.split(orientation=Qt.Vertical))
        self.connect(self.editortabwidget, SIGNAL("split_horizontally()"),
                     lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editortabwidget)
        
    def editortabwidget_closed(self):
        self.editortabwidget = None
        if self.count() == 1:
            # editortabwidget just closed was the last widget in this QSplitter
            self.close()
        
    def editorsplitter_closed(self, obj):
        if self.count() == 1 and self.editortabwidget is None:
            # editorsplitter just closed was the last widget in this QSplitter
            self.close()
        elif self.count() == 2 and self.editortabwidget:
            # back to the initial state: a single editortabwidget instance,
            # as a single widget in this QSplitter: orientation may be changed
            self.editortabwidget.reset_orientation()
        
    def split(self, orientation=Qt.Vertical):
        self.setOrientation(orientation)
        self.editortabwidget.set_orientation(orientation)
        editorsplitter = EditorSplitter(self.plugin, self.tab_actions)
        self.addWidget(editorsplitter)
        self.connect(editorsplitter, SIGNAL("destroyed(QObject*)"),
                     self.editorsplitter_closed)


#===============================================================================
# Status bar widgets
#===============================================================================
class ReadWriteStatus(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)
        
        font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(translate("Editor", "Permissions:")))
        self.readwrite = QLabel()
        self.readwrite.setFont(font)
        layout.addWidget(self.readwrite)
        layout.addSpacing(10)
        self.setLayout(layout)
        
        statusbar.addPermanentWidget(self)
        self.hide()
        
    def readonly_changed(self, readonly):
        readwrite = "R" if readonly else "RW"
        self.readwrite.setText(readwrite.ljust(3))
        self.show()

class EncodingStatus(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)
        
        font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(translate("Editor", "Encoding:")))
        self.encoding = QLabel()
        self.encoding.setFont(font)
        layout.addWidget(self.encoding)
        layout.addSpacing(10)
        self.setLayout(layout)
        
        statusbar.addPermanentWidget(self)
        self.hide()
        
    def encoding_changed(self, encoding):
        self.encoding.setText(str(encoding).upper().ljust(15))
        self.show()

class CursorPositionStatus(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)
        
        font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(translate("Editor", "Line:")))
        self.line = QLabel()
        self.line.setFont(font)
        layout.addWidget(self.line)
        layout.addWidget(QLabel(translate("Editor", "Column:")))
        self.column = QLabel()
        self.column.setFont(font)
        layout.addWidget(self.column)
        self.setLayout(layout)
        
        statusbar.addPermanentWidget(self)
        self.hide()
        
    def cursor_position_changed(self, line, index):
        self.line.setText("%-6d" % (line+1))
        self.column.setText("%-4d" % (index+1))
        self.show()
        

#TODO: This class clearly needs some code cleaning/refactoring
class Editor(PluginWidget):
    """
    Multi-file Editor widget
    """
    ID = 'editor'
    file_path = get_conf_path('.temp.py')
    def __init__(self, parent):
        self.file_dependent_actions = []
        self.pythonfile_dependent_actions = []
        self.dock_toolbar_actions = None
        self.file_toolbar_actions = None
        self.analysis_toolbar_actions = None
        self.run_toolbar_actions = None
        self.edit_toolbar_actions = None
        PluginWidget.__init__(self, parent)
        
        statusbar = self.main.statusBar()
        self.readwrite_status = ReadWriteStatus(self, statusbar)
        self.encoding_status = EncodingStatus(self, statusbar)
        self.cursorpos_status = CursorPositionStatus(self, statusbar)
        
        layout = QVBoxLayout()
        self.dock_toolbar = QToolBar(self)
        add_actions(self.dock_toolbar, self.dock_toolbar_actions)
        layout.addWidget(self.dock_toolbar)
        
        # Class browser
        self.classbrowser = ClassBrowser(self)
        self.classbrowser.setVisible( CONF.get(self.ID, 'class_browser') )
        self.connect(self.classbrowser, SIGNAL('go_to_line(int)'),
                     self.go_to_line)
        
        # Opened files listwidget
        self.openedfileslistwidget = QListWidget(self)
        self.connect(self.openedfileslistwidget,
                     SIGNAL('itemActivated(QListWidgetItem*)'),
                     self.openedfileslistwidget_clicked)
        
        # Analysis results listwidget
        self.analysislistwidget = QListWidget(self)
        self.analysislistwidget.setWordWrap(True)
        self.connect(self.analysislistwidget,
                     SIGNAL('itemActivated(QListWidgetItem*)'),
                     self.analysislistwidget_clicked)
        
        # Right panel toolbox
        self.toolbox = QToolBox(self)
        self.toolbox.addItem(self.classbrowser, get_icon('class_browser.png'),
                             translate("ClassBrowser", "Classes and functions"))
        self.toolbox.addItem(self.openedfileslistwidget,
                             get_icon('opened_files.png'),
                             self.tr('Opened files'))
        self.toolbox.addItem(self.analysislistwidget,
                             get_icon('analysis_results.png'),
                             self.tr('Code analysis'))
        #TODO: New toolbox item: template list
        #TODO: New toolbox item: file metrics (including current line, index)
        self.connect(self.toolbox, SIGNAL('currentChanged(int)'),
                     self.toolbox_current_changed)
        
        self.editortabwidgets = []
        
        cb_splitter = QSplitter(self)
        cb_splitter.addWidget(EditorSplitter(self, self.tab_actions))
        cb_splitter.addWidget(self.toolbox)
        cb_splitter.setStretchFactor(0, 3)
        cb_splitter.setStretchFactor(1, 1)
        layout.addWidget(cb_splitter)
        
        toolbox_state = CONF.get(self.ID, 'toolbox_panel')
        self.toolbox_action.setChecked(toolbox_state)
        self.toolbox.setVisible(toolbox_state)
        
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
        
        self.last_focus_editortabwidget = None
        self.connect(self, SIGNAL("focus_changed()"),
                     self.save_focus_editortabwidget)
        
        self.filetypes = ((self.tr("Python files"), ('.py', '.pyw')),
                          (self.tr("Pyrex files"), ('.pyx',)),
                          (self.tr("C files"), ('.c', '.h')),
                          (self.tr("C++ files"), ('.cc', '.cpp', '.h', '.cxx',
                                                  '.hpp', '.hh')),
                          (self.tr("Fortran files"),
                           ('.f', '.for', '.f90', '.f95', '.f2k')),
                          (self.tr("Patch and diff files"),
                           ('.patch', '.diff', '.rej')),
                          (self.tr("Batch files"),
                           ('.bat', '.cmd')),
                          (self.tr("Text files"), ('.txt',)),
                          (self.tr("Web page files"),
                           ('.css', '.htm', '.html',)),
                          (self.tr("Configuration files"),
                           ('.properties', '.session', '.ini', '.inf',
                            '.reg', '.cfg')),
                          (self.tr("All files"), ('.*',)))
        
        
    #------ Toolboxes
    def toolbox_current_changed(self, index):
        """Toolbox current index has changed"""
        if self.openedfileslistwidget.isVisible():
            self.refresh_openedfileslistwidget()
        elif self.classbrowser.isVisible():
            # Refreshing class browser
            editortabwidget = self.get_current_editortabwidget()
            editortabwidget.refresh()
        elif self.analysislistwidget.isVisible():
            self.refresh_analysislistwidget()

    def openedfileslistwidget_clicked(self, item):
        filename = unicode(item.data(Qt.UserRole).toString())
        editortabwidget, index = self.get_editortabwidget_index(filename)
        editortabwidget.data[index].editor.setFocus()
        editortabwidget.setCurrentIndex(index)
    
    def analysislistwidget_clicked(self, item):
        line, _ok = item.data(Qt.UserRole).toInt()
        self.get_current_editor().highlight_line(line+1)
    
    def refresh_analysislistwidget(self):
        """Refresh analysislistwidget *and* analysis navigation buttons"""
        editortabwidget = self.get_current_editortabwidget()
        check_results = editortabwidget.get_analysis_results()
        state = CONF.get(self.ID, 'code_analysis') \
                and check_results is not None and len(check_results)
        self.previous_warning_action.setEnabled(state)
        self.next_warning_action.setEnabled(state)
        if self.analysislistwidget.isHidden():
            return
        self.analysislistwidget.clear()
        self.analysislistwidget.setEnabled(state and check_results is not None)
        if state and check_results:
            for message, line0, error in check_results:
                icon = get_icon('error.png' if error else 'warning.png')
                item = QListWidgetItem(icon, message[:1].upper() + message[1:],
                                       self.analysislistwidget)
                item.setData(Qt.UserRole, QVariant(line0-1))
    
    def go_to_next_warning(self):
        editor = self.get_current_editor()
        editor.go_to_next_warning()
    
    def go_to_previous_warning(self):
        editor = self.get_current_editor()
        editor.go_to_previous_warning()
            
    def refresh_openedfileslistwidget(self):
        """
        Opened files list has changed:
        --> open/close file action
        --> modification ('*' added to title)
        --> current edited file has changed
        """
        # Refresh Python file dependent actions:
        fname = self.get_current_filename()
        if fname:
            enable = osp.splitext(fname)[1] in ('.py', '.pyw')
            for action in self.pythonfile_dependent_actions:
                action.setEnabled(enable)
        # Refresh openedfileslistwidget:
        if self.openedfileslistwidget.isHidden():
            return
        filenames = self.get_filenames()
        current_filename = self.get_current_filename()
        self.openedfileslistwidget.clear()
        for filename in filenames:
            editortabwidget, index = self.get_editortabwidget_index(filename)
            title = editortabwidget.get_full_title(index=index)
            item = QListWidgetItem(get_filetype_icon(filename),
                                   title, self.openedfileslistwidget)
            item.setData(Qt.UserRole, QVariant(filename))
            if filename == current_filename:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.openedfileslistwidget.addItem(item)
        

    def get_filetype_filters(self):
        filters = []
        for title, ftypes in self.filetypes:
            filters.append("%s (*%s)" % (title, " *".join(ftypes)))
        return "\n".join(filters)

    def get_valid_types(self):
        ftype_list = []
        for _title, ftypes in self.filetypes:
            ftype_list += list(ftypes)
        return ftype_list

    def get_filenames(self):
        filenames = []
        for editortabwidget in self.editortabwidgets:
            filenames += [finfo.filename for finfo in editortabwidget.data]
        return filenames

    def get_editortabwidget_index(self, filename):
        for editortabwidget in self.editortabwidgets:
            index = editortabwidget.has_filename(filename)
            if index is not None:
                return (editortabwidget, index)
        else:
            return (None, None)
        
    def __get_focus_editortabwidget(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, QsciEditor):
            for editortabwidget in self.editortabwidgets:
                if fwidget is editortabwidget.currentWidget():
                    return editortabwidget
        elif isinstance(fwidget, EditorTabWidget):
            return fwidget
        
    def save_focus_editortabwidget(self):
        editortabwidget = self.__get_focus_editortabwidget()
        if editortabwidget is not None:
            self.last_focus_editortabwidget = editortabwidget
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Editor')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.get_current_editor()
        
    def __reset_statusbar(self):
        self.encoding_status.hide()
        self.cursorpos_status.hide()
        
    def register_editortabwidget(self, editortabwidget):
        self.editortabwidgets.append(editortabwidget)
        self.last_focus_editortabwidget = editortabwidget
        self.connect(editortabwidget, SIGNAL('reset_statusbar()'),
                     self.readwrite_status.hide)
        self.connect(editortabwidget, SIGNAL('reset_statusbar()'),
                     self.encoding_status.hide)
        self.connect(editortabwidget, SIGNAL('reset_statusbar()'),
                     self.cursorpos_status.hide)
        self.connect(editortabwidget, SIGNAL('readonly_changed(bool)'),
                     self.readwrite_status.readonly_changed)
        self.connect(editortabwidget, SIGNAL('encoding_changed(QString)'),
                     self.encoding_status.encoding_changed)
        self.connect(editortabwidget, SIGNAL('cursorPositionChanged(int,int)'),
                     self.cursorpos_status.cursor_position_changed)
        self.connect(editortabwidget, SIGNAL('opened_files_list_changed()'),
                     self.refresh_openedfileslistwidget)
        self.connect(editortabwidget, SIGNAL('refresh_analysis_results()'),
                     self.refresh_analysislistwidget)
        self.connect(editortabwidget,
                     SIGNAL('refresh_file_dependent_actions()'),
                     self.refresh_file_dependent_actions)
        self.connect(editortabwidget, SIGNAL('move_tab(long,long,int,int)'),
                     self.move_tabs_between_editortabwidgets)
        
    def unregister_editortabwidget(self, editortabwidget):
        """Removing editortabwidget only if it's not the last remaining"""
        if len(self.editortabwidgets) > 1:
            index = self.editortabwidgets.index(editortabwidget)
            self.editortabwidgets.pop(index)
            editortabwidget.close() # remove widget from splitter
            focus_widget = self.get_focus_widget()
            if focus_widget is not None:
                focus_widget.setFocus()
            return True
        else:
            # Tabbededitor was not removed!
            return False
        
    def __get_editortabwidget_from_id(self, t_id):
        for editortabwidget in self.editortabwidgets:
            if id(editortabwidget) == t_id:
                return editortabwidget
        
    def move_tabs_between_editortabwidgets(self, id_from, id_to,
                                        index_from, index_to):
        """
        Move tab between tabwidgets
        (see editortabwidget.move_data when moving tabs inside one tabwidget)
        Tabs haven't been moved yet since tabwidgets don't have any
        reference towards other tabwidget instances
        """
        tw_from = self.__get_editortabwidget_from_id(id_from)
        tw_to = self.__get_editortabwidget_from_id(id_to)

        tw_from.move_data(index_from, index_to, tw_to)

        tip, text = tw_from.tabToolTip(index_from), tw_from.tabText(index_from)
        icon, widget = tw_from.tabIcon(index_from), tw_from.widget(index_from)
        
        tw_from.removeTab(index_from)
        tw_to.insertTab(index_to, widget, icon, text)
        tw_to.setTabToolTip(index_to, tip)
        
        tw_to.setCurrentIndex(index_to)

    def get_current_editortabwidget(self):
        if len(self.editortabwidgets) == 1:
            return self.editortabwidgets[0]
        else:
            editortabwidget = self.__get_focus_editortabwidget()
            if editortabwidget is None:
                return self.last_focus_editortabwidget
            else:
                return editortabwidget
        
    def get_current_editor(self):
        editortabwidget = self.get_current_editortabwidget()
        if editortabwidget is not None:
            return editortabwidget.currentWidget()
        
    def get_current_filename(self):
        editortabwidget = self.get_current_editortabwidget()
        if editortabwidget is not None:
            return editortabwidget.get_current_filename()
        
    def is_file_opened(self, filename=None):
        if filename is None:
            # Is there any file opened?
            return self.get_current_editor() is not None
        else:
            editortabwidget, _index = self.get_editortabwidget_index(filename)
            return editortabwidget
        
    def set_current_filename(self, filename):
        """Set focus to *filename* if this file has been opened"""
        editortabwidget, _index = self.get_editortabwidget_index(filename)
        if editortabwidget is not None:
            return editortabwidget.set_current_filename(filename)
    
    def refresh_file_dependent_actions(self):
        """Enable/disable file dependent actions
        (only if dockwidget is visible)"""
        if self.dockwidget and self.dockwidget.isVisible():
            enable = self.get_current_editor() is not None
            for action in self.file_dependent_actions:
                action.setEnabled(enable)
                
    def refresh_save_all_action(self):
        state = False
        for editortabwidget in self.editortabwidgets:
            if editortabwidget.count() > 1:
                state = state or any([finfo.editor.isModified() for finfo \
                                      in editortabwidget.data])
        self.save_all_action.setEnabled(state)
    
    def refresh(self):
        """Refresh editor plugin"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.refresh()
        self.refresh_save_all_action()
        
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
        if enable:
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
        
        pylint_action = create_action(self, self.tr("Run pylint code analysis"),
                                      "F7", triggered=self.run_pylint)
        pylint_action.setEnabled(is_pylint_installed())
        
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set text and margin font style"),
            triggered=self.change_font)
        analyze_action = create_action(self,
            self.tr("Code analysis (pyflakes)"),
            toggled=self.toggle_code_analysis,
            tip=self.tr("If enabled, Python source code will be analyzed "
                        "using <b>pyflakes</b>, lines containing errors or "
                        "warnings will be highlighted"))
        analyze_action.setChecked( CONF.get(self.ID, 'code_analysis') )
        fold_action = create_action(self, self.tr("Code folding"),
            toggled=self.toggle_code_folding)
        fold_action.setChecked( CONF.get(self.ID, 'code_folding') )
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        tab_action = create_action(self, self.tr("Tab always indent"),
            toggled=self.toggle_tab_mode,
            tip=self.tr("If enabled, pressing Tab will always indent, "
                        "even when the cursor is not at the beginning "
                        "of a line"))
        tab_action.setChecked( CONF.get(self.ID, 'tab_always_indent') )
        workdir_action = create_action(self, self.tr("Set working directory"),
            tip=self.tr("Change working directory to current script directory"),
            triggered=self.set_workdir)

        self.toolbox_action = create_action(self,
            self.tr("Lateral panel"), None, 'toolbox.png',
            tip=self.tr("Editor lateral panel (class browser, "
                        "opened file list, ...)"),
            toggled=self.toggle_toolbox)
                
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
                self.exec_process_debug_action, None, pylint_action,
                None, font_action, wrap_action, tab_action, fold_action,
                analyze_action, self.toolbox_action)
        self.file_toolbar_actions = [self.new_action, self.open_action,
                self.save_action, self.save_all_action]
        self.analysis_toolbar_actions = [self.previous_warning_action,
                self.next_warning_action, self.toolbox_action]
        self.run_toolbar_actions = [self.exec_action,
                self.exec_selected_action, self.exec_process_action,
                self.exec_interact_action]
        self.edit_toolbar_actions = [self.comment_action, self.uncomment_action,
                self.indent_action, self.unindent_action]
        self.dock_toolbar_actions = self.file_toolbar_actions + [None] + \
                                    self.analysis_toolbar_actions + [None] + \
                                    self.run_toolbar_actions + [None] + \
                                    self.edit_toolbar_actions
        self.pythonfile_dependent_actions = (self.exec_action, pylint_action,
                self.exec_interact_action, self.exec_selected_action,
                self.exec_process_action, self.exec_process_interact_action,
                self.exec_process_args_action, self.exec_process_debug_action,
                self.previous_warning_action, self.next_warning_action,
                self.blockcomment_action, self.unblockcomment_action,
                )
        self.file_dependent_actions = self.pythonfile_dependent_actions + \
                (self.save_action, self.save_as_action,
                 self.save_all_action, workdir_action, self.close_action,
                 self.close_all_action,
                 self.comment_action, self.uncomment_action,
                 self.indent_action, self.unindent_action)
        self.tab_actions = (self.save_action, self.save_as_action,
                self.exec_action, self.exec_process_action,
                workdir_action, self.close_action)
        return (source_menu_actions, self.dock_toolbar_actions)        
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        filenames = []
        for editortabwidget in self.editortabwidgets:
            filenames += [finfo.filename for finfo in editortabwidget.data]
        CONF.set(self.ID, 'filenames', filenames)
        CONF.set(self.ID, 'current_filename', self.get_current_filename())
        CONF.set(self.ID, 'recent_files', self.recent_files)
        is_ok = True
        for editortabwidget in self.editortabwidgets:
            is_ok = is_ok and editortabwidget.save_if_changed(cancelable)
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
            
    def run_pylint(self):
        """Run pylint code analysis"""
        fname = self.get_current_filename()
        self.emit(SIGNAL('run_pylint(QString)'), fname)
        
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
            
    def close_all_files(self):
        """Close all opened scripts"""
        for editortabwidget in self.editortabwidgets:
            editortabwidget.close_all_files()
        
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
                          self.get_filetype_filters())
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
            for editortabwidget in self.editortabwidgets:
                # -- Do not open an already opened file
                if editortabwidget.set_current_filename(filename):
                    break
            else:
                # -- Not a valid filename:
                if not osp.isfile(filename):
                    continue
                # --
                editortabwidget = self.get_current_editortabwidget()
                editortabwidget.load(filename, goto)
                self.add_recent_file(filename)
                
        if goto > 0:
            editor = self.get_current_editor()
            editor.highlight_line(goto)


    def __close_and_reload(self, filename, new_filename=None):
        filename = osp.abspath(unicode(filename))
        for editortabwidget in self.editortabwidgets:
            index = editortabwidget.has_filename(filename)
            if index is not None:
                editortabwidget.close_file(index)
                if new_filename is not None:
                    self.load(unicode(new_filename))
                
    def removed(self, filename):
        """File was removed in explorer widget"""
        self.__close_and_reload(filename)
    
    def renamed(self, source, dest):
        """File was renamed in explorer widget"""
        self.__close_and_reload(source, new_filename=dest)
                
                
    def close_file(self):
        """Close current file"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.close_file()
                
    def save(self, index=None, force=False):
        """Save file"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.save(index=index, force=force)
                
    def save_as(self):
        """Save *as* the currently edited file"""
        fname = self.get_current_filename()
        if fname is not None:
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            filename = QFileDialog.getSaveFileName(self,
                          self.tr("Save Python script"), fname,
                          self.get_filetype_filters())
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            if filename:
                filename = osp.normpath(unicode(filename))
                editortabwidget = self.get_current_editortabwidget()
                index = editortabwidget.currentIndex()
                editortabwidget.filenames[index] = filename
            else:
                return False
            self.save(force=True)
            # Refresh the explorer widget if it exists:
            self.emit(SIGNAL("refresh_explorer()"))
        
    def save_all(self):
        """Save all opened files"""
        for editortabwidget in self.editortabwidgets:
            editortabwidget.save_all()
    
    def exec_script_extconsole(self, ask_for_arguments=False,
                               interact=False, debug=False):
        """Run current script in another process"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.exec_script_extconsole( \
            ask_for_arguments=ask_for_arguments, interact=interact, debug=debug)
    
    def exec_script(self, set_focus=False):
        """Run current script"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.exec_script(set_focus=set_focus)
    
    def exec_script_and_interact(self):
        """Run current script and set focus to shell"""
        self.exec_script(set_focus=True)
        
    def exec_selected_text(self):
        """Run selected text in current script and set focus to shell"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.exec_selected_text()
        
    def change_font(self):
        """Change editor font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                          self.tr("Select a new font"))
        if valid:
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.set_wrap_mode(checked)
            CONF.set(self.ID, 'wrap', checked)
            
    def toggle_tab_mode(self, checked):
        """
        Toggle tab mode:
        checked = tab always indent
        (otherwise tab indents only when cursor is at the beginning of a line)
        """
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.set_tab_mode(checked)
            CONF.set(self.ID, 'tab_always_indent', checked)
            
    def toggle_code_folding(self, checked):
        """Toggle code folding"""
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.setup_margins(linenumbers=True,
                              code_folding=checked,
                              code_analysis=CONF.get(self.ID, 'code_analysis'))
                    if not checked:
                        finfo.editor.unfold_all()
            CONF.set(self.ID, 'code_folding', checked)
            
    def toggle_code_analysis(self, checked):
        """Toggle code analysis"""
        if hasattr(self, 'editortabwidgets'):
            CONF.set(self.ID, 'code_analysis', checked)
            current_editortabwidget = self.get_current_editortabwidget()
            current_index = current_editortabwidget.currentIndex()
            for editortabwidget in self.editortabwidgets:
                for index, finfo in enumerate(editortabwidget.data):
                    finfo.editor.setup_margins(linenumbers=True,
                              code_analysis=checked,
                              code_folding=CONF.get(self.ID, 'code_folding'))
                    if index != current_index:
                        editortabwidget.analyze_script(index)
            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            current_editortabwidget.analyze_script()

    def toggle_toolbox(self, checked):
        """Toggle toolbox"""
        self.toolbox.setVisible(checked)
        CONF.set(self.ID, 'toolbox_panel', checked)
