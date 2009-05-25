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
Matplotlib figure integration
"""

import sys

# For debugging purpose:
STDOUT = sys.stdout

from PyQt4.QtGui import QHBoxLayout, QVBoxLayout, QLabel, QDockWidget
from PyQt4.QtCore import Qt

# Local imports
from PyQtShell.plugins import PluginWidget
from PyQtShell.config import get_font, get_icon
from PyQtShell.qthelpers import create_toolbutton

class MatplotlibFigure(PluginWidget):
    """
    Matplotlib Figure Dockwidget
    """
    ID = 'figure'
    features = QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable
    location = Qt.LeftDockWidgetArea
    def __init__(self, parent, canvas, num):        
        self.canvas = canvas
        self.num = num
        PluginWidget.__init__(self, parent)

        # Close button
        self.close_button = create_toolbutton(self, callback=self.close,
                                      icon=get_icon("fileclose.png"),
                                      tip=self.tr("Close figure %1").arg(num))
        
        # Top horizontal layout
        self.h_layout = QHBoxLayout()
        self.statusbar = self.set_statusbar()        
        self.h_layout.addWidget(self.statusbar)
        self.h_layout.addWidget(self.close_button)
        
        # Main vertical layout
        self.v_layout = QVBoxLayout()
        self.v_layout.addLayout(self.h_layout)
        self.v_layout.addWidget(self.canvas)
        self.setLayout(self.v_layout)
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("Figure %d" % self.num)
        
    def set_statusbar(self):
        """Set status bar"""
        statusbar = QLabel('')
        statusbar.setFont(get_font(self.ID, 'statusbar'))
        return statusbar
        
    def statusBar(self):
        """Fake Qt method --> for matplotlib"""
        return self
    
    def showMessage(self, message):
        """Fake Qt method --> for matplotlib"""
        self.statusbar.setText("    " + message)
        
    def addToolBar(self, toolbar):
        """Fake Qt method --> for matplotlib"""
        self.h_layout.insertWidget(0, toolbar)
        
    def refresh(self):
        """Refresh widget"""
        pass
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def closeEvent(self, event):
        """closeEvent reimplementation"""
        self.main.widgetlist.pop(self.main.widgetlist.index(self))
        self.dockwidget.close()
        event.accept()

