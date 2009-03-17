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
#    Foobar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
Matplotlib figure integration
"""

from PyQt4.QtGui import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                         QSizePolicy, QDockWidget)
from PyQt4.QtCore import Qt, SIGNAL

# Local imports
from PyQtShell.widgets.base import WidgetMixin
from PyQtShell.config import get_font, get_icon

class MatplotlibFigure(QWidget, WidgetMixin):
    """
    Matplotlib Figure Dockwidget
    """
    ID = 'figure'
    def __init__(self, parent, canvas, num):
        QWidget.__init__(self, None) # Bug if parent is not None!!
        WidgetMixin.__init__(self, parent)
        
        self.num = num
        self.canvas = canvas
        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(self.canvas)

        self.h_layout = QHBoxLayout()
        self.statusbar = self.set_statusbar()        
        self.h_layout.addWidget(self.statusbar)
        self.close_button = QPushButton(get_icon('close.png'), self.tr("Close"))
        self.close_button.setToolTip(self.tr("Close figure %1").arg(num))
        self.connect(self.close_button, SIGNAL('clicked()'),
                     self.close)
        self.close_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.h_layout.addWidget(self.close_button)
        
        self.v_layout.addLayout(self.h_layout)        
        self.setLayout(self.v_layout)
        
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
        
    def get_name(self, raw=True):
        """Return widget name"""
        return self.tr("Figure %d" % self.num)
        
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
    
    def get_dockwidget_features(self):
        """Return QDockWidget features"""
        return QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable
        
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
        dock = self.mainwindow.dockdict.pop(self)
        self.mainwindow.widgetlist.pop(self.mainwindow.widgetlist.index(self))
        self.mainwindow.view_menu.removeAction(dock.toggleViewAction())
        dock.close()
        event.accept()

