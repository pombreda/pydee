#!/usr/bin/env python
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

"""
PyQtShell.widgets
=================

Widgets defined in this module may be used in any other PyQt4-based application

They are also used in Pydee through the Plugin interface (see PyQtShell.plugins)
"""

from PyQt4.QtGui import QTabWidget, QMenu, QMouseEvent
from PyQt4.QtCore import SIGNAL, Qt, QEvent

# Local imports
from PyQtShell.qthelpers import add_actions

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

