# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Editor widgets"""

from PyQt4.QtGui import QVBoxLayout, QFontDialog
from PyQt4.QtCore import Qt, SIGNAL

import os.path as osp

import sys
# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib import encoding
from pydeelib.config import CONF, get_font, get_icon, set_font
from pydeelib.qthelpers import create_action
from pydeelib.widgets.tabs import Tabs
from pydeelib.widgets.qscieditor import QsciEditor
from pydeelib.widgets.findreplace import FindReplace
from pydeelib.plugins import PluginWidget

#TODO: External console: add history length option (or move the interactive console option?)
#TODO: Add a tabwidget to handle the 3 Pydee history files
class HistoryLog(PluginWidget):
    """
    History log widget
    """
    ID = 'historylog'
    location = Qt.RightDockWidgetArea
    def __init__(self, parent):
        self.tabwidget = None
        self.menu_actions = None
        self.dockviewer = None
        
        self.editors = []
        self.filenames = []
        self.icons = []
        
        PluginWidget.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh)
        self.connect(self.tabwidget, SIGNAL("close_tab(int)"),
                     self.tabwidget.removeTab)
        self.connect(self.tabwidget, SIGNAL('move_data(int,int)'),
                     self.move_tab)
        layout.addWidget(self.tabwidget)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)
        
    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        filename = self.filenames.pop(index_from)
        editor = self.editors.pop(index_from)
        icon = self.icons.pop(index_from)
        
        self.filenames.insert(index_to, filename)
        self.editors.insert(index_to, editor)
        self.icons.insert(index_to, icon)
        
    def add_history(self, filename):
        """
        Add new history tab
        Slot for SIGNAL('add_history(QString)') emitted by QsciShell
        """
        filename = unicode(filename)
        if filename in self.filenames:
            return
        editor = QsciEditor(self)
        if osp.splitext(filename)[1] == '.py':
            language = 'py'
            icon = get_icon('python.png')
        else:
            language = 'bat'
            icon = get_icon('cmdprompt.png')
        editor.setup_editor(linenumbers=False, language=language,
                            code_folding=True)
        self.connect(editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        editor.setReadOnly(True)
        editor.set_font( get_font(self.ID) )
        editor.set_wrap_mode( CONF.get(self.ID, 'wrap') )

        text, _ = encoding.read(filename)
        editor.set_text(text)
        editor.move_cursor_to_end()
        
        self.editors.append(editor)
        self.filenames.append(filename)
        self.icons.append(icon)
        index = self.tabwidget.addTab(editor, osp.basename(filename))
        self.find_widget.set_editor(editor)
        self.tabwidget.setTabToolTip(index, filename)
        self.tabwidget.setTabIcon(index, icon)
        self.tabwidget.setCurrentIndex(index)
        
    def append_to_history(self, filename, command):
        """
        Append an entry to history filename
        Slot for SIGNAL('append_to_history(QString,QString)')
        emitted by QsciShell
        """
        filename, command = unicode(filename), unicode(command)
        index = self.filenames.index(filename)
        self.editors[index].append(command)
        self.editors[index].move_cursor_to_end()
        self.tabwidget.setCurrentIndex(index)
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('History log')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.tabwidget.currentWidget()
        
    def set_actions(self):
        """Setup actions"""
        font_action = create_action(self, self.tr("&Font..."), None,
                                    'font.png', self.tr("Set shell font style"),
                                    triggered=self.change_font)
        wrap_action = create_action(self, self.tr("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        self.menu_actions = [font_action, wrap_action]
        return (self.menu_actions, None)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                       self, self.tr("Select a new font"))
        if valid:
            for editor in self.editors:
                editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.tabwidget is None:
            return
        for editor in self.editors:
            editor.set_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
    def refresh(self):
        """Refresh tabwidget"""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget()
        else:
            editor = None
        self.find_widget.set_editor(editor)
