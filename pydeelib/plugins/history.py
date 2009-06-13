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

from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtCore import SIGNAL

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.config import CONF, get_font
from pydeelib.widgets.qscieditor import QsciEditor
from pydeelib.widgets.findreplace import FindReplace
from pydeelib.plugins import PluginWidget


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
