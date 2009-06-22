# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Editor widgets"""

from PyQt4.QtGui import QVBoxLayout

import sys
# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.plugins import ReadOnlyEditor

#TODO: Add a tabwidget to handle the 3 Pydee history files
#TODO: [low-priority] add a combo box to select a date from the shown history
class HistoryLog(ReadOnlyEditor):
    """
    History log widget
    """
    ID = 'historylog'
    def __init__(self, parent):
        ReadOnlyEditor.__init__(self, parent)
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