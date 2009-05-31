# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
pydeelib.widgets
=================

Widgets defined in this module may be used in any other PyQt4-based application

They are also used in Pydee through the Plugin interface (see pydeelib.plugins)
"""

from PyQt4.QtGui import QTabWidget, QMenu, QMouseEvent
from PyQt4.QtCore import SIGNAL, Qt, QEvent

# Local imports
from pydeelib.qthelpers import add_actions

class Tabs(QTabWidget):
    """TabWidget with a context-menu"""
    def __init__(self, parent, actions):
        QTabWidget.__init__(self, parent)
        self.menu = QMenu(self)
        if actions:
            add_actions(self.menu, actions)
        
    def contextMenuEvent(self, event):
        """Override Qt method"""
        if self.menu:
            self.menu.popup(event.globalPos())
            
    def mousePressEvent(self, event):
        """Override Qt method"""
        if event.button() == Qt.MidButton:
            if self.count():
                #TODO: Really close the clicked tab and not the last one
                self.emit(SIGNAL("close_tab(int)"), self.currentIndex())

